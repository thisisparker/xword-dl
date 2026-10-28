import urllib.parse
from datetime import datetime

import requests
from puz import Puzzle

from ..util import (
    read_config_values,
    remove_invalid_chars_from_filename,
    sanitize_for_puzfile,
)

try:
    from .._version import __version__ as __version__  # type: ignore
except ModuleNotFoundError:
    __version__ = "0.0.0-dev"


class BaseDownloader:
    command = ""
    outlet = ""
    outlet_prefix = None

    def __init__(self, **kwargs):
        self.date = kwargs.get("date", None)
        self.netloc = urllib.parse.urlparse(kwargs.get("url", "")).netloc

        self.settings = {}

        self.settings["headers"] = {"User-Agent": f"xword-dl/{__version__}"}

        self.settings.update(read_config_values("general"))

        if "inherit_settings" in kwargs:
            self.settings.update(read_config_values(kwargs["inherit_settings"]))

        if self.command:
            self.settings.update(read_config_values(self.command))

        elif "url" in kwargs:
            self.settings.update(read_config_values("url"))
            self.settings.update(read_config_values(self.netloc))

        self.settings.update(kwargs)

        self.session = requests.Session()
        self.session.headers.update(self.settings.get("headers", {}))
        self.session.cookies.update(self.settings.get("cookies", {}))

    def pick_filename(self, puzzle: Puzzle, **kwargs) -> str:
        tokens = {
            "outlet": self.outlet or "",
            "prefix": self.outlet_prefix or "",
            "title": puzzle.title or "",
            "author": puzzle.author or "",
            "cmd": getattr(self, "command", self.netloc or ""),
            "netloc": self.netloc or "",
        }

        tokens = {t: kwargs[t] if t in kwargs else tokens[t] for t in tokens}

        date = kwargs.get("date", self.date)

        template = self.settings.get("filename") or ""

        if not template:
            template += "%prefix" if tokens.get("prefix") else "%author"
            template += " - %Y%m%d" if date else ""
            template += " - %title" if tokens.get("title") else ""

        for token in tokens.keys():
            replacement = kwargs.get(token, tokens[token])
            replacement = remove_invalid_chars_from_filename(replacement)
            template = template.replace("%" + token, replacement)

        if date:
            template = date.strftime(template)

        if not template.endswith(".puz"):
            template += ".puz"

        template = " ".join(template.split())

        return template

    def download(self, url: str) -> Puzzle:
        """Download, parse, and return a puzzle at a given URL."""

        solver_url = self.find_solver(url)
        xword_data = self.fetch_data(solver_url)
        puzzle = self.parse_xword(xword_data)

        puzzle = sanitize_for_puzfile(
            puzzle, preserve_html=self.settings.get("preserve_html", False)
        )

        return puzzle

    def find_solver(self, url: str) -> str:
        """Given a URL for a puzzle, returns the essential 'solver' URL.

        This is implemented in subclasses, and in instances where there is no
        separate 'landing page' URL for a puzzle, it may be a very transparent
        pass-through.
        """
        raise NotImplementedError

    def fetch_data(self, solver_url: str):
        """Given a URL from the find_solver function, return JSON crossword data

        This is implemented in subclasses and the returned data will not be
        standardized until later.
        """
        raise NotImplementedError

    def parse_xword(self, xw_data) -> Puzzle:
        """Given a blob of crossword data, parse and stuff into puz format.

        This method is implemented in subclasses based on the differences in
        the data format in situ.
        """
        raise NotImplementedError

    def find_latest(self) -> str:
        """Get the latest available crossword for this outlet.

        This method is implemented in subclasses and should return a string
        representing the URL to the latest puzzle."""
        raise NotImplementedError

    def find_by_date(self, dt: datetime) -> str:
        """Get the outlet's crossword for the specified date, if any.

        This method is implemented in subclasses and should return a string
        representing the URL to the puzzle."""
        raise NotImplementedError

    @classmethod
    def matches_url(cls, url_components: urllib.parse.ParseResult) -> bool:
        """Returns whether this plugin can download the provided URL."""
        raise NotImplementedError

    @classmethod
    def matches_embed_pattern(cls, url: str, page_source: str) -> str | None:
        """Returns a URL to a puzzle this plugin can parse, given HTML page source."""
        raise NotImplementedError

    @classmethod
    def authenticate(cls, username: str | None, password: str | None) -> None:
        """Authenticate the puzzle source with a username and password.

        This method is implemented in subclasses, and should save a login token to the
        program's settings when it is possible to do so. Authenticate is a class method
        and is usually not called on an instance of the class."""
        raise NotImplementedError
