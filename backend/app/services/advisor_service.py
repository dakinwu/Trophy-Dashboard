"""Official PSN library retrieval and ownership-aware advisor view model."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from contextlib import nullcontext
from datetime import datetime, timezone

from app.config import settings
from app.core.cache import FileCache
from app.models import (
    AdvisorBundleChildResult,
    AdvisorBundleResult,
    AdvisorCandidate,
    AdvisorGame,
    AdvisorLibrary,
    AdvisorSignalResult,
    PsnprofilesAdvisorSignals,
)
from app.services.http import PSNProfilesFetchError, create_session
from app.services.autopop_catalog import get_autopop_info
from app.services.gemini_title_service import (
    TitleResolution,
    candidate_key,
    is_english_search_title,
    resolve_advisor_titles,
)
from app.services.gemini_bundle_service import resolve_advisor_bundles
from app.services.psn_service import (
    _client,
    _game_name_score,
    _playtime_from_title_stats,
    _stats_platform,
    _trophy_title_platform,
)
from app.services.psnprofiles_trophies_service import get_psnprofiles_trophies

logger = logging.getLogger(__name__)

_LIBRARY_URL = "https://web.np.playstation.com/api/graphql/v1/op"
_LIBRARY_OPERATION = "getPurchasedGameList"
_LIBRARY_QUERY_HASH = (
    "827a423f6a8ddca4107ac01395af2ec0eafd8396fc7fa204aaf9b7ed2eefa168"
)
_LIBRARY_PAGE_SIZE = 100
_LIBRARY_TTL = 24 * 3600
_SUPPORTED_PLATFORMS = {"PS3", "PS4", "PS5"}
_TRIAL_TITLE = re.compile(
    r"(?:^|[\s\-–—:|([）])"
    r"(?:demo|trial(?:\s+version)?|free\s+trial|playtest|open\s+beta|"
    r"closed\s+beta|private\s+beta|beta(?:\s*(?:test|測試|测试))?|network\s+test|technical\s+test|"
    r"public\s+test\s+server|test\s+server|pts)"
    r"(?:$|[\s\-–—:|)\]（])|"
    r"試玩(?:版)?|试玩(?:版)?|體驗版|体验版|測試版|测试版|"
    r"公開測試|公开测试|体験版|ベータテスト",
    flags=re.IGNORECASE,
)
_BETA_TITLE = re.compile(
    r"(?:^|[^A-Za-z0-9])beta(?=$|[^A-Za-z0-9])",
    flags=re.IGNORECASE,
)
_TRIAL_VALUES = {
    "TRIAL",
    "DEMO",
    "BETA",
    "PLAYTEST",
    "PUBLIC_TEST_SERVER",
    "PTS",
    "TEST_SERVER",
    "GAME_TRIAL",
    "TRIAL_VERSION",
}
_NON_GAME_CONTENT_TITLE = re.compile(
    r"(?:bonus\s+content|extra\s+content|digital\s+deluxe\s+content|"
    r"soundtrack|art\s*book|digital\s+art|premium\s+musical\s+notes|"
    r"數位豪華內容|数字豪华内容|獎勵內容|奖励内容|額外內容|额外内容|"
    r"特典內容|特典内容|原聲帶|原声带|美術集|美术集|美術書|美术书|"
    r"數位歷史書|数字历史书|數位永恆精選|数字永恒精选|"
    r"ボーナスコンテンツ|サウンドトラック|アートブック)",
    flags=re.IGNORECASE,
)
_NON_GAME_CONTENT_VALUES = {
    "ADD_ON",
    "ADDON",
    "BONUS_CONTENT",
    "DLC",
    "EXTRA_CONTENT",
}
_NON_GAME_EXACT_TITLES = {
    "amazon prime video",
    "apple tv",
    "bravia tv player",
    "crunchyroll",
    "disney+",
    "disney plus",
    "hulu",
    "ign",
    "media player",
    "netflix",
    "plex",
    "prime video",
    "spotify",
    "twitch",
    "youtube",
    "youtube tv",
    "媒體播放器",
    "媒体播放器",
}
_NON_GAME_PRODUCT_MARKERS = {
    "BRAVIATVPLAYER",
    "MEDIAPLAYER",
    "NETFLIX",
    "SPOTIFY",
    "TWITCH",
    "YOUTUBE",
}
class AdvisorUnavailableError(RuntimeError):
    """The authenticated owner's private library cannot currently be read."""


