from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException


class VultureDownloader(AmuseLabsDownloader):
    command = "vult"
    outlet = "Vulture"
    outlet_prefix = "Vulture"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.archive_url = "https://www.vulture.com/tags/vulture-10x10/"

    @classmethod
    def matches_url(cls, url_components):
        return (
            "vulture.com" in url_components.netloc
            and "/article/daily-crossword-puzzle" in url_components.path
        )

    def find_latest(self) -> str:
        res = self.session.get(self.archive_url)
        if not res.ok:
            raise XWordDLException(
                f"Could not connect to Vulture index at {self.archive_url}"
            )

        soup = BeautifulSoup(res.text, features="lxml")

        first_tile = soup.find("li", attrs={"class": "article"})

        if not (isinstance(first_tile, Tag)):
            raise XWordDLException("Unable to find latest Vulture puzzle")

        link = first_tile.find("a")

        if not (isinstance(link, Tag)):
            raise XWordDLException("Puzzle link not found in expected place")

        url = str(link.get("href"))

        return url

    def find_by_date(self, dt):
        url_format = f"{dt:%B-{dt.day}-%Y}".lower()
        guessed_url = (
            f"https://www.vulture.com/article/daily-crossword-puzzle-{url_format}.html"
        )
        res = self.session.head(guessed_url)
        if res.status_code == 404:
            raise XWordDLException(
                f"No page found for the specified date (tried {guessed_url})"
            )

        return guessed_url

    def find_solver(self, url):
        try:
            parsed_url = urlparse(url)
            slug = parsed_url.path.split("/")[-1].removesuffix(".html")
            date_section = "-".join(slug.split("-")[-3:])
            self.date = datetime.strptime(date_section, "%B-%d-%Y")
        except Exception:
            pass

        res = self.session.get(url)
        if not res.ok:
            raise XWordDLException(f"Connection error: status code {res.status_code}")

        solver_url = self.matches_embed_pattern(page_source=res.text)

        if not solver_url:
            raise XWordDLException("Can't find latest Vulture puzzle.")

        return solver_url
