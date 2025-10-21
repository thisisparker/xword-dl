import re
import secrets

import dateparser
import puz

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .basedownloader import BaseDownloader
from ..util import join_bylines, XWordDLException


class PuzzmoDownloader(BaseDownloader):
    command = "pzm"
    outlet = "Puzzmo"
    outlet_prefix = "Puzzmo"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.temporary_user_id = secrets.token_urlsafe(21)
        self.session.headers.update({"Puzzmo-Gameplay-Id": self.temporary_user_id})

        self.finder_key = "today:/{date_string}/crossword"

        self.date_string = ""

    def _get_puzzmo_date(self, dt=None):
        # Returns what "today" is for Puzzmo, right now or for a given datetime object
        if not dt:
            dt = datetime.now(tz=ZoneInfo("America/New_York"))
        else:
            dt = dt.astimezone(tz=ZoneInfo("America/New_York"))

        return dt if dt.hour >= 1 else dt - timedelta(days=1)

    @classmethod
    def matches_url(cls, url_components):
        return "puzzmo.com" in url_components.netloc and bool(
            re.match(r"^/puzzle/\d{4}-\d{2}-\d{2}/crossword/?$", url_components.path)
        )

    def find_latest(self):
        puzzmo_date = self._get_puzzmo_date()

        return self.find_by_date(puzzmo_date)

    def find_by_date(self, dt):
        self.date_string = dt.strftime("%Y-%m-%d")

        # This URL is arbitrary but it seems better to return the solving page, why not?
        # In practice, setting the date_string above does everything we need here.
        return f"https://www.puzzmo.com/puzzle/{self.date_string}/crossword"

    def find_solver(self, url):
        if not self.date_string:
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", url)
            if date_match:
                self.date_string = date_match.group(1)
        return url

    def fetch_data(self, solver_url):
        query = """query PlayGameScreenQuery(
                      $finderKey: String!
                      $gameContext: StartGameContext!
                    ) {
                      startOrFindGameplay(finderKey: $finderKey, context: $gameContext) {
                        __typename
                        ... on ErrorableResponse {
                          message
                          failed
                          success
                        }
                        ...on HasGamePlayed {
                          gamePlayed{
                            puzzle {
                              name
                              emoji
                              puzzle
                              dailyTitle
                              author
                              authors {
                                publishingName
                                username
                                usernameID
                                name
                                id
                              }
                            }
                          }
                        }
                      }
                    }"""

        variables = {
            "finderKey": self.finder_key.format(date_string=self.date_string),
            "gameContext": {"partnerSlug": None, "pingOwnerForMultiplayer": True},
        }

        operation_name = "PlayGameScreenQuery"

        payload = {
            "operationName": operation_name,
            "query": query,
            "variables": variables,
        }

        res = self.session.post(
            "https://www.puzzmo.com/_api/prod/graphql?PlayGameScreenQuery", json=payload
        )

        response = res.json()["data"]["startOrFindGameplay"]

        if response["__typename"] == "ErrorableResponse":
            error = response["message"]
            raise XWordDLException(f"Puzzmo error: {error}")

        try:
            xw_data = res.json()["data"]["startOrFindGameplay"]["gamePlayed"]["puzzle"]
        except KeyError:
            raise XWordDLException("Unable to extract puzzle data.")

        return xw_data

    def parse_xword(self, xw_data):
        xd_data = xw_data["puzzle"]

        puzzle = self.parse_xd_format(xd_data)

        # Override xd metadata with more reliable API results
        self.date = dateparser.parse(xw_data["dailyTitle"]) or dateparser.parse(
            xw_data["dailyTitle"].split("-")[0]
        )

        puzzle.title = xw_data.get("name", "")
        puzzle.author = join_bylines(
            [a.get("publishingName") or a.get("name") for a in xw_data["authors"]]
        )

        return puzzle

    def parse_xd_format(self, xd_data):
        puzzle = puz.Puzzle()

        puzzle_lines = [line.strip() for line in xd_data.splitlines()]

        section = None
        blank_count = 2
        named_sections = False
        default_sections = ["metadata", "grid", "clues", "notes"]
        observed_height = 0
        observed_width = 0
        fill = ""
        solution = ""
        markup = b""
        rebus_board = []
        rebus_index = 0
        rebus_table = ""
        clue_list = []
        rebus_entries = {}

        for line in puzzle_lines:
            if not line:
                blank_count += 1
                continue
            else:
                if line.startswith("## "):
                    named_sections = True
                    section = line[3:].lower()
                    blank_count = 0
                    continue

                elif not named_sections and blank_count >= 2:
                    section = default_sections.pop(0)
                    blank_count = 0

            if section == "metadata":
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip().lower(), v.strip()

                    if k == "title":
                        puzzle.title = v
                    elif k == "author":
                        puzzle.author = v
                    # This is how we WOULD set the date here, but so far Puzzmo
                    # is always "Not set" and the New Yorker is always 2025-09-02
                    # elif k == "date":
                    #     try:
                    #         self.date = datetime.strptime(v, "%Y-%m-%d")
                    #         print("setting date as", self.date)
                    #     except ValueError:
                    #         pass
                    elif k == "copyright":
                        puzzle.copyright = v.strip(" ©")
                    elif k == "rebus":
                        rebus_entries = {
                            entry.split("=")[0]: entry.split("=")[1]
                            for entry in v.split()
                        }

            elif section == "grid":
                if not observed_width:
                    observed_width = len(line)

                observed_height += 1

                for c in line:
                    if c.isalnum():
                        fill += "-"
                        solution += c.upper()
                    else:
                        fill += "."
                        solution += "."

            elif section == "clues":
                if clue_parts := re.match(r"([AD])(\d{1,2})\.(.*)", line):
                    clue_text = clue_parts[3]
                    markdown_sigils = "/*-_~^"
                    for sigil in markdown_sigils:
                        clue_text = clue_text.replace("{" + sigil, sigil)
                        clue_text = clue_text.replace(sigil + "}", sigil)
                    clue_list.append((clue_parts[1], int(clue_parts[2]), clue_text))
                else:
                    continue

            elif section == "design":
                if "style" in line or "{" in line:
                    continue
                else:
                    for c in line:
                        markup += b"\x00" if c in "#." else b"\x80"

        for c in solution:
            if c in rebus_entries:
                rebus_board.append(rebus_index + 1)
                rebus_table += "{:2d}:{};".format(rebus_index, rebus_entries[c])
                rebus_index += 1
            else:
                rebus_board.append(0)

        puzzle.height = observed_height
        puzzle.width = observed_width
        puzzle.solution = solution
        puzzle.fill = fill

        has_markup = b"\x80" in markup
        has_rebus = any(rebus_board)

        if has_markup:
            puzzle.extensions[b"GEXT"] = markup
            puzzle._extensions_order.append(b"GEXT")
            puzzle.markup()

        if has_rebus:
            puzzle.extensions[b"GRBS"] = bytes(rebus_board)
            puzzle.extensions[b"RTBL"] = rebus_table.encode(puz.ENCODING)
            puzzle._extensions_order.extend([b"GRBS", b"RTBL"])
            puzzle.rebus()

        clue_list.sort(key=lambda c: (c[1], c[0]))

        puzzle.clues = [c[2].split(" ~ ")[0].strip() for c in clue_list]

        return puzzle