class AdvisorOwnerMismatchError(PermissionError):
    """A private library was requested for someone other than the token owner."""


def _cache_key(online_id: str, npsso: str) -> str:
    identity = f"{online_id.casefold()}\0{npsso}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    # v6 invalidates older serialized Advisor libraries so newly classified
    # trials, bonus content, and media apps disappear without manual cleanup.
    return f"psn_advisor_library_v6/{digest}"


def _response_json(response) -> dict:
    if isinstance(response, dict):
        return response
    return response.json()


def _fetch_library_pages(authenticator) -> list[dict]:
    games: list[dict] = []
    offset = 0

    for _page in range(100):
        variables = {
            "isActive": True,
            "platform": ["ps3", "ps4", "ps5"],
            "start": offset,
            "size": _LIBRARY_PAGE_SIZE,
            "sortBy": "ACTIVE_DATE",
            "sortDirection": "desc",
        }
        extensions = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": _LIBRARY_QUERY_HASH,
            }
        }
        response = authenticator.get(
            url=_LIBRARY_URL,
            params={
                "operationName": _LIBRARY_OPERATION,
                "variables": json.dumps(variables, separators=(",", ":")),
                "extensions": json.dumps(extensions, separators=(",", ":")),
            },
            headers={"x-apollo-operation-name": "pn_psn"},
        )
        payload = _response_json(response)
        node = ((payload.get("data") or {}).get("purchasedTitlesRetrieve") or {})
        page_games = node.get("games")
        page_info = node.get("pageInfo")
        if not isinstance(page_games, list) or not isinstance(page_info, dict):
            errors = payload.get("errors") or []
            detail = errors[0].get("message") if errors and isinstance(errors[0], dict) else None
            raise AdvisorUnavailableError(
                detail or "Sony's library response did not contain games and paging information."
            )

        games.extend(game for game in page_games if isinstance(game, dict))
        if page_info.get("isLast") is True:
            return games

        next_offset = int(page_info.get("offset", offset)) + int(
            page_info.get("size", len(page_games))
        )
        if next_offset <= offset:
            raise AdvisorUnavailableError("Sony's library paging offset did not advance.")
        offset = next_offset

    raise AdvisorUnavailableError("Sony's library exceeded the paging safety limit.")


def _trophy_total(trophy_set) -> int | None:
    if trophy_set is None:
        return None
    values = [getattr(trophy_set, grade, None) for grade in ("platinum", "gold", "silver", "bronze")]
    if not any(isinstance(value, int) for value in values):
        return None
    return sum(value for value in values if isinstance(value, int))


def _earned_platinum(trophy_title) -> int | None:
    if trophy_title is None:
        return None
    earned = getattr(trophy_title, "earned_trophies", None)
    value = getattr(earned, "platinum", None)
    return value if isinstance(value, int) and value >= 0 else None


def _best_name_match(name: str, platform: str, candidates: list, name_getter, platform_getter):
    ranked: list[tuple[float, object]] = []
    for candidate in candidates:
        candidate_platform = platform_getter(candidate)
        if platform != "UNKNOWN" and candidate_platform and candidate_platform != platform:
            continue
        score = _game_name_score(name, name_getter(candidate))
        ranked.append((score, candidate))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked:
        return None
    best_score, best = ranked[0]
    runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
    if best_score >= 0.82 and (best_score >= 0.99 or best_score - runner_up >= 0.08):
        return best
    return None


