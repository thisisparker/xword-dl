import base64
import datetime
import functools
import json
import re

import requests

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException


class BillboardDownloader(AmuseLabsDownloader):
    command = "bill"
    outlet = "Billboard"
    outlet_prefix = "Billboard"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = (
            "https://cdn2.amuselabs.com/pmm/date-picker?set=billboard-crossword"
        )
        self.url_from_id = "https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=billboard-crossword"

    @classmethod
    def matches_url(cls, url_components):
        return (
            url_components.netloc == "www.billboard.com"
            and url_components.path.removesuffix("/") == "/p/billboard-crossword"
        )

    def find_latest(self) -> str:
        raise XWordDLException(
            "Billboard ran from October 2, 2025 to February 10, 2026 and is no longer publishing. "
            "Use --date to download a puzzle from the archive."
        )

    def find_solver(self, url) -> str:
        if "amuselabs.com" in url:
            return url

        res = self.session.get(url)

        if not res.ok:
            raise XWordDLException("Unable to connect to Billboard.")

        solver_url = self.matches_embed_pattern(page_source=res.text)

        if not solver_url:
            raise XWordDLException("Can't find latest Billboard puzzle.")

        return solver_url

    @functools.cached_property
    def _archive(self):
        # Fetch the picker page to get a loadToken for the archive API
        res = requests.get(
            "https://cdn2.amuselabs.com/pmm/date-picker?set=billboard-crossword"
        )
        if not res.ok:
            raise XWordDLException("Could not reach Billboard puzzle picker.")

        m = re.search(r'id="params"[^>]*>([^<]+)<', res.text, re.DOTALL)
        if not m:
            raise XWordDLException("Could not parse Billboard picker page.")
        obj = json.loads(m.group(1).strip())
        rawsps = obj.get("rawsps", "")
        try:
            sps = json.loads(base64.b64decode(rawsps + "==").decode("utf-8"))
            load_token = sps.get("loadToken", "")
        except Exception:
            raise XWordDLException(
                "Could not extract auth token from Billboard picker."
            )

        if not load_token:
            raise XWordDLException(
                "Could not retrieve authentication token for Billboard archive."
            )

        api_res = self.session.get(
            "https://cdn2.amuselabs.com/pmm/api/v1/puzzles",
            params={
                "set": "billboard-crossword",
                "limit": 200,
                "offset": 0,
                "loadToken": load_token,
            },
        )
        if not api_res.ok:
            raise XWordDLException("Could not fetch Billboard puzzle archive.")

        return (
            api_res.json()
            .get("seriesToPuzzleMetadata", {})
            .get("billboard-crossword", [])
        )

    def find_by_date(self, dt):
        self.date = dt
        target_date_str = dt.strftime("%Y%m%d")

        puzzles = self._archive

        # Match by ID suffix (most IDs are TitleSlug_YYYYMMDD)
        puzzle_id = next(
            (
                p.get("puzzleId")
                for p in puzzles
                if p.get("puzzleId", "").endswith("_" + target_date_str)
            ),
            None,
        )

        # Fall back to matching by publication timestamp
        if not puzzle_id:
            target_date = dt.date() if hasattr(dt, "date") else dt
            puzzle_id = next(
                (
                    p.get("puzzleId")
                    for p in puzzles
                    if datetime.datetime.utcfromtimestamp(
                        p.get("publicationTime", 0) / 1000
                    ).date()
                    == target_date
                ),
                None,
            )

        if not puzzle_id:
            raise XWordDLException(
                f"No Billboard puzzle found for {dt.strftime('%Y-%m-%d')}."
            )

        self.id = puzzle_id
        # Return crossword URL without loadToken — it works unauthenticated
        return f"https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=billboard-crossword"

    def parse_xword(self, xw_data):
        # Billboard puzzles are typically untitled, and some have the title set to '-'
        # so let's clear that out so it's "truly" untitled after parsing
        # If we see this in other outlets it might be worth promoting to the general Amuse parser
        puzzle = super().parse_xword(xw_data)
        if puzzle.title == "-":
            puzzle.title = ""

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        explicit_title = puzzle.title

        if not explicit_title:
            puzzle.title = f"Billboard Crossword: {self.date:%b {self.date.day}, %Y}"

        return super().pick_filename(puzzle, title=explicit_title, **kwargs)
