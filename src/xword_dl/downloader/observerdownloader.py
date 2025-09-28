import re
import urllib.parse

import dateparser

from bs4 import BeautifulSoup, Tag

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException


class ObserverDownloader(AmuseLabsDownloader):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # These must be set by subclasses
        self.landing_page_url = ""
        self.article_url_string = ""

    def find_latest(self):
        res = self.session.get(self.landing_page_url)
        soup = BeautifulSoup(res.text, features="lxml")

        links = [
            str(link.get("href"))
            for link in soup.find_all("a")
            if isinstance(link, Tag)
        ]
        latest_link = next(link for link in links if self.article_url_string in link)

        latest_abs_url = urllib.parse.urljoin("https://observer.co.uk", latest_link)

        return latest_abs_url

    def find_solver(self, url):
        solver_url = super().matches_embed_pattern(url)
        if not solver_url:
            raise XWordDLException(f"Unable to find a puzzle at {url}")
        return solver_url

    def parse_xword(self, xw_data):
        puzzle = super().parse_xword(xw_data)

        guessed_date_match = re.search(r"\((.+)\)", puzzle.title)
        if guessed_date_match:
            self.date = dateparser.parse(guessed_date_match.groups()[0])

        return puzzle


class EverymanDownloader(ObserverDownloader):
    command = "ever"
    outlet = "Observer"
    outlet_prefix = "Observer"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.landing_page_url = "https://observer.co.uk/topics/everyman"
        self.article_url_string = "/puzzles/everyman/article"

    @classmethod
    def matches_url(cls, url_components):
        return (
            "observer.co.uk" in url_components.netloc
            and "/puzzles/everyman/article" in url_components.path
        )


class SpeedyDownloader(ObserverDownloader):
    command = "spdy"
    outlet = "Observer"
    outlet_prefix = "Observer"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.landing_page_url = "https://observer.co.uk/topics/speedy"
        self.article_url_string = "/puzzles/speedy/article"

    @classmethod
    def matches_url(cls, url_components):
        return (
            "observer.co.uk" in url_components.netloc
            and "/puzzles/speedy/article" in url_components.path
        )