def _source(raw: dict) -> str:
    membership = str(raw.get("membership") or "").upper()
    subscription = str(raw.get("subscriptionService") or "").upper()
    if membership == "PS_PLUS" or subscription not in {"", "NONE", "NULL"}:
        return "ps_plus"
    if membership in {"", "NONE"}:
        return "purchased"
    return "other"


def _is_trial_game(raw: dict) -> bool:
    name = str(raw.get("name") or "").strip()
    if "resident evil 7 teaser" in name.casefold():
        return True
    if _TRIAL_TITLE.search(name) or _BETA_TITLE.search(name):
        return True
    for field in (
        "productType",
        "entitlementType",
        "packageType",
        "gameType",
        "type",
        "membership",
    ):
        value = str(raw.get(field) or "").strip().upper().replace("-", "_")
        if value in _TRIAL_VALUES:
            return True
    return False


def _is_non_game_content(raw: dict) -> bool:
    """Identify add-on entitlements that cannot be chosen as a standalone game."""
    name = str(raw.get("name") or "").strip()
    if name.casefold() in _NON_GAME_EXACT_TITLES:
        return True
    if _NON_GAME_CONTENT_TITLE.search(name):
        return True
    product_identity = " ".join(
        str(raw.get(field) or "").upper()
        for field in ("titleId", "productId", "conceptId")
    )
    if any(marker in product_identity for marker in _NON_GAME_PRODUCT_MARKERS):
        return True
    for field in ("productType", "entitlementType", "packageType", "gameType", "type"):
        value = str(raw.get(field) or "").strip().upper().replace("-", "_")
        if value in _NON_GAME_CONTENT_VALUES:
            return True
    return False


def _exact_platinum_match(names: list[str], trophy_titles: list):
    """Find an earned platinum for the same title, regardless of console stack."""
    usable_names = [name for name in names if name]
    for trophy_title in trophy_titles:
        if not (_earned_platinum(trophy_title) or 0) > 0:
            continue
        trophy_name = str(getattr(trophy_title, "title_name", "") or "")
        if any(_game_name_score(name, trophy_name) >= 0.99 for name in usable_names):
            return trophy_title
    return None


def _merge_cross_platform_games(games: list[AdvisorGame]) -> tuple[list[AdvisorGame], int]:
    """Collapse cross-gen entitlements while retaining the edition to continue."""
    groups: list[list[AdvisorGame]] = []
    for game in games:
        matched_group = None
        for group in groups:
            exemplar = group[0]
            same_product = bool(
                game.product_id
                and exemplar.product_id
                and game.product_id.casefold() == exemplar.product_id.casefold()
            )
            same_concept = bool(
                game.concept_id
                and exemplar.concept_id
                and game.concept_id.casefold() == exemplar.concept_id.casefold()
            )
            cross_platform = any(member.platform != game.platform for member in group)
            if (
                (same_product or same_concept)
                and cross_platform
                and _game_name_score(game.name, exemplar.name) >= 0.82
            ):
                matched_group = group
                break
        if matched_group is None:
            groups.append([game])
        else:
            matched_group.append(game)

    status_rank = {"unplayed": 0, "in_progress": 1, "completed": 2}
    platform_rank = {"UNKNOWN": 0, "PS3": 1, "PS4": 2, "PS5": 3}
    platform_order = {"PS5": 0, "PS4": 1, "PS3": 2, "UNKNOWN": 3}
    merged: list[AdvisorGame] = []
    merged_platform_count = 0
    for group in groups:
        primary = max(
            group,
            key=lambda game: (
                status_rank[game.status],
                game.progress if game.progress is not None else -1,
                game.playtime_seconds if game.playtime_seconds is not None else -1,
                platform_rank[game.platform],
            ),
        )
        available_platforms = sorted(
            {
                platform
                for game in group
                for platform in (game.available_platforms or [game.platform])
            },
            key=platform_order.__getitem__,
        )
        autopop_game = next(
            (game for game in group if game.ps4_to_ps5_autopop is not None),
            None,
        )
        autopop_update = {}
        if autopop_game is not None:
            autopop_update = {
                "ps4_to_ps5_autopop": autopop_game.ps4_to_ps5_autopop,
                "autopop_note": autopop_game.autopop_note,
                "autopop_source_url": autopop_game.autopop_source_url,
                "autopop_verified_at": autopop_game.autopop_verified_at,
            }
        elif {"PS4", "PS5"}.issubset(available_platforms):
            autopop_update = {
                "ps4_to_ps5_autopop": "unknown",
                "autopop_note": "目前沒有足夠可靠的 PS4→PS5 自動跳杯資料。",
                "autopop_verified_at": "2026-08-25",
            }
        merged.append(
            primary.model_copy(
                update={
                    "available_platforms": available_platforms,
                    "library_index": min(game.library_index for game in group),
                    "ps4_platinum_earned": any(
                        game.ps4_platinum_earned for game in group
                    ),
                    **autopop_update,
                }
            )
        )
        merged_platform_count += len(group) - 1
    merged.sort(key=lambda game: game.library_index)
    return merged, merged_platform_count


