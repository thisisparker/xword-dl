import json
import urllib.parse

import dateparser
import requests

from bs4 import BeautifulSoup, Tag

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException


class NewYorkerDownloader(AmuseLabsDownloader):
    command = "tny"
    outlet = "New Yorker"
    outlet_prefix = "New Yorker"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = (
            "https://cdn3.amuselabs.com/tny/crossword?id={puzzle_id}&set=tny-weekly"
        )

        self.theme_title = ""

    @classmethod
    def matches_url(cls, url_components):
        return (
            "newyorker.com" in url_components.netloc
            and "/puzzles-and-games-dept/crossword" in url_components.path
        )

    def find_by_date(self, dt):
        url_format = dt.strftime("%Y/%m/%d")
        guessed_url = urllib.parse.urljoin(
            "https://www.newyorker.com/puzzles-and-games-dept/crossword/", url_format
        )
        return guessed_url

    def find_latest(self, search_string="/crossword/"):
        url = "https://www.newyorker.com/puzzles-and-games-dept/crossword"
        res = self.session.get(url)
        if not res.ok:
            raise XWordDLException("Could not fetch latest crossword URL.")

        soup = BeautifulSoup(res.text, "html.parser")

        json_tag = soup.find("script", attrs={"type": "application/ld+json"})
        if not isinstance(json_tag, Tag):
            raise XWordDLException("Could not find metadata tag for latest crossword.")

        json_str = json_tag.get_text()
        puzzle_list = json.loads(json_str).get("itemListElement", {})
        latest_url = next(
            (item for item in puzzle_list if search_string in item.get("url", "")), {}
        ).get("url")

        if not latest_url:
            raise XWordDLException(
                "Could not identify the latest puzzle at {}".format(url)
            )

        return latest_url

    def find_solver(self, url):
        res = requests.get(url)

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            raise XWordDLException("Unable to load {}".format(url))

        soup = BeautifulSoup(res.text, "html.parser")

        iframe_tag = soup.find("iframe", id="crossword")
        if not isinstance(iframe_tag, Tag):
            raise XWordDLException("Could not find crossword iframe.")

        iframe_url = iframe_tag.get("data-src")
        if not isinstance(iframe_url, str):
            raise XWordDLException("Could not get URL src for iframe.")

        query = urllib.parse.urlparse(iframe_url).query
        self.id = urllib.parse.parse_qs(query)["id"][0]

        pubdate = soup.find("time")
        if pubdate:
            pubdate = pubdate.get_text()
            pubdate_dt = dateparser.parse(pubdate)
            self.date = pubdate_dt

        theme_supra = "Today’s theme: "
        desc = soup.find("meta", attrs={"property": "og:description"})
        if isinstance(desc, Tag):
            desc = desc.get("content", "")
            if isinstance(desc, str):
                if desc.startswith(theme_supra):
                    self.theme_title = desc[len(theme_supra) :].rstrip(".")

        return self.find_puzzle_url_from_id(self.id)

    def parse_xword(self, xw_data):
        puzzle = super().parse_xword(xw_data)

        if "<" in puzzle.title:
            puzzle.title = puzzle.title.split("<")[0]

        if self.theme_title:
            puzzle.title += f" - {self.theme_title}"

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        try:
            supra, main = puzzle.title.split(":", 1)
            if self.theme_title:
                main = main.rsplit(" - ")[0]
            if supra == "The Crossword" and dateparser.parse(main):
                title = self.theme_title
            else:
                title = main.strip()
        except XWordDLException:
            title = puzzle.title
        return super().pick_filename(puzzle, title=title, **kwargs)
