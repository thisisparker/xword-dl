#!/usr/bin/env python3

import argparse
import json
import sys
import textwrap
import urllib.parse

import requests

from puz import Puzzle

from .downloader import get_plugins
from .downloader.basedownloader import BaseDownloader as __bd
from .util import XWordDLException, parse_date_or_exit, save_puzzle

try:
    from ._version import __version__ as __version__  # type: ignore
except ModuleNotFoundError:
    __version__ = "0.0.0-dev"

plugins = get_plugins()


def by_keyword(keyword: str, **kwargs) -> tuple[Puzzle, str]:
    selected_downloader = next(
        (d for d in get_supported_outlets(command_only=True) if d.command == keyword),
        None,
    )

    if selected_downloader:
        dl = selected_downloader(**kwargs)
    else:
        raise XWordDLException("Keyword {} not recognized.".format(keyword))

    date = kwargs.get("date")

    if not date:
        puzzle_url = dl.find_latest()
    elif date and hasattr(dl, "find_by_date"):
        parsed_date = parse_date_or_exit(date)
        dl.date = parsed_date
        puzzle_url = dl.find_by_date(parsed_date)
    else:
        raise XWordDLException(
            "Selection by date not available for {}.".format(dl.outlet)
        )

    puzzle = dl.download(puzzle_url)
    filename = dl.pick_filename(puzzle)

    return puzzle, filename


def by_url(url: str, **kwargs) -> tuple[Puzzle, str]:
    supported_downloaders = get_supported_outlets(matches_url=True)

    dl = None

    for d in supported_downloaders:
        url_components = urllib.parse.urlparse(url)

        if d.matches_url(url_components):
            dl = d(url=url, **kwargs)
            puzzle_url = url
            break
    else:
        dl, puzzle_url = parse_for_embedded_puzzle(url, **kwargs)

    if dl and puzzle_url:
        puzzle = dl.download(puzzle_url)
    else:
        raise XWordDLException("Unable to find a puzzle at {}.".format(url))

    filename = dl.pick_filename(puzzle)

    return puzzle, filename


def parse_for_embedded_puzzle(url: str, **kwargs):
    supported_downloaders = get_supported_outlets(matches_embed_pattern=True)

    res = requests.get(url, headers={"User-Agent": "xword-dl"})
    page_source = res.text

    for dlr in supported_downloaders:
        puzzle_url = dlr.matches_embed_pattern(url, page_source)
        # TODO: would it be better to just return a URL and have controller
        # request this from the plugin via normal methods?
        if puzzle_url is not None:
            return (dlr(url=url, **kwargs), puzzle_url)

    return None, None


def get_supported_outlets(
    command_only=False, matches_url=False, matches_embed_pattern=False
):
    matched_plugins = []

    # build a list of plugins with the requested features
    for plugin in plugins:
        if command_only and not plugin.command:
            continue
        # detects whether a plugin has implemented matches_url as a @classmethod
        if matches_url and (
            getattr(plugin.matches_url, "__func__")
            is getattr(__bd.matches_url, "__func__")
        ):
            continue
        if matches_embed_pattern and (
            (
                getattr(plugin.matches_embed_pattern, "__func__")
                is getattr(__bd.matches_embed_pattern, "__func__")
            )
            or ("matches_embed_pattern" not in plugin.__dict__)
        ):
            continue
        matched_plugins.append(plugin)
    return matched_plugins


def get_help_text_formatted_list():
    text = ""
    for d in sorted(
        get_supported_outlets(command_only=True), key=lambda x: x.outlet.lower()
    ):
        text += "{:<5} {}\n".format(d.command, d.outlet)

    return text


def main():
    parser = argparse.ArgumentParser(
        prog="xword-dl",
        description=textwrap.dedent("""\
        xword-dl is a tool to download online crossword puzzles and save them
        locally as AcrossLite-compatible .puz files. It works with supported
        sites, a list of which can be found below.

        By default, xword-dl will download the most recent puzzle available at
        a given outlet, and some outlets support searching by date.
        """),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("-v", "--version", action="version", version=__version__)

    parser.add_argument(
        "source",
        nargs="?",
        help=textwrap.dedent("""\
                                specify a URL or a keyword to select an
                                outlet from which to download a puzzle.

                                Supported outlet keywords are:\n""")
        + "{}".format(get_help_text_formatted_list()),
    )

    selector = parser.add_mutually_exclusive_group()

    selector.add_argument(
        "-l",
        "--latest",
        help=textwrap.dedent("""\
                                select most recent available puzzle
                                (this is the default behavior)"""),
        action="store_true",
        default=True,
    )

    selector.add_argument(
        "-d", "--date", help="a specific puzzle date to select", default=None
    )

    parser.add_argument(
        "-a",
        "--authenticate",
        help=textwrap.dedent("""\
                            when used with a subscription-only puzzle source,
                            stores an authentication token without downloading
                            a puzzle. If username or password are not provided
                            as flags xword-dl will prompt for those values at
                            runtime"""),
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "-u",
        "--username",
        help=textwrap.dedent("""\
                            username for a site that requires credentials"""),
        default=None,
    )

    parser.add_argument(
        "-p",
        "--password",
        help=textwrap.dedent("""\
                            password for a site that requires credentials"""),
        default=None,
    )

    parser.add_argument(
        "--preserve-html",
        help=textwrap.dedent("""\
                            preserves any HTML present in scraped puzzle
                            (by default, HTML is converted into plain
                            markdown)"""),
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--settings",
        help=textwrap.dedent("""\
                            JSON-encoded object specifying settings
                            values for given keys"""),
        default=None,
    )

    parser.add_argument(
        "-o",
        "--output",
        help=textwrap.dedent("""\
                            filename (or filename template) for the
                            saved puzzle. (if not provided, a default value
                            will be used)"""),
        default=None,
    )

    args = parser.parse_args()
    if args.authenticate and args.source:
        selected_downloader = next(
            (
                d
                for d in get_supported_outlets(command_only=True)
                if d.command == args.source
            ),
            None,
        )
        if selected_downloader is None:
            raise XWordDLException("Keyword {} not recognized.".format(args.source))

        if not hasattr(selected_downloader, "authenticate"):
            sys.exit("This outlet does not support authentication.")

        selected_downloader.authenticate(args.username, args.password)

    elif args.authenticate:
        sys.exit("Authentication flag must use a puzzle outlet keyword.")

    if not args.source:
        sys.exit(parser.format_help())

    options = {}
    if args.username:
        options["username"] = args.username
    if args.password:
        options["password"] = args.password
    if args.preserve_html:
        options["preserve_html"] = args.preserve_html
    if args.output:
        options["filename"] = args.output
    if args.date:
        options["date"] = args.date
    if args.settings:
        try:
            raw_settings = json.loads(args.settings)
            settings = {k.replace("-", "_"): raw_settings[k] for k in raw_settings}
        except json.JSONDecodeError:
            sys.exit("Settings object not valid JSON.")
        options.update(settings)

    try:
        if args.source.startswith("http"):
            puzzle, filename = by_url(args.source, **options)
        else:
            puzzle, filename = by_keyword(args.source, **options)
    except XWordDLException as e:
        sys.exit(str(e))

    # specialcase the output file '-'
    if args.output == "-":
        sys.stdout.buffer.write(puzzle.tobytes())
    else:
        if not filename.endswith(".puz"):
            filename = filename + ".puz"
        save_puzzle(puzzle, filename)


if __name__ == "__main__":
    main()
