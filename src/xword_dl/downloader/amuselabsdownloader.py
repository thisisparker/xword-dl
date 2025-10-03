import base64
import binascii
import datetime
import json
import urllib.parse

import puz
import requests

import re

from bs4 import BeautifulSoup, Tag

from .basedownloader import BaseDownloader
from ..util import XWordDLException, unidecode


class AmuseLabsDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.id = None

        # these values must be overridden by subclasses, if used
        self.picker_url = None
        self.url_from_id = None

    @classmethod
    def matches_url(cls, url_components):
        return "amuselabs.com" in url_components.netloc

    @classmethod
    def matches_embed_pattern(cls, url="", page_source=""):
        if url and not page_source:
            res = requests.get(url)
            page_source = res.text

        if not page_source:
            return None

        soup = BeautifulSoup(page_source, features="lxml")

        sources = [
            urllib.parse.urljoin(
                url,
                str(iframe.get("data-crossword-url", ""))
                or str(iframe.get("data-src", ""))
                or str(iframe.get("src", "")),
            )
            for iframe in soup.find_all("iframe")
            if isinstance(iframe, Tag)
        ]

        sources = [src for src in sources if src != "about:blank"]

        for embed_src in sources:
            parsed_url = urllib.parse.urlparse(embed_src)
            if "amuselabs.com" in parsed_url.netloc:
                return embed_src

        script_sources = [
            str(s.get("src")) for s in soup.find_all("script") if isinstance(s, Tag)
        ]

        if any(s.endswith("puzzleme-embed.js") for s in script_sources):
            base_path = ""
            puzzle_id = ""
            puzzle_set = ""
            base_path_regex_match = re.search(
                r"PM_BasePath\s*=\s*\"(.*)\"", page_source
            )
            if base_path_regex_match:
                base_path = base_path_regex_match.groups()[0]
            embed_div = soup.find("div", attrs={"class": "pm-embed-div"})
            if isinstance(embed_div, Tag):
                puzzle_id = embed_div.get("data-id")
                puzzle_set = embed_div.get("data-set")

            if base_path and puzzle_id and puzzle_set:
                return f"{base_path}crossword?id={puzzle_id}&set={puzzle_set}"

        return None

    def find_latest(self) -> str:
        if self.picker_url is None or self.url_from_id is None:
            raise XWordDLException(
                "This outlet does not support finding the latest crossword."
            )
        res = requests.get(self.picker_url)
        soup = BeautifulSoup(res.text, "html.parser")

        param_tag = soup.find("script", id="params")
        param_obj = (
            json.loads(param_tag.string or "") if isinstance(param_tag, Tag) else {}
        )

        puzzles = param_obj.get("puzzles", [])

        if not puzzles:
            raise XWordDLException("Unable to find puzzles data from picker page.")

        self.id = puzzles[0]["id"]

        self.get_and_add_picker_token(res.text)

        return self.find_puzzle_url_from_id(self.id)

    def get_and_add_picker_token(self, picker_source=None):
        if self.picker_url is None:
            raise XWordDLException(
                "No picker URL was available. Please report this as a bug."
            )
        if not picker_source:
            res = requests.get(self.picker_url)
            picker_source = res.text

        if "pickerParams.rawsps" in picker_source:
            rawsps = next(
                (
                    line.strip().split("'")[1]
                    for line in picker_source.splitlines()
                    if "pickerParams.rawsps" in line
                ),
                None,
            )
        else:
            soup = BeautifulSoup(picker_source, "html.parser")
            param_tag = soup.find("script", id="params")
            param_obj = (
                json.loads(param_tag.string or "") if isinstance(param_tag, Tag) else {}
            )
            rawsps = param_obj.get("rawsps", None)

        # FIXME: should this raise an exception when not defined?
        if rawsps:
            picker_params = json.loads(base64.b64decode(rawsps).decode("utf-8"))
            token = picker_params.get("loadToken", None)
            if token:
                self.url_from_id += "&loadToken=" + token

    def find_puzzle_url_from_id(self, puzzle_id):
        if self.url_from_id is None:
            raise XWordDLException(
                "No URL for puzzle IDs was available. Please report this as a bug."
            )
        return self.url_from_id.format(puzzle_id=puzzle_id)

    def guess_date_from_id(self, puzzle_id):
        """Subclass method to set date from an AmuseLabs id, if possible.

        If a date can be derived from the id, it is set as a datetime object in
        the date property of the downloader object. This method is called when
        picking a filename for AmuseLabs-type puzzles.
        """

        pass

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url):
        res = requests.get(solver_url)

        # It looks like Amuse returns 200s instead of 404s. This is hacky but catches them
        # early and produces a more informative error than letting it through to fail at
        # the parsing stage
        if (
            not res.ok
            or "The puzzle you are trying to access was not found" in res.text
        ):
            raise XWordDLException(f"Could not fetch solver at {solver_url}")

        if "window.rawc" in res.text or "window.puzzleEnv.rawc" in res.text:
            rawc = next(
                (
                    line.strip().split("'")[1]
                    for line in res.text.splitlines()
                    if ("window.rawc" in line or "window.puzzleEnv.rawc" in line)
                ),
                None,
            )
        else:
            # As of 2023-12-01, it looks like the rawc value is sometimes
            # given as a parameter in an embedded json blob, which means
            # parsing the page
            soup = BeautifulSoup(res.text, "html.parser")
            if not isinstance(soup, Tag):
                raise XWordDLException(
                    "Crossword puzzle not found. Could not parse HTML."
                )

            script_tag = soup.find("script", id="params")
            if not isinstance(script_tag, Tag):
                raise XWordDLException(
                    "Crossword puzzle not found. Could not find script tag."
                )

            rawc = json.loads(script_tag.string or "").get("rawc")

        ## In some cases we need to pull the underlying JavaScript ##
        # Find the JavaScript URL
        amuseKey = None
        m1 = re.search(r'"([^"]+c-min.js[^"]+)"', res.text)
        if m1 is None:
            raise XWordDLException("Failed to find JS url for amuseKey.")
        js_url_fragment = m1.groups()[0]
        js_url = urllib.parse.urljoin(solver_url, js_url_fragment)

        # get the "key" from the URL
        res2 = requests.get(js_url)

        # matches a 7-digit hex string preceded by `="` and followed by `"`
        m2 = re.search(r'="([0-9a-f]{7})"', res2.text)
        if m2:
            # in this format, add 2 to each digit
            amuseKey = [int(c, 16) + 2 for c in m2.groups()[0]]
        else:
            # otherwise, grab the new format key and do not add 2
            amuseKey = [
                int(x) for x in re.findall(r"=\[\]\).push\(([0-9]{1,2})\)", res2.text)
            ]

        # But now that might not be the right key, and there's another one
        # that we need to try!
        # added on 2023-10-26
        # updated with stricter regex on 2025-08-04
        # TODO: Find a better system for finding this
        key_2_order_regex = r"n=(\d+);n<t\.length;n\+="
        key_2_digit_regex = r"<t\.length\?(\d+)"

        key_digits = [int(x) for x in re.findall(key_2_digit_regex, res2.text)]
        key_orders = [int(x) for x in re.findall(key_2_order_regex, res2.text)]

        amuseKey2 = [
            x for x, _ in sorted(zip(key_digits, key_orders), key=lambda pair: pair[1])
        ]

        # try to decode potentially obsfucated rawc with the two detected keys
        xword_data = load_rawc(rawc, amuseKey=amuseKey) or load_rawc(
            rawc, amuseKey=amuseKey2
        )

        if xword_data is None:
            raise XWordDLException("Could not decode rawc for AmuseLabs puzzle.")

        return xword_data

    def parse_xword(self, xw_data):
        puzzle = puz.Puzzle()
        puzzle.title = xw_data.get("title", "").strip()
        puzzle.author = xw_data.get("author", "").strip()
        puzzle.copyright = xw_data.get("copyright", "").strip()
        puzzle.width = xw_data.get("w")
        puzzle.height = xw_data.get("h")

        timestamp = int(xw_data.get("publishTime", 0)) // 1000
        if timestamp and not self.date:
            self.date = datetime.date.fromtimestamp(timestamp)

        markup_data = xw_data.get("cellInfos", "")

        circled = [
            (square["x"], square["y"]) for square in markup_data if square["isCircled"]
        ]

        solution = ""
        fill = ""
        markup = b""
        rebus_board = []
        rebus_index = 0
        rebus_table = ""

        box = xw_data["box"]
        for row_num in range(xw_data.get("h")):
            for col_num, column in enumerate(box):
                cell = column[row_num]
                if cell == "\x00":
                    solution += "."
                    fill += "."
                    markup += b"\x00"
                    rebus_board.append(0)
                elif len(cell) == 1:
                    solution += cell
                    fill += "-"
                    markup += b"\x80" if (col_num, row_num) in circled else b"\x00"
                    rebus_board.append(0)
                elif not cell:
                    solution += "X"
                    fill += "-"
                    markup += b"\x00"
                    rebus_board.append(0)
                else:
                    solution += cell[0]
                    fill += "-"
                    rebus_board.append(rebus_index + 1)
                    rebus_table += "{:2d}:{};".format(rebus_index, unidecode(cell))
                    rebus_index += 1

        puzzle.solution = solution
        puzzle.fill = fill

        if all(c in [".", "X"] for c in puzzle.solution):
            puzzle.solution_state = 0x0002
            puzzle.title += " - no solution provided"

        placed_words = xw_data["placedWords"]

        weirdass_puz_clue_sorting = sorted(
            placed_words,
            key=lambda word: (word["y"], word["x"], not word["acrossNotDown"]),
        )

        clues = [word["clue"].get("clue", "") for word in weirdass_puz_clue_sorting]

        puzzle.clues.extend(clues)

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

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        if not self.date and self.id:
            self.guess_date_from_id(self.id)
        return super().pick_filename(puzzle, **kwargs)


