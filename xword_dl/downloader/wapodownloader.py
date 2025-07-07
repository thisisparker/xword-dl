from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import puz

from .basedownloader import BaseDownloader
from ..util import XWordDLException


class WaPoDownloader(BaseDownloader):
    command = "wp"
    outlet = "Washington Post"
    outlet_prefix = "WaPo"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def find_latest(self):
        today = datetime.now(tz=ZoneInfo("America/New_York"))

        most_recent_sunday = today - timedelta(today.isoweekday() % 7)

        return self.find_by_date(most_recent_sunday)

    def find_by_date(self, dt):
        self.date = dt
        url_formatted_date = dt.strftime("%Y/%m/%d")

        return f"https://games-service-prod.site.aws.wapo.pub/crossword/levels/sunday/{url_formatted_date}"

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url: str):
        res = self.session.get(solver_url)

        try:
            res.raise_for_status()
        except Exception as err:
            raise XWordDLException("Error downloading puzzle:", err)

        try:
            xw_data = res.json()
        except Exception:
            raise XWordDLException(f"No parseable JSON at {solver_url}")

        return xw_data

    def parse_xword(self, xw_data: dict) -> puz.Puzzle:
        puzzle = puz.Puzzle()

        puzzle.title = xw_data.get("title", "").strip()
        puzzle.author = xw_data.get("creator", "").strip()
        puzzle.copyright = xw_data.get("copyright", "").strip()

        try:
            puzzle.width = xw_data["width"]
            puzzle.height = len(xw_data["cells"]) // puzzle.width
        except KeyError:
            raise XWordDLException("Puzzle JSON is malformed: does not specify size.")

        puzzle.notes = xw_data.get("description", "")

        solution = ""
        fill = ""
        markup = b""

        for cell in xw_data["cells"]:
            if ans := cell.get("answer"):
                solution += ans
                fill += "-"
                markup += b"\x80" if cell.get("circle") else b"\x00"
            else:
                solution += "."
                fill += "."
                markup += b"\x00"

        puzzle.solution = solution
        puzzle.fill = fill

        clues = xw_data["words"]

        # I bet these are always sorted but it doesn't hurt to ensure it
        clues.sort(key=lambda x: (min(x["indexes"]), x["direction"]))

        puzzle.clues = [clue["clue"].strip() for clue in clues]

        has_markup = b"\x80" in markup

        if has_markup:
            puzzle.extensions[b"GEXT"] = markup
            puzzle._extensions_order.append(b"GEXT")
            puzzle.markup()

        return puzzle
