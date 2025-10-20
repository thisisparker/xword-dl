import datetime
import json
import re
import urllib.parse

import dateparser
import requests

from bs4 import BeautifulSoup, Tag

from .puzzmodownloader import PuzzmoDownloader
from ..util import XWordDLException


class NewYorkerDownloader(PuzzmoDownloader):
    command = "tny"
    outlet = "New Yorker"
    outlet_prefix = "New Yorker"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.api_endpoint = (
            "https://puzzles-games-api.gp-prod.conde.digital/api/v1/games/"
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
        res = self.session.get(url)

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            raise XWordDLException(f"Unable to load {url}")

        m = re.search(
            r"\"id\":\"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\"",
            res.text,
        )
        if not m:
            raise XWordDLException(f"Puzzle ID not found on {url}")
        puzzle_id = m.groups()[0]

        soup = BeautifulSoup(res.text, features="lxml")

        theme_supra = "Today’s theme: "
        desc = soup.find("meta", attrs={"property": "og:description"})
        if isinstance(desc, Tag):
            desc = desc.get("content", "")
            if isinstance(desc, str):
                if desc.startswith(theme_supra):
                    self.theme_title = desc[len(theme_supra) :].rstrip(".")

        published_time = soup.find("time")
        if isinstance(published_time, Tag):
            datetime_attr = str(published_time.get("datetime"))
            self.date = datetime.datetime.fromisoformat(datetime_attr)

        return urllib.parse.urljoin(self.api_endpoint, puzzle_id)

    def fetch_data(self, solver_url):
        res = self.session.get(solver_url)
        try:
            res.raise_for_status()
        except Exception as err:
            raise XWordDLException(f"Error while downloading puzzle data: {err}")

        return res.json()["data"]

    def parse_xword(self, xw_data):
        puzzle = self.parse_xd_format(xw_data)

        if "<" in puzzle.title:
            puzzle.title = puzzle.title.split("<")[0]

        if self.theme_title:
            puzzle.title += f" - {self.theme_title}"

        return puzzle

    def pick_filename(self, puzzle, boilerplate_supra="The Crossword", **kwargs):
        try:
            supra, main = puzzle.title.split(":", 1)
            if self.theme_title:
                main = main.rsplit(" - ")[0]
            if supra == boilerplate_supra and dateparser.parse(main):
                title = self.theme_title
            else:
                title = main.strip()
        except XWordDLException:
            title = puzzle.title
        return super().pick_filename(puzzle, title=title, **kwargs)


class NewYorkerMiniDownloader(NewYorkerDownloader):
    command = "tnym"
    outlet = "New Yorker Mini"
    outlet_prefix = "New Yorker Mini"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def matches_url(cls, url_components):
        return (
            "newyorker.com" in url_components.netloc
            and "/puzzles-and-games-dept/mini-crossword" in url_components.path
        )

    def find_latest(self, search_string="/mini-crossword/"):
        return super().find_latest(search_string=search_string)

    def find_by_date(self, dt):
        url_format = dt.strftime("%Y/%m/%d")
        guessed_url = urllib.parse.urljoin(
            "https://www.newyorker.com/puzzles-and-games-dept/mini-crossword/",
            url_format,
        )
        return guessed_url

    def pick_filename(self, puzzle, boilerplate_supra="The Mini Crossword", **kwargs):
        return super().pick_filename(puzzle, boilerplate_supra, **kwargs)
