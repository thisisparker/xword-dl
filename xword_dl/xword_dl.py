#!/usr/bin/env python3

import argparse
import json
import os
import sys
import textwrap
import urllib.parse

import requests

from bs4 import BeautifulSoup

from .downloader import get_plugins
from .util import XWordDLException, parse_date_or_exit, save_puzzle

with open(os.path.join(os.path.dirname(__file__), 'version')) as f:
    __version__ = f.read().strip()

plugins = get_plugins()


def by_keyword(keyword, **kwargs):
    selected_downloader = next(
        (d for d in get_supported_outlets() if d.command == keyword), None
    )

    if selected_downloader:
        dl = selected_downloader(**kwargs)
    else:
        raise XWordDLException('Keyword {} not recognized.'.format(keyword))

    date = kwargs.get('date')

    if not date:
        puzzle_url = dl.find_latest()
    elif date and hasattr(dl, 'find_by_date'):
        parsed_date = parse_date_or_exit(date)
        dl.date = parsed_date
        puzzle_url = dl.find_by_date(parsed_date)
    else:
        raise XWordDLException(
            'Selection by date not available for {}.'.format(dl.outlet))

    puzzle = dl.download(puzzle_url)
    filename = dl.pick_filename(puzzle)

    return puzzle, filename


def by_url(url, **kwargs):
    supported_downloaders = [d for d in
            get_supported_outlets(command_only=False)
            if hasattr(d, 'matches_url')]

    dl = None

    for d in supported_downloaders:
        url_components = urllib.parse.urlparse(url)

        if d.matches_url(url_components):
            dl = d(url=url, **kwargs)
            puzzle_url = url
            break
    else:
        dl, puzzle_url = parse_for_embedded_puzzle(url, **kwargs)

    if dl:
        puzzle = dl.download(puzzle_url)
    else:
        raise XWordDLException('Unable to find a puzzle at {}.'.format(url))

    filename = dl.pick_filename(puzzle)

    return puzzle, filename


def parse_for_embedded_puzzle(url, **kwargs):
    supported_downloaders = [
        d
        for d in get_supported_outlets(command_only=False)
        if hasattr(d, 'matches_embed_url')
    ]

    res = requests.get(url, headers={'User-Agent':'xword-dl'})
    soup = BeautifulSoup(res.text, 'lxml')

    sources = [urllib.parse.urljoin(url,
                    iframe.get('data-crossword-url', '') or
                    iframe.get('data-src', '') or
                    iframe.get('src', ''))
                for iframe in soup.find_all('iframe')]

    sources = [src for src in sources if src != 'about:blank']

    sources.insert(0, url)

    for src in sources:
        for dlr in supported_downloaders:
            puzzle_url = dlr.matches_embed_url(src)
            if puzzle_url is not None:
                return (dlr(), puzzle_url)

    return None, None


def get_supported_outlets(command_only=True):
    if command_only:
        return [d for d in plugins if hasattr(d, 'command')]
    return plugins


def get_help_text_formatted_list():
    text = ''
    for d in sorted(get_supported_outlets(), key=lambda x: x.outlet.lower()):
        text += '{:<5} {}\n'.format(d.command, d.outlet)

    return text


def main():
    parser = argparse.ArgumentParser(prog='xword-dl',
                                     description=textwrap.dedent("""\
        xword-dl is a tool to download online crossword puzzles and save them
        locally as AcrossLite-compatible .puz files. It works with supported
        sites, a list of which can be found below.

        By default, xword-dl will download the most recent puzzle available at
        a given outlet, and some outlets support searching by date.
        """),
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-v', '--version',
                        action='version', version=__version__)

    parser.add_argument('source', nargs="?", help=textwrap.dedent("""\
                                specify a URL or a keyword to select an
                                outlet from which to download a puzzle.

                                Supported outlet keywords are:\n""") +
                        "{}".format(get_help_text_formatted_list()))

    selector = parser.add_mutually_exclusive_group()

    selector.add_argument('-l', '--latest',
                          help=textwrap.dedent("""\
                                select most recent available puzzle
                                (this is the default behavior)"""),
                          action='store_true',
                          default=True)

    selector.add_argument('-d', '--date',
                          help='a specific puzzle date to select',
                          default=None)

    parser.add_argument('-a', '--authenticate',
                        help=textwrap.dedent("""\
                            when used with a subscription-only puzzle source,
                            stores an authentication token without downloading
                            a puzzle. If username or password are not provided
                            as flags xword-dl will prompt for those values at
                            runtime"""),
                        action='store_true',
                        default=False)

    parser.add_argument('-u', '--username',
                        help=textwrap.dedent("""\
                            username for a site that requires credentials"""),
                        default=None)

    parser.add_argument('-p', '--password',
                        help=textwrap.dedent("""\
                            password for a site that requires credentials"""),
                        default=None)

    parser.add_argument('--preserve-html',
                        help=textwrap.dedent("""\
                            preserves any HTML present in scraped puzzle
                            (by default, HTML is converted into plain
                            markdown)"""),
                        action='store_true',
                        default=False)

    parser.add_argument('--settings',
                        help=textwrap.dedent("""\
                            JSON-encoded object specifying settings
                            values for given keys"""),
                        default=None)

    parser.add_argument('-o', '--output',
                        help=textwrap.dedent("""\
                            filename (or filename template) for the
                            saved puzzle. (if not provided, a default value
                            will be used)"""),
                        default=None)


    args = parser.parse_args()
    if args.authenticate and args.source:
        selected_downloader = next(
            (d for d in get_supported_outlets() if d.command == args.source), None
        )
        if selected_downloader is None:
            raise XWordDLException('Keyword {} not recognized.'.format(args.source))

        if not hasattr(selected_downloader, "authenticate"):
            sys.exit('This outlet does not support authentication.')

        selected_downloader.authenticate(args.username, args.password)

    elif args.authenticate:
        sys.exit('Authentication flag must use a puzzle outlet keyword.')

    if not args.source:
        sys.exit(parser.format_help())

    options = {}
    if args.username:
        options['username'] = args.username
    if args.password:
        options['password'] = args.password
    if args.preserve_html:
        options['preserve_html'] = args.preserve_html
    if args.output:
        options['filename'] = args.output
    if args.date:
        options['date'] = args.date
    if args.settings:
        try:
            raw_settings = json.loads(args.settings)
            settings = {k.replace('-','_'):raw_settings[k] for k in raw_settings}
        except json.JSONDecodeError:
            sys.exit('Settings object not valid JSON.')
        options.update(settings)

    try:
        if args.source.startswith('http'):
            puzzle, filename = by_url(args.source, **options)
        else:
            puzzle, filename = by_keyword(args.source, **options)
    except XWordDLException as e:
        sys.exit(str(e))

    # specialcase the output file '-'
    if args.output == '-':
        sys.stdout.buffer.write (puzzle.tobytes())
    else:
        if not filename.endswith('.puz'):
            filename = filename + '.puz'
        save_puzzle(puzzle, filename)


if __name__ == '__main__':
    main()
