import datetime

import puz

from .basedownloader import BaseDownloader
from ..util import XWordDLException


class PrincetonianBaseDownloader(BaseDownloader):
    BASE_URL = "https://crossword.dailyprincetonian.com"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mini = False

    def _list_url(self):
        return f"{self.BASE_URL}/api/crosswords?mini={str(self._mini).lower()}"

    def _get_puzzle_list(self):
        res = self.session.get(self._list_url())
        res.raise_for_status()
        return res.json()

    def find_latest(self):
        puzzles = self._get_puzzle_list()
        if not puzzles:
            raise XWordDLException("No puzzles found.")
        latest = puzzles[0]
        self.date = datetime.date.fromisoformat(latest["date"][:10])
        return f"{self.BASE_URL}/api/crosswords/{latest['id']}"

    def find_by_date(self, dt):
        puzzles = self._get_puzzle_list()
        target = dt.strftime("%Y-%m-%d")
        for puzzle in puzzles:
            if puzzle["date"].startswith(target):
                self.date = dt
                return f"{self.BASE_URL}/api/crosswords/{puzzle['id']}"
        raise XWordDLException(f"No puzzle found for {target}.")

    def find_solver(self, url):
        if "api/crosswords" not in url:
            return self.find_latest()
        return url

    def fetch_data(self, solver_url):
        puzzle_id = solver_url.rstrip("/").split("/")[-1]

        meta = self.session.get(f"{self.BASE_URL}/api/crosswords/{puzzle_id}").json()
        clues = self.session.get(
            f"{self.BASE_URL}/api/crosswords/{puzzle_id}/clues"
        ).json()
        authors = self.session.get(
            f"{self.BASE_URL}/api/crosswords/{puzzle_id}/authors"
        ).json()

        return {"meta": meta, "clues": clues, "authors": authors}

    def parse_xword(self, xw_data):
        meta = xw_data["meta"]
        clues = xw_data["clues"]
        authors = xw_data["authors"]

        puzzle = puz.Puzzle()
        puzzle.title = meta.get("title", "")
        puzzle.author = " / ".join(
            f"{a['first_name']} {a['last_name']}".strip() for a in authors
        )
        puzzle.copyright = "The Daily Princetonian"

        date_str = meta.get("date", "")
        if date_str and not self.date:
            self.date = datetime.date.fromisoformat(date_str[:10])

        width = 0
        height = 0
        for c in clues:
            if c["is_across"]:
                width = max(width, c["x"] + len(c["answer"]))
                height = max(height, c["y"] + 1)
            else:
                width = max(width, c["x"] + 1)
                height = max(height, c["y"] + len(c["answer"]))

        puzzle.width = width
        puzzle.height = height

        grid = [["." for _ in range(width)] for _ in range(height)]
        circled = set()
        for c in clues:
            x, y, ans = c["x"], c["y"], c["answer"]
            if c["is_across"]:
                for i, letter in enumerate(ans):
                    if letter.islower():
                        circled.add((x + i, y))
                    grid[y][x + i] = letter.upper()
            else:
                for i, letter in enumerate(ans):
                    if letter.islower():
                        circled.add((x, y + i))
                    grid[y + i][x] = letter.upper()

        puzzle.solution = "".join("".join(row) for row in grid)
        puzzle.fill = "".join("-" if c != "." else "." for c in puzzle.solution)

        if circled:
            indices = [row * width + col for col, row in circled]
            puzzle.markup().set_markup_squares(indices, puz.GridMarkup.Circled)

        sorted_clues = sorted(clues, key=lambda c: (c["y"], c["x"], not c["is_across"]))
        puzzle.clues = [c["clue"] for c in sorted_clues]

        return puzzle


class PrincetonianDownloader(PrincetonianBaseDownloader):
    command = "prince"
    outlet = "Daily Princetonian"
    outlet_prefix = "Princetonian"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mini = False

    @classmethod
    def matches_url(cls, url_components):
        return (
            "crossword.dailyprincetonian.com" in url_components.netloc
            and "minis" not in url_components.path
        )


class PrincetonianMiniDownloader(PrincetonianBaseDownloader):
    command = "prince-mini"
    outlet = "Daily Princetonian Mini"
    outlet_prefix = "Princetonian Mini"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mini = True

    @classmethod
    def matches_url(cls, url_components):
        return (
            "crossword.dailyprincetonian.com" in url_components.netloc
            and "minis" in url_components.path
        )
