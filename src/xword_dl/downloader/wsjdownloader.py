"""
WSJ downloader

Note that this only allows downloads from the puzzlr.net URLs,
and will not download a puzzle from the WSJ puzzle page.
This can be considered a TODO.
"""

import datetime
import puz


from .basedownloader import BaseDownloader


class WSJDownloader(BaseDownloader):
    command = "wsj"
    outlet = "Wall Street Journal"
    outlet_prefix = "WSJ"

    def __init__(self, **kwargs):
        super().__init__(headers={"User-Agent": "xword-dl"}, **kwargs)

    @classmethod
    def matches_url(cls, url_components):
        return "puzzlr.net" in url_components

    def find_by_date(self, dt):
        self.date = dt  # self.date used by BaseDownloader.pick_filename()
        ymd = dt.strftime("%Y-%m-%d")  # YYYY-MM-DD format
        url = f"https://api.puzzlr.net/trpc/crossword.getLevel?batch=1&input=%7B%220%22%3A%7B%22tenant%22%3A%22wsj%22%2C%22date%22%3A%22{ymd}%22%7D%7D"
        return url

    def find_latest(self):
        return self.find_by_date(datetime.datetime.today())

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url):
        res = self.session.get(solver_url)
        return res.json()

    def parse_xword(self, xw_data):
        xw_data = xw_data[0]["result"]["data"]["data"]

        date_string = xw_data["date"]

        self.date = datetime.datetime.strptime(date_string, "%Y-%m-%d")

        puzzle = puz.Puzzle()
        puzzle.title = xw_data.get("title") or ""
        puzzle.author = xw_data.get("author") or ""
        puzzle.copyright = xw_data.get("description") or ""
        puzzle.width = xw_data["width"]
        puzzle.height = xw_data["height"]

        # TODO: is there ever a notepad in non-contest puzzles?
        puzzle.notes = xw_data.get("contestClueText") or ""

        solution = ""
        fill = ""
        markup = b""

        for row in xw_data["grid"]:
            for cell in row:
                if cell.get("isBlack"):
                    fill += "."
                    solution += "."
                    markup += b"\x00"
                else:
                    fill += "-"
                    solution += cell.get("answer") or "X"
                    markup += b"\x80" if cell.get("isCircled") else b"\x00"

        puzzle.fill = fill
        puzzle.solution = solution

        if all(c in [".", "X"] for c in puzzle.solution):
            puzzle.solution_state = 0x0002

        clue_list = xw_data["clues"]["across"] + xw_data["clues"]["down"]
        sorted_clue_list = sorted(clue_list, key=lambda x: int(x["number"]))

        clues = [clue["text"] for clue in sorted_clue_list]

        puzzle.clues = clues

        has_markup = b"\x80" in markup

        if has_markup:
            puzzle.extensions[b"GEXT"] = markup
            puzzle._extensions_order.append(b"GEXT")
            puzzle.markup()

        return puzzle
