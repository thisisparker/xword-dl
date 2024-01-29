import json

import puz
import requests

from base64 import b64decode
from datetime import datetime, timedelta, timezone

from .basedownloader import BaseDownloader
from ..util import XWordDLException, base_n_fmt, decrypt_aes


class FinancialTimesDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crossword_type = ""
        self.selected_date = None

    def find_by_date(self, dt=None):
        if dt:
            self.selected_date = dt
            prev_date = dt
        else:
            dt = datetime.utcnow()
            prev_date = dt - timedelta(days=31)

        baseurl = "https://d3qii0ai0bvcck.cloudfront.net/prod/fetchlatestpuzzles"
        qs = "?left_window={}T00:00:00.000Z&right_window={}T00:00:00.000Z"

        date_format = dt.strftime("%Y-%m-%d")
        prev_date_format = prev_date.strftime("%Y-%m-%d")

        return baseurl + qs.format(prev_date_format, date_format)

    def find_latest(self):
        return self.find_by_date()

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url: str) -> dict:
        headers = {
            "Origin": "https://app.ft.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
        try:
            r = requests.get(solver_url, headers=headers)
            j = r.json()
            lm, response = j["lastModified"], j["response"]
        except (json.JSONDecodeError, KeyError):
            raise XWordDLException("Unable to download puzzle data.")

        try:
            ciphertext = b64decode(response)
            key, iv = self.__get_aes_keyiv(lm)
            plaintext = decrypt_aes(ciphertext, key, iv)
            xword_data = json.loads(plaintext.decode("utf-8"))
        except (json.JSONDecodeError, ValueError):
            raise XWordDLException("Unable to decrypt payload.")
        return xword_data

    def parse_xword(self, xword_data):
        puzzles = []
        for puzzle in xword_data["Items"]:
            if puzzle["crossword_type"] != self.crossword_type:
                continue
            if self.selected_date:
                puzzle_date = datetime.fromisoformat(puzzle["crossword_timestamp"])
                if self.selected_date.date() != puzzle_date.date():
                    continue
            puzzles.append(puzzle)

        if not puzzles:
            raise XWordDLException("No valid puzzles found.")

        # either only one puzzle matches, or we choose the most recent puzzle
        puzzles.sort(key=lambda x: x["crossword_timestamp"])
        xword_data = puzzles[-1]
        xword = json.loads(xword_data["crossword"])

        puzzle = puz.Puzzle()
        puzzle.title = "Financial Times {}: {}".format(
            self.crossword_type.replace("_", " ").title(),
            xword_data["crossword_id"],
        )
        puzzle.author = xword_data.get("author")
        puzzle.width, puzzle.height = (
            int(x) for x in xword_data["dimensions"].split("x")
        )

        # Extract clues and answers
        clues = []
        grid = [["."] * puzzle.width for _ in range(puzzle.height)]
        for direction in ("across", "down"):
            for _, clue in sorted(xword[direction].items(), key=lambda x: int(x[0])):
                text = clue["clue"]
                if "format" in clue:
                    text += " ({})".format(clue["format"])
                row, col = clue["row"], clue["col"]
                clues.append((text, (row, col)))
                for c in clue["answer"]:
                    grid[row][col] = c
                    if direction == "across":
                        col += 1
                    else:
                        row += 1

        # clues are sorted by (rol, col), which is the same order as clue number
        # assumes stable sort: across clues should sort before down clues
        puzzle.clues = [clue[0] for clue in sorted(clues, key=lambda x: x[1])]

        puzzle.solution = "".join(["".join(row) for row in grid])
        puzzle.fill = "".join(["." if c == "." else "-" for c in puzzle.solution])

        if "author_message" in xword_data:
            puzzle.notes = xword_data["author_message"]

        return puzzle

    @staticmethod
    def __get_aes_keyiv(lm):
        """Determine the encryption key and initialization vector from the timestamp"""

        # msec since the epoch, interpreted as base16, printed in base36
        key = base_n_fmt(int(str(lm), 16), 36)

        # year+day combination, printed in base 24
        dt = datetime.fromtimestamp(lm / 1000, timezone.utc)
        rev_day = int(dt.strftime("%d")[::-1])
        rev_year = int(dt.strftime("%Y")[::-1])
        key += base_n_fmt((dt.day + rev_day) * (dt.year + rev_year), 24)

        # pad with "0" and chop to get 14 bytes, append two chars to get to 16
        key = f"#{key[:14]:014}$"

        # return as bytes; the IV is just the uppercased key
        return (key.encode("utf-8"), key.upper().encode("utf-8"))


class FinancialTimesCrypticDownloader(FinancialTimesDownloader):
    command = "ftc"
    outlet = "Financial Times Cryptic"
    outlet_prefix = "Financial Times Cryptic"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crossword_type = "CRYPTIC"


class FinancialTimesPolymathDownloader(FinancialTimesDownloader):
    command = "ftp"
    outlet = "Financial Times Polymath"
    outlet_prefix = "Financial Times Polymath"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crossword_type = "POLYMATH"


class FinancialTimesWeekendDownloader(FinancialTimesDownloader):
    command = "ftw"
    outlet = "Financial Times Weekend"
    outlet_prefix = "Financial Times Weekend"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crossword_type = "WEEKEND_MAGAZINE"