def _build_games(
    raw_games: list[dict],
    playtime_entries: list[dict],
    trophy_titles: list,
) -> tuple[list[AdvisorGame], int, int, int]:
    stats_by_title_id = {
        str(entry.get("title_id") or "").upper(): entry
        for entry in playtime_entries
        if entry.get("title_id")
    }
    unique: dict[str, dict] = {}
    excluded_trial_count = 0
    excluded_content_count = 0
    for raw in raw_games:
        title_id = str(raw.get("titleId") or "").strip().upper()
        name = str(raw.get("name") or "").strip()
        if title_id and name and title_id not in unique and _is_trial_game(raw):
            excluded_trial_count += 1
            continue
        if title_id and name and title_id not in unique and _is_non_game_content(raw):
            excluded_content_count += 1
            continue
        if title_id and name and title_id not in unique:
            unique[title_id] = raw

    games: list[AdvisorGame] = []
    excluded_platinum_count = 0
    for library_index, (title_id, raw) in enumerate(unique.items()):
        name = str(raw.get("name") or "").strip()
        raw_platform = str(raw.get("platform") or "").upper()
        platform = raw_platform if raw_platform in _SUPPORTED_PLATFORMS else "UNKNOWN"

        stat = stats_by_title_id.get(title_id)
        if stat is None:
            stat = _best_name_match(
                name,
                platform,
                playtime_entries,
                lambda entry: str(entry.get("name") or ""),
                lambda entry: str(entry.get("platform") or ""),
            )
        match_names = [name]
        if stat is not None:
            stat_name = str(stat.get("name") or "").strip()
            if stat_name and stat_name not in match_names:
                match_names.append(stat_name)

        trophy_title = None
        for match_name in match_names:
            trophy_title = _best_name_match(
                match_name,
                platform,
                trophy_titles,
                lambda title: str(getattr(title, "title_name", "") or ""),
                _trophy_title_platform,
            )
            if trophy_title is not None:
                break
        platinum_title = _exact_platinum_match(match_names, trophy_titles)
        earned_platinum = _earned_platinum(trophy_title)
        autopop_info = get_autopop_info(*match_names)
        platinum_platform = (
            _trophy_title_platform(platinum_title) if platinum_title is not None else None
        )
        ps4_platinum_opportunity = bool(
            platform == "PS5"
            and platinum_platform == "PS4"
            and not (earned_platinum or 0) > 0
            and autopop_info is not None
            and autopop_info.status in {"full", "partial"}
        )
        if (earned_platinum or 0) > 0 or (
            platinum_title is not None and not ps4_platinum_opportunity
        ):
            excluded_platinum_count += 1
            continue

        progress = getattr(trophy_title, "progress", None) if trophy_title else None
        progress = progress if isinstance(progress, int) and 0 <= progress <= 100 else None
        playtime_seconds = int(stat["seconds"]) if stat and stat.get("seconds") is not None else None
        played = stat is not None or trophy_title is not None or bool(progress)
        status = "completed" if progress == 100 else "in_progress" if played else "unplayed"
        image = raw.get("image") if isinstance(raw.get("image"), dict) else {}

        games.append(
            AdvisorGame(
                title_id=title_id,
                product_id=str(raw.get("productId") or "") or None,
                concept_id=str(raw.get("conceptId") or "") or None,
                name=name,
                platform=platform,
                available_platforms=(
                    ["PS5", "PS4"] if ps4_platinum_opportunity else [platform]
                ),
                image_url=str(image.get("url") or "") or None,
                source=_source(raw),
                is_downloadable=bool(raw.get("isDownloadable")),
                is_preorder=bool(raw.get("isPreOrder")),
                library_index=library_index,
                played=played,
                status=status,
                progress=progress,
                playtime_seconds=playtime_seconds,
                earned_trophies=_trophy_total(getattr(trophy_title, "earned_trophies", None)),
                defined_trophies=_trophy_total(getattr(trophy_title, "defined_trophies", None)),
                earned_platinum=earned_platinum,
                trophy_title=(str(getattr(trophy_title, "title_name", "") or "") or None),
                ps4_platinum_earned=ps4_platinum_opportunity,
                ps4_to_ps5_autopop=(
                    autopop_info.status if autopop_info is not None else None
                ),
                autopop_note=(autopop_info.note if autopop_info is not None else None),
                autopop_source_url=(
                    autopop_info.source_url if autopop_info is not None else None
                ),
                autopop_verified_at=(
                    autopop_info.verified_at if autopop_info is not None else None
                ),
            )
        )
    return games, excluded_trial_count, excluded_content_count, excluded_platinum_count


