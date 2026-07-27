from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400 and self.status_code != 404:
            import requests
            raise requests.exceptions.HTTPError(f"status {self.status_code}")


class FakeSession:
    """Mimics the requests-like subset used by the nodriver fetch facade."""

    def __init__(self, summary_html: str = "", log_pages: list[str] | None = None):
        self.summary_html = summary_html
        self.log_pages = list(log_pages or [])
        self.headers: dict[str, str] = {}
        self._page_idx = 0

    def get(self, url: str, timeout: float | None = None) -> FakeResponse:
        if "/log?page=" in url:
            if self._page_idx < len(self.log_pages):
                html = self.log_pages[self._page_idx]
                self._page_idx += 1
                return FakeResponse(html, 200)
            return FakeResponse("", 404)
        return FakeResponse(self.summary_html, 200)
