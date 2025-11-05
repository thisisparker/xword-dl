import os
import sys

import dateparser
import emoji
import yaml
from puz import Puzzle

from anyascii import anyascii
from html_text.html_text import extract_text


def latinize(string):
    """Get latin-1 version of string using the anyascii module.
    # replacement values for these characters to unidecode, we prevent it from
    # changing them.
    _unidecode.Cache[0] = [chr(c) if c > 127 else "" for c in range(256)]

        Calling it on one character at a time is still efficient because
        anyascii caches lookups using a module global."""

    # Replace any colons coming from anyascii with empty string to match previous unidecode behavior
    return "".join(
        c if ord(c) <= 0xFF else anyascii(c).replace(":", "") for c in string
    )


CONFIG_PATH = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
CONFIG_PATH = os.path.join(CONFIG_PATH, "xword-dl/xword-dl.yaml")

if not os.path.exists(CONFIG_PATH):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    open(CONFIG_PATH, "a").close()


class XWordDLException(Exception):
    pass


def save_puzzle(puzzle: Puzzle, filename: str):
    if not os.path.exists(filename):
        puzzle.save(filename)
        msg = (
            "Puzzle downloaded and saved as {}.".format(filename)
            if sys.stdout.isatty()
            else filename
        )
        print(msg)
    else:
        print(
            "Not saving: a file named {} already exists.".format(filename),
            file=sys.stderr,
        )


def join_bylines(byline_list: list[str], and_word="&"):
    return (
        ", ".join(byline_list[:-1]) + f", {and_word} " + byline_list[-1]
        if len(byline_list) > 2
        else f" {and_word} ".join(byline_list)
    )


def remove_invalid_chars_from_filename(filename: str):
    invalid_chars = r'<>:"/\|?*'

    for char in invalid_chars:
        filename = filename.replace(char, "")

    return filename


def cleanup(field: str, preserve_html=False):
    if preserve_html:
        field = latinize(emoji.demojize(field)).strip()
    else:
        field = latinize(emoji.demojize(extract_text(field))).strip()
    return field


def sanitize_for_puzfile(puzzle: Puzzle, preserve_html=False) -> Puzzle:
    puzzle.title = cleanup(puzzle.title, preserve_html)
    puzzle.author = cleanup(puzzle.author, preserve_html)
    puzzle.copyright = cleanup(puzzle.copyright, preserve_html)

    puzzle.notes = cleanup(puzzle.notes, preserve_html)

    puzzle.clues = [cleanup(clue, preserve_html) for clue in puzzle.clues]

    return puzzle


def parse_date(entered_date: str):
    return dateparser.parse(entered_date, settings={"PREFER_DATES_FROM": "past"})


def parse_date_or_exit(entered_date: str):
    guessed_dt = parse_date(entered_date)

    if not guessed_dt:
        raise XWordDLException(
            'Unable to determine a date from "{}".'.format(entered_date)
        )

    return guessed_dt


def update_config_file(heading: str, new_values_dict: dict):
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f) or {}

    if heading not in config:
        config[heading] = {}

    config[heading].update(new_values_dict)

    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f)


def read_config_values(heading: str):
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f) or {}

    # config file keys and command line flags use '-', python uses '_', so we
    # replace '-' with '_' for the settings object
    raw_subsettings = config.get(heading) or {}
    subsettings = {k.replace("-", "_"): raw_subsettings[k] for k in raw_subsettings}

    return subsettings
