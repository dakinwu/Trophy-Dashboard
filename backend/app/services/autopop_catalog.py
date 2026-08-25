"""Curated PS4-to-PS5 trophy inheritance facts for owned cross-gen games.

This is deliberately local and source-backed: cross-buy or save transfer alone
does not prove that trophies auto-unlock. Unknown games stay unknown rather than
being optimistically classified.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.psn_service import _game_name_score

AutopopStatus = Literal["full", "partial", "none", "unknown"]


@dataclass(frozen=True)
class AutopopInfo:
    status: AutopopStatus
    note: str
    source_url: str | None
    aliases: tuple[str, ...]
    verified_at: str = "2026-08-25"


_NODE_GAMERS = "https://nodegamers.com/list-of-auto-pop-ps5-platinum-trophies/"
_PLEY_AGAIN = "https://www.pley-again.com/2023/12/jeux-ps4-ps5-mise-a-niveau-sauvegardes-transferables-et-auto-pop/"


_CATALOG: tuple[AutopopInfo, ...] = (
    AutopopInfo("full", "可透過遊戲內存檔轉移完整跳出獎盃，包含 DLC。", _NODE_GAMERS, ("Dying Light 2: Stay Human",)),
    AutopopInfo("partial", "只有 Ultimate Team、VOLTA 等共享進度可能帶動部分獎盃，不能視為完整白金。", "https://forums.ea.com/discussions/fc-24-general-discussion-en/re-cross-progression/7692499", ("EA SPORTS FC 24",)),
    AutopopInfo("none", "PS4 與 PS5 沒有存檔轉移或自動跳杯。", "https://www.giga.de/tipp/saints-row-2022-alle-trophaeen-erfolge-leitfaden-fuer-100/", ("Saints Row",)),
    AutopopInfo("unknown", "目前沒有足夠可靠的 PS4→PS5 自動跳杯資料。", None, ("SpongeBob SquarePants: The Cosmic Shake", "海綿寶寶 : The Cosmic Shake")),
    AutopopInfo("none", "兩個世代版本彼此獨立，沒有已確認的存檔轉移或自動跳杯。", "https://gamefaqs.gamespot.com/boards/264562-playstation-5/81095065", ("Disney Epic Mickey: Rebrushed",)),
    AutopopInfo("partial", "只確認少量累積型獎盃會在完成一次相關動作後跳出。", _NODE_GAMERS, ("Evil Dead: The Game",)),
    AutopopInfo("none", "官方說明確認 PS4 與 PS5 版本不共用存檔。", "https://legogamessupport.wbgames.com/hc/en-us/articles/5179918833043-How-Do-I-Upgrade-My-PlayStation-4-Version-Of-The-Game-To-PlayStation-5", ("LEGO Star Wars: The Skywalker Saga", "LEGO® Star Wars™ : 天行者傳奇")),
    AutopopInfo("partial", "累積型獎盃通常需再做一次動作；情境型獎盃需要重解。", _NODE_GAMERS, ("Among Us",)),
    AutopopInfo("full", "伺服器進度可完整同步並自動跳杯。", _NODE_GAMERS, ("Diablo IV", "《暗黑破壞神 IV》")),
    AutopopInfo("unknown", "目前沒有足夠可靠的 PS4→PS5 自動跳杯資料。", None, ("EA SPORTS FC 26",)),
    AutopopInfo("unknown", "跨平台遊玩不等於獎盃繼承，目前沒有可靠的完整自動跳杯證據。", None, ("Chivalry 2",)),
    AutopopInfo("none", "已確認不支援 PS4→PS5 自動跳杯。", _PLEY_AGAIN, ("Godfall: Challenger Edition", "Godfall")),
    AutopopInfo("partial", "只確認排名相關的一座獎盃能在再次升級後跳出。", _NODE_GAMERS, ("THE KING OF FIGHTERS XV", "King of Fighters XV")),
    AutopopInfo("partial", "可帶出部分等級與地點相關獎盃，但無法完整自動白金。", _NODE_GAMERS, ("Borderlands 3", "邊緣禁地®3")),
    AutopopInfo("partial", "只有 MyFACTION 類獎盃可在完成一場比賽後帶出，沒有完整存檔轉移。", "https://www.powerpyx.com/wwe-2k24-trophy-guide-roadmap/", ("WWE 2K24",)),
    AutopopInfo("full", "登入伺服器後可完整自動跳杯，亦包含 DLC。", _NODE_GAMERS, ("The Elder Scrolls Online", "Elder Scrolls Online")),
    AutopopInfo("none", "兩套獎盃需分開完成，未確認有獎盃繼承。", "https://note.com/agile_robin8722/n/ne50a608334c8", ("Totally Accurate Battle Simulator",)),
    AutopopInfo("none", "PS4 存檔不能匯入 PS5 版本。", "https://gamefaqs.gamespot.com/boards/256516-subnautica-below-zero/79461779", ("Subnautica Below Zero",)),
    AutopopInfo("none", "獎盃與遊戲進度都不會在 PS4／PS5 版本間繼承。", "https://www.playstationtrophies.org/game/mlb-the-show-24/guide/", ("MLB The Show 24", "MLB® The Show™ 24")),
    AutopopInfo("full", "支援 PS4→PS5 完整自動跳杯。", _NODE_GAMERS, ("SCARLET NEXUS", "緋紅結繫")),
    AutopopInfo("full", "匯入 PS4 存檔後可完整自動跳杯，亦包含 DLC。", _NODE_GAMERS, ("Resident Evil 4",)),
    AutopopInfo("full", "透過遊戲內存檔轉移可完整自動跳杯，亦包含 DLC。", _NODE_GAMERS, ("Tales of Arise", "破曉傳奇")),
    AutopopInfo("partial", "可匯入 PS4 存檔並跳出大部分獎盃，仍有少量獎盃需要補解。", _NODE_GAMERS, ("Nioh 2", "Nioh 2 Remastered", "仁王２ Remastered", "仁王2 Remastered")),
    AutopopInfo("none", "PS4 存檔無法交給 PS5 版本使用，因此不能自動跳杯。", "https://www.reddit.com/r/TunicGame/comments/15p00pb/transfer_ps4_save_to_ps5/", ("Tunic",)),
    AutopopInfo("none", "Enhanced Edition 無法讀取 PS4 版存檔。", "https://www.reddit.com/r/LittleNightmares2/comments/pcblea/ps5_enhanced_edition_upgrade/", ("Little Nightmares II", "Little Nightmares II 小小夢魘2")),
    AutopopInfo("unknown", "目前找不到足夠可靠的 PS4→PS5 存檔與獎盃繼承證據。", None, ("Viewfinder",)),
)


def get_autopop_info(*names: str) -> AutopopInfo | None:
    usable_names = [name for name in names if name]
    best: tuple[float, AutopopInfo] | None = None
    for info in _CATALOG:
        score = max(
            (_game_name_score(name, alias) for name in usable_names for alias in info.aliases),
            default=0.0,
        )
        if score >= 0.82 and (best is None or score > best[0]):
            best = (score, info)
    return best[1] if best is not None else None