# helper function to decode rawc as occasionally it can be obfuscated
def load_rawc(rawc, amuseKey=None):
    try:
        # the original case is just base64'd JSON
        return json.loads(base64.b64decode(rawc).decode("utf-8"))
    except (binascii.Error, json.JSONDecodeError, UnicodeError):
        pass
    try:
        # case 2 is the first obfuscation
        E = rawc.split(".")
        A = list(E[0])
        H = E[1][::-1]
        F = [int(A, 16) + 2 for A in H]
        B, G = 0, 0
        while B < len(A) - 1:
            C = min(F[G % len(F)], len(A) - B)
            for D in range(C // 2):
                A[B + D], A[B + C - D - 1] = A[B + C - D - 1], A[B + D]
            B += C
            G += 1
        newRawc = "".join(A)
        return json.loads(base64.b64decode(newRawc).decode("utf-8"))
    except (binascii.Error, IndexError, json.JSONDecodeError, UnicodeError):
        if amuseKey is None:
            return None

    try:
        # case 3 is the most recent obfuscation
        e = list(rawc)
        H = amuseKey
        E = []
        F = 0

        while F < len(H):
            J = H[F]
            E.append(J)
            F += 1

        A, G, I = 0, 0, len(e) - 1  # noqa: E741
        while A < I:
            B = E[G]
            L = I - A + 1
            C = A
            B = min(B, L)
            D = A + B - 1
            while C < D:
                M = e[D]
                e[D] = e[C]
                e[C] = M
                D -= 1
                C += 1
            A += B
            G = (G + 1) % len(E)
        deobfuscated = "".join(e)
        return json.loads(base64.b64decode(deobfuscated).decode("utf-8"))
    except (binascii.Error, IndexError, json.JSONDecodeError, UnicodeError):
        return None