class PuzzmoBigDownloader(PuzzmoDownloader):
    command = "pzmb"
    outlet = "Puzzmo Big"
    outlet_prefix = "Puzzmo Big"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.finder_key += "/big"

    def _get_most_recent_puzzmo_big_date(self, dt):
        # Puzzles were every two weeks from 2025-01-13 (launch) to 2025-06-16
        # Starting 2025-07-07, they are monthly first monday

        start_date = datetime(2025, 1, 13, 1, tzinfo=ZoneInfo("America/New_York"))
        last_biweekly = datetime(2025, 6, 16, 1, tzinfo=ZoneInfo("America/New_York"))
        first_monthly = datetime(2025, 7, 7, 1, tzinfo=ZoneInfo("America/New_York"))

        guessed_most_recent = last_biweekly

        if start_date <= dt < last_biweekly:
            delta_days = (dt.date() - start_date.date()).days
            even_weeks = (delta_days // 7) // 2 * 2

            most_recent_even_monday = start_date + timedelta(weeks=even_weeks)
            guessed_most_recent = most_recent_even_monday

        elif last_biweekly <= dt < first_monthly:
            pass

        elif first_monthly <= dt:
            month_with_puzzle = dt.month - 1 if dt.day <= dt.weekday() else dt.month
            year_with_puzzle = dt.year
            if month_with_puzzle == 0:
                month_with_puzzle = 12
                year_with_puzzle -= 1
            reference_date = datetime(year_with_puzzle, month_with_puzzle, 7)
            offset = reference_date.weekday()
            guessed_most_recent = reference_date - timedelta(offset)

        return guessed_most_recent

    @classmethod
    def matches_url(cls, url_components):
        return "puzzmo.com" in url_components.netloc and bool(
            re.match(
                r"^/puzzle/\d{4}-\d{2}-\d{2}/crossword/big/?$", url_components.path
            )
        )

    def find_latest(self):
        today = self._get_puzzmo_date()
        guessed_most_recent_date = self._get_most_recent_puzzmo_big_date(today)

        return self.find_by_date(guessed_most_recent_date) + "/big"
