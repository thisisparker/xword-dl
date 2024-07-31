import re
from datetime import datetime
from urllib.parse import urljoin

import puz
import requests
from bs4 import BeautifulSoup as bs

from .basedownloader import BaseDownloader
from ..util import XWordDLException, update_config_file, parse_date


class AVCXBaseDownloader(BaseDownloader):
    command = "avcx"
    outlet_prefix = "AVCX"
    outlet = "American Values Crossword Club"
    base_url = "https://avxwords.com"

    def __init__(self, **kwargs):
        super().__init__(inherit_settings="avcx", **kwargs)

        self.descriptions = []

        self.session = requests.Session()

        user_t = self.settings.get("AVCX_USER")
        token_t = self.settings.get("AVCX_TOKEN")
        if not user_t or not token_t:
            username = self.settings.get("username")
            password = self.settings.get("password")
            if username and password:
                user_t, token_t = self.authenticate(username, password)

        if not user_t or not token_t:
            raise XWordDLException(
                "No credentials provided or stored. Try running xword-dl avcx --authenticate."
            )
        else:
            self.session.cookies.set("PA_AUS", user_t)
            self.session.cookies.set("PA_ATOK", token_t)

    @staticmethod
    def matches_url(url_components):
        return "avxwords.com" in url_components.netloc and (
            "puzzles" in url_components.path or "download-puzzle" in url_components.path
        )

    def authenticate(self, username, password):
        """Given an AVCX username and password, return username-based login token"""

        try:
            res = requests.post(
                "https://avxwords.com/log-in/",
                data={"email": username, "password": password},
                allow_redirects=False,
            )

            res.raise_for_status()
        except requests.HTTPError:
            raise XWordDLException("Unable to authenticate.")

        user_t = res.cookies.get("PA_AUS")
        token_t = res.cookies.get("PA_ATOK")

        if user_t and token_t:
            update_config_file("avcx", {"AVCX-USER": user_t})
            update_config_file("avcx", {"AVCX-TOKEN": token_t})
            return (user_t, token_t)
        else:
            raise XWordDLException("No login token found in authentication response.")

    def find_latest(self):
        if self.puzzle_type is None:
            raise XWordDLException(
                "You must specify the AVCX variety to get the latest crossword."
            )
        return self.find_by_date()

    def find_by_date(self, dt=None):
        if self.puzzle_type is None:
            raise XWordDLException(
                "You must specify the AVCX variety to choose by date."
            )
        if dt is None:
            year = datetime.now().strftime("%Y")
        else:
            year = dt.strftime("%Y")
        res = self.session.get(f"https://avxwords.com/puzzles-by-year/?y={year}")
        soup = bs(res.text, "lxml")
        puzzle_list = next(
            el.find_next("ul")
            for el in soup.find_all("h3")
            if el.string and self.puzzle_type in el.string
        )

        if dt is None:
            latest_url = puzzle_list.find("li", class_="row").find("a").get("href")
            return urljoin(self.base_url, latest_url)

        for row in puzzle_list.find_all("li", class_="row"):
            date = row.find("span", class_="puzzle-date").text.strip()
            row_dt = parse_date(date)
            if row_dt.date() == dt.date():
                url = row.find("a").get("href")
                return urljoin(self.base_url, url)

        raise XWordDLException("Could not find puzzle for date.")

    def find_solver(self, url):
        if "puzzles" in url:
            url = url.removesuffix("/")
            number = url.split("/")[-1]
            url = f"https://avxwords.com/download-puzzle/?id={number}"
        elif "download-puzzle" not in url:
            raise XWordDLException("Invalid URL for AVCX.")

        try:
            res = self.session.get(url)
            res.raise_for_status()
        except requests.HTTPError:
            raise XWordDLException(
                "Unable to open page. Possible authentication issue?"
            )

        soup = bs(res.text, "lxml")

        difficulty_l = soup.find(
            "span",
            class_="difficulty",
        ).get("aria-label")
        if difficulty_l:
            difficulty = difficulty_l.split()[0]
            self.descriptions.append(f"Difficulty: {difficulty}.")

        desc = soup.find(id="puzzle-newsletter").get_text()
        if desc:
            self.descriptions.append(desc.strip())

        al_string = re.compile(".*AcrossLite.*")
        al_badge = soup.find("span", class_="badge", string=al_string)
        if al_badge:
            url = al_badge.parent.get("href")
            return urljoin(self.base_url, url)

        # if AVCX doesn't have .puz, download JPZ and convert it (TODO)
        jpz_string = re.compile(".*JPZ.*")
        jpz_badge = soup.find("span", class_="badge", string=jpz_string)
        if jpz_badge:
            url = jpz_badge.parent.get("href")
            return urljoin(self.base_url, url)

        raise XWordDLException("Could not find valid puzzle file.")

    def fetch_data(self, solver_url):
        res = self.session.get(solver_url)

        try:
            res.raise_for_status()
        except requests.HTTPError:
            raise XWordDLException("Puzzle data not found.")

        return res.content

    def parse_xword(self, xword_data):
        # This function can receive either PUZ files or JPZ
        if xword_data[2:14] == b"ACROSS&DOWN\x00":
            return self._parse_puz(xword_data)
        elif xword_data[:5] == b"<?xml":
            return self._parse_jpz(xword_data)
        else:
            raise XWordDLException("Invalid puzzle data.")

    def _parse_puz(self, data):
        puzzle = puz.load(data)
        puzzle.author = puzzle.author.strip()
        puzzle.title = puzzle.title.strip()

        if puzzle.title and ", edited by " in puzzle.title:
            parts = puzzle.title.partition(", edited by ")
            puzzle.title = parts[0]
            self.descriptions.append(f"Edited by {parts[2]}.")

        if self.descriptions:
            puzzle.notes = "\n\n".join(self.descriptions)

        if puzzle.title and puzzle.author:
            if puzzle.author in puzzle.title:
                title = puzzle.title.replace(f"by {puzzle.author}", "")
                title = title.replace(puzzle.author, "").strip(" -")
                puzzle.title = title

        return puzzle

    def _parse_jpz(self, data):
        raise XWordDLException(
            "This puzzle is only available in JPZ format, which is currently unsuported.\n"
            "If you can fix this, please send a pull request!"
        )


class AVCXWeeklyDownloader(AVCXBaseDownloader):
    command = "avcw"
    outlet = "American Values Crossword Club Classic"
    puzzle_type = "Weekly Puzzles"


class AVCXSDownloader(AVCXBaseDownloader):
    command = "avcs"
    outlet = "American Values Crossword Club AVCX+"
    puzzle_type = "AVCX+s"


class AVCXLDownloader(AVCXBaseDownloader):
    command = "avcl"
    outlet = "American Values Crossword Club Lil AVCX"
    puzzle_type = "Lil AVCXs"


class AVCXCDownloader(AVCXBaseDownloader):
    command = "avcc"
    outlet = "American Values Crossword Club Cryptic"
    puzzle_type = "Cryptic Puzzles"