def _filter_cached_games(data: AdvisorLibrary) -> AdvisorLibrary:
    without_trials = [
        game for game in data.games if not _is_trial_game({"name": game.name})
    ]
    removed_trials = len(data.games) - len(without_trials)
    without_content = [
        game
        for game in without_trials
        if not _is_non_game_content({"name": game.name})
    ]
    removed_content = len(without_trials) - len(without_content)
    without_platinums = [game for game in without_content if not game.earned_platinum]
    removed_platinums = len(without_content) - len(without_platinums)
    kept, merged_platforms = _merge_cross_platform_games(without_platinums)
    if removed_trials or removed_content or removed_platinums or merged_platforms:
        data.games = kept
        data.excluded_trial_count += removed_trials
        data.excluded_content_count += removed_content
        data.excluded_platinum_count += removed_platinums
        data.merged_platform_count += merged_platforms
        data.total_count = len(kept)
        data.unplayed_count = sum(game.status == "unplayed" for game in kept)
        data.in_progress_count = sum(game.status == "in_progress" for game in kept)
        data.completed_count = sum(game.status == "completed" for game in kept)
    data.title_resolver = "gemini" if settings.gemini_api_key else "source_title"
    return data


def get_advisor_library(
    username: str,
    *,
    force: bool = False,
    cache: FileCache | None = None,
    npsso: str | None = None,
) -> AdvisorLibrary:
    username = (username or "").strip()
    npsso = npsso or settings.psn_npsso
    if not npsso:
        raise AdvisorUnavailableError("PSN_NPSSO is not configured.")

    cache = cache or FileCache(settings.cache_dir)
    requested_key = _cache_key(username, npsso)
    if not force:
        cached = cache.load(requested_key, _LIBRARY_TTL)
        if cached is not None:
            data = _filter_cached_games(AdvisorLibrary.model_validate(cached))
            if data.username.casefold() == username.casefold():
                data.cache_status = "cached"
                modified_at = cache.modified_at(requested_key)
                if modified_at is not None:
                    data.fetched_at = datetime.fromtimestamp(modified_at, timezone.utc).isoformat()
                return data

    try:
        me = _client(npsso)
        online_id = str(me.online_id)
    except Exception as exc:
        raise AdvisorUnavailableError("The PSN login is unavailable or the NPSSO may have expired.") from exc

    if username.casefold() != online_id.casefold():
        raise AdvisorOwnerMismatchError(
            "The complete PlayStation library is private to the configured NPSSO owner."
        )

    key = _cache_key(online_id, npsso)

    try:
        raw_games = _fetch_library_pages(me.authenticator)
        playtime_entries = _playtime_from_title_stats(me, online_id, cache)
        try:
            trophy_titles = list(me.trophy_titles())
        except Exception as exc:
            logger.info("Advisor trophy progress unavailable: %s", exc)
            trophy_titles = []
    except AdvisorUnavailableError:
        raise
    except Exception as exc:
        raise AdvisorUnavailableError("Sony's library API could not be read.") from exc

    games, excluded_trial_count, excluded_content_count, excluded_platinum_count = _build_games(
        raw_games,
        playtime_entries,
        trophy_titles,
    )
    games, merged_platform_count = _merge_cross_platform_games(games)
    data = AdvisorLibrary(
        username=online_id,
        games=games,
        total_count=len(games),
        unplayed_count=sum(game.status == "unplayed" for game in games),
        in_progress_count=sum(game.status == "in_progress" for game in games),
        completed_count=sum(game.status == "completed" for game in games),
        excluded_trial_count=excluded_trial_count,
        excluded_content_count=excluded_content_count,
        excluded_platinum_count=excluded_platinum_count,
        merged_platform_count=merged_platform_count,
        cache_status="live",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        title_resolver="gemini" if settings.gemini_api_key else "source_title",
    )
    cache.save(key, data.model_dump())
    return data


