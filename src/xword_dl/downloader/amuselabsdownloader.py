import base64
import datetime
import json
import urllib.parse

import puz
import requests

import re

from bs4 import BeautifulSoup, Tag

from collections import deque
from typing import List

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
                if "crossword" in parsed_url.path:
                    return embed_src
                elif parsed_url.path.endswith("date-picker"):
                    queries = urllib.parse.parse_qs(parsed_url.query)
                    if "idx" in queries:
                        res = requests.get(embed_src)
                        index = int(queries["idx"][0]) - 1
                        puzzle_id = cls._select_puzzle_at_index_from_date_picker(
                            picker_src=res.text, index=index
                        )
                        puzzle_url = f"{embed_src.replace('date-picker', 'crossword')}&id={puzzle_id}"
                        return puzzle_url

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

        self.id = self._select_puzzle_at_index_from_date_picker(
            picker_src=res.text, index=0
        )

        self.get_and_add_picker_token(res.text)

        return self.find_puzzle_url_from_id(self.id)

    @staticmethod
    def _select_puzzle_at_index_from_date_picker(picker_src=None, index=0):
        if not picker_src:
            raise XWordDLException(
                "Bad call to puzzle selection function. Report this as a bug."
            )

        soup = BeautifulSoup(picker_src, "html.parser")

        param_tag = soup.find("script", id="params")
        param_obj = (
            json.loads(param_tag.string or "") if isinstance(param_tag, Tag) else {}
        )

        puzzles = param_obj.get("puzzles", [])

        if not puzzles:
            raise XWordDLException("Unable to find puzzles data from picker page.")

        return puzzles[index]["id"]

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
        res = self.session.get(solver_url)

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

            rawc = json.loads(script_tag.string or "").get("rawc") or ""

        if not rawc:
            raise XWordDLException("Unable to find rawc object in AmuseLabs page")

        xword_data = json.loads(deobfuscate_rawc(rawc))

        if not xword_data:
            raise XWordDLException("Unable to decode AmuseLabs rawc object")

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


# helper functions for rawc deobfuscation
# these were adapted from https://github.com/jpd236/kotwords/ and
# used here under the terms of that project's Apache license
# https://github.com/jpd236/kotwords/blob/master/LICENSE
def is_valid_key_prefix(rawc: str, key_prefix: List[int], spacing: int) -> bool:
    """
    Determine if the given key prefix could be valid.

    Simulates reversing chunks of the string and validates that:
    1. Base64 portions decode successfully
    2. Decoded bytes contain only valid UTF-8 (no invalid continuation bytes)
    """
    try:
        pos = 0
        chunk = []

        while pos < len(rawc):
            start_pos = pos
            key_index = 0

            # Assemble a chunk by reversing segments of specified lengths
            while key_index < len(key_prefix) and pos < len(rawc):
                chunk_length = min(key_prefix[key_index], len(rawc) - pos)
                chunk.append(rawc[pos : pos + chunk_length][::-1])
                pos += chunk_length
                key_index += 1

            chunk_str = "".join(chunk)

            # Align to 4-byte Base64 boundaries
            base64_start = ((start_pos + 3) // 4) * 4 - start_pos
            base64_end = (pos // 4) * 4 - start_pos

            if base64_start >= len(chunk_str) or base64_end <= base64_start:
                chunk.clear()
                pos += spacing
                continue

            b64_chunk = chunk_str[base64_start:base64_end]

            try:
                decoded = base64.b64decode(b64_chunk)
            except Exception:
                return False

            # Check for invalid UTF-8 bytes
            for byte in decoded:
                byte_val = byte if isinstance(byte, int) else ord(byte)
                if (
                    (byte_val < 32 and byte_val not in (0x09, 0x0A, 0x0D))
                    or byte_val == 0xC0
                    or byte_val == 0xC1
                    or byte_val >= 0xF5
                ):
                    return False

            pos += spacing
            chunk.clear()

        return True
    except Exception:
        return False


def deobfuscate_rawc_with_key(rawc: str, key: List[int]) -> str:
    """
    Deobfuscate using a known key.

    Reverses successive chunks of the string (using key digits as chunk lengths),
    then Base64-decodes the result.
    """
    try:
        buffer = list(rawc)
        i = 0
        segment_count = 0

        # Reverse chunks based on key digits
        while i < len(buffer) - 1:
            segment_length = min(key[segment_count % len(key)], len(buffer) - i)
            segment_count += 1

            left = i
            right = i + segment_length - 1
            while left < right:
                buffer[left], buffer[right] = buffer[right], buffer[left]
                left += 1
                right -= 1

            i += segment_length

        reversed_str = "".join(buffer)
        decoded_bytes = base64.b64decode(reversed_str)
        return decoded_bytes.decode("utf-8")
    except Exception:
        return ""


def deobfuscate_rawc(rawc: str) -> str:
    """
    Brute-force deobfuscate obfuscated crossword puzzle data.
    """
    # Heuristic: find "ye" or "we" which appear at the start of Base64-encoded JSON
    # In particular, these strings (reversed) correspond to `{"` and `{\n`
    ye_pos = rawc.find("ye")
    we_pos = rawc.find("we")

    ye_pos = ye_pos if ye_pos != -1 else len(rawc)
    we_pos = we_pos if we_pos != -1 else len(rawc)

    first_key_digit = min(ye_pos, we_pos) + 2

    # Initialize BFS queue
    if first_key_digit > 18:
        candidate_queue = deque([[]])
    else:
        candidate_queue = deque([[first_key_digit]])

    while candidate_queue:
        candidate_key_prefix = candidate_queue.popleft()

        if len(candidate_key_prefix) == 7:
            deobfuscated = deobfuscate_rawc_with_key(rawc, candidate_key_prefix)
            try:
                json.loads(deobfuscated)
                return deobfuscated
            except (json.JSONDecodeError, ValueError):
                continue

        # Expand by trying next digits (2-18)
        for next_digit in range(2, 19):
            new_candidate = candidate_key_prefix + [next_digit]

            remaining_digits = 7 - len(new_candidate)
            min_spacing = 2 * remaining_digits
            max_spacing = 18 * remaining_digits

            # Test if any spacing within bounds produces valid output
            if any(
                is_valid_key_prefix(rawc, new_candidate, spacing)
                for spacing in range(min_spacing, max_spacing + 1)
            ):
                candidate_queue.append(new_candidate)

    return "{}"