def get_advisor_signals_batch(
    candidates: list[AdvisorCandidate],
    *,
    cache: FileCache | None = None,
    cache_only: bool = False,
) -> list[AdvisorSignalResult]:
    """Enrich a bounded batch, retrying unmatched titles once with Gemini."""
    cache = cache or FileCache(settings.cache_dir)
    logger.info(
        "Advisor analysis batch start count=%d cache_only=%s",
        len(candidates),
        cache_only,
    )
    results: list[AdvisorSignalResult] = []
    retry_candidates: list[tuple[int, AdvisorCandidate, TitleResolution]] = []
    terminal_error: str | None = None
    resolutions = resolve_advisor_titles(
        candidates,
        cache=cache,
        allow_api=not cache_only,
    )
    bundle_resolutions = resolve_advisor_bundles(
        candidates,
        {
            key: resolution.search_title
            for key, resolution in resolutions.items()
        },
        cache=cache,
        allow_api=not cache_only,
    )

    def to_signals(data: dict | None) -> PsnprofilesAdvisorSignals | None:
        if data is None:
            return None
        return PsnprofilesAdvisorSignals(
            title=str(data["title"]),
            platform=str(data.get("platform") or ""),
            game_url=str(data["game_url"]),
            owners=data.get("owners"),
            average_completion=data.get("average_completion"),
            platinum_achievers=data.get("platinum_achievers"),
            platinum_rate=data.get("platinum_rate"),
        )

    session_context = nullcontext(None) if cache_only else create_session()
    with session_context as session:
        for candidate in candidates:
            if terminal_error is not None:
                results.append(
                    AdvisorSignalResult(
                        game=candidate.game,
                        platform=candidate.platform,
                        error=terminal_error,
                    )
                )
                continue
            resolution = resolutions[candidate_key(candidate)]
            logger.info(
                "Advisor title resolved original=%r resolved=%r platform=%s source=%s trial=%s cache_only=%s",
                candidate.game,
                resolution.search_title,
                candidate.platform or "UNKNOWN",
                resolution.source,
                resolution.is_trial,
                cache_only,
            )
            bundle_resolution = bundle_resolutions.get(candidate_key(candidate))
            if bundle_resolution is not None:
                logger.info(
                    "Advisor analysis bundle title=%r platform=%s source=%s children=%d",
                    resolution.search_title,
                    candidate.platform or "UNKNOWN",
                    bundle_resolution.source,
                    len(bundle_resolution.children),
                )
                if bundle_resolution.error:
                    results.append(
                        AdvisorSignalResult(
                            game=candidate.game,
                            platform=candidate.platform,
                            error=bundle_resolution.error,
                        )
                    )
                    continue
                bundle_children: list[AdvisorBundleChildResult] = []
                bundle_error: str | None = None
                try:
                    for child in bundle_resolution.children:
                        child_data = get_psnprofiles_trophies(
                            child.game,
                            child.platform,
                            search_aliases=[],
                            cache_only=cache_only,
                            cache=cache,
                            session=session,
                        )
                        child_signals = to_signals(child_data)
                        bundle_children.append(
                            AdvisorBundleChildResult(
                                game=child.game,
                                platform=child.platform,
                                signals=child_signals,
                                error=(
                                    None
                                    if child_signals is not None or cache_only
                                    else "找不到相符的 PSNProfiles 獎盃列表。"
                                ),
                            )
                        )
                except PSNProfilesFetchError as exc:
                    logger.warning(
                        "Advisor bundle browser failure title=%r error=%s",
                        resolution.search_title,
                        exc,
                    )
                    terminal_error = (
                        "PSNProfiles 瀏覽器載入失敗，請確認可見的 Chrome 視窗已完成驗證。"
                    )
                    bundle_error = terminal_error
                except Exception as exc:
                    logger.exception(
                        "Advisor bundle analysis unexpected failure title=%r: %s",
                        resolution.search_title,
                        exc,
                    )
                    bundle_error = "目前無法取得這個合集的 PSNProfiles 資料。"
                results.append(
                    AdvisorSignalResult(
                        game=candidate.game,
                        platform=candidate.platform,
                        bundle=AdvisorBundleResult(
                            source=bundle_resolution.source,
                            source_urls=list(bundle_resolution.source_urls),
                            verified_at=bundle_resolution.verified_at,
                            children=bundle_children,
                            complete=(
                                bundle_error is None
                                and len(bundle_children)
                                == len(bundle_resolution.children)
                                and all(
                                    child.signals is not None
                                    for child in bundle_children
                                )
                            ),
                        ),
                        error=bundle_error,
                    )
                )
                continue
            if resolution.is_trial:
                results.append(
                    AdvisorSignalResult(
                        game=candidate.game,
                        platform=candidate.platform,
                        error="已排除試玩版、Demo、Beta 或測試版本。",
                        retryable=False,
                    )
                )
                continue
            if not is_english_search_title(resolution.search_title):
                message = resolution.error
                if not settings.gemini_api_key:
                    message = "請先在 .env 設定 GEMINI_API_KEY，以解析英文遊戲名稱。"
                results.append(
                    AdvisorSignalResult(
                        game=candidate.game,
                        platform=candidate.platform,
                        error=message or "找不到可用的英文遊戲名稱。",
                    )
                )
                continue
            try:
                # PSNProfiles search is substantially more reliable with its
                # English catalogue titles. Localized library names remain
                # useful for matching/cache validation, but must never become
                # a visible browser search fallback.
                search_aliases = [
                    alias
                    for alias in [candidate.game, *candidate.aliases]
                    if is_english_search_title(alias)
                ]
                data = get_psnprofiles_trophies(
                    resolution.search_title,
                    candidate.platform,
                    search_aliases=search_aliases,
                    cache_only=cache_only,
                    cache=cache,
                    session=session,
                )
                signals = to_signals(data)
                if not cache_only and signals is None:
                    logger.warning(
                        "Advisor analysis no PSNProfiles match original=%r resolved=%r platform=%s",
                        candidate.game,
                        resolution.search_title,
                        candidate.platform or "UNKNOWN",
                    )
                results.append(
                    AdvisorSignalResult(
                        game=candidate.game,
                        platform=candidate.platform,
                        signals=signals,
                    )
                )
                if not cache_only and data is None and settings.gemini_api_key:
                    retry_candidates.append((len(results) - 1, candidate, resolution))
            except PSNProfilesFetchError as exc:
                logger.warning(
                    "Advisor analysis browser failure original=%r resolved=%r platform=%s error=%s",
                    candidate.game,
                    resolution.search_title,
                    candidate.platform or "UNKNOWN",
                    exc,
                )
                terminal_error = (
                    "PSNProfiles 未能完成載入，目前仍可使用 PSN 官方收藏庫資料。"
                )
                results.append(
                    AdvisorSignalResult(
                        game=candidate.game,
                        platform=candidate.platform,
                        error=terminal_error,
                    )
                )
            except Exception as exc:
                logger.exception(
                    "Advisor analysis unexpected failure original=%r resolved=%r platform=%s: %s",
                    candidate.game,
                    resolution.search_title,
                    candidate.platform or "UNKNOWN",
                    exc,
                )
                results.append(
                    AdvisorSignalResult(
                        game=candidate.game,
                        platform=candidate.platform,
                        error="目前無法取得這款遊戲的 PSNProfiles 資料。",
                    )
                )
        if retry_candidates and terminal_error is None and settings.gemini_api_key:
            retry_input = [candidate for _, candidate, _ in retry_candidates]
            retry_attempts = {
                candidate_key(candidate): resolution.search_title
                for _, candidate, resolution in retry_candidates
            }
            retry_resolutions = resolve_advisor_titles(
                retry_input,
                cache=cache,
                allow_api=True,
                retry_attempts=retry_attempts,
            )
            logger.info(
                "Advisor fallback title lookup start unresolved=%d",
                len(retry_candidates),
            )
            for result_index, candidate, first_resolution in retry_candidates:
                retry_resolution = retry_resolutions[candidate_key(candidate)]
                if (
                    retry_resolution.error
                    or retry_resolution.is_trial
                    or not is_english_search_title(retry_resolution.search_title)
                    or retry_resolution.search_title.casefold()
                    == first_resolution.search_title.casefold()
                ):
                    continue
                retry_aliases = [
                    alias
                    for alias in [
                        candidate.game,
                        first_resolution.search_title,
                        *candidate.aliases,
                    ]
                    if is_english_search_title(alias)
                ]
                try:
                    retry_data = get_psnprofiles_trophies(
                        retry_resolution.search_title,
                        candidate.platform,
                        search_aliases=retry_aliases,
                        cache_only=False,
                        cache=cache,
                        session=session,
                    )
                except Exception as exc:
                    logger.warning(
                        "Advisor fallback PSNProfiles lookup failed original=%r attempted=%r fallback=%r error=%s",
                        candidate.game,
                        first_resolution.search_title,
                        retry_resolution.search_title,
                        exc,
                    )
                    continue
                retry_signals = to_signals(retry_data)
                if retry_signals is None:
                    logger.info(
                        "Advisor fallback title still had no safe PSNProfiles match original=%r attempted=%r fallback=%r",
                        candidate.game,
                        first_resolution.search_title,
                        retry_resolution.search_title,
                    )
                    continue
                results[result_index] = AdvisorSignalResult(
                    game=candidate.game,
                    platform=candidate.platform,
                    signals=retry_signals,
                )
                logger.info(
                    "Advisor fallback recovered PSNProfiles match original=%r attempted=%r fallback=%r",
                    candidate.game,
                    first_resolution.search_title,
                    retry_resolution.search_title,
                )
    logger.info(
        "Advisor analysis batch complete count=%d matched=%d failed=%d cache_only=%s",
        len(results),
        sum(
            result.signals is not None
            or (
                result.bundle is not None
                and any(
                    child.signals is not None
                    for child in result.bundle.children
                )
            )
            for result in results
        ),
        sum(result.signals is None and result.bundle is None for result in results),
        cache_only,
    )
    return results
