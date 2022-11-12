#!/usr/bin/env python3

import argparse
import inspect
import sys
import textwrap
import time
import urllib

import requests

from getpass import getpass

from bs4 import BeautifulSoup

from . import downloader

from .util import *

with open(os.path.join(os.path.dirname(__file__), 'version')) as f:
    __version__ = f.read().strip()


def by_keyword(keyword, **kwargs):
    keyword_dict = {d[1].command: d[1] for d in get_supported_outlets()}
    selected_downloader = keyword_dict.get(keyword, None)

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
    filename = dl.pick_filename(puzzle, filename=kwargs.get('filename'))

    return puzzle, filename


def by_url(url, filename=None):
    netloc = urllib.parse.urlparse(url).netloc

    supported_sites = [('wsj.com', downloader.WSJDownloader),
                       ('newyorker.com', downloader.NewYorkerDownloader),
                       ('amuselabs.com', downloader.AmuseLabsDownloader)]

    dl = None

    supported_downloader = next((site[1] for site in supported_sites
                                 if site[0] in netloc), None)

    if supported_downloader:
        dl = supported_downloader(netloc=netloc)
        puzzle_url = url
    else:
        amuse_url = None
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')

        for iframe in soup.find_all('iframe'):
            src = urllib.parse.urljoin(url, iframe.get('src', '') or iframe.get('data-crossword-url', ''))
            if 'amuselabs.com' in src:
                amuse_url = src
                break

        if amuse_url:
            dl = AmuseLabsDownloader(netloc=netloc)
            puzzle_url = amuse_url

    if dl:
        puzzle = dl.download(puzzle_url)
    else:
        raise XWordDLException('Unable to find a puzzle at {}.'.format(url))

    filename = filename or dl.pick_filename(puzzle)

    return puzzle, filename


def get_supported_outlets():
    all_classes = inspect.getmembers(sys.modules['xword_dl.downloader'],
                                     inspect.isclass)
    dls = [d for d in all_classes if issubclass(d[1], 
                   downloader.BaseDownloader)
                   and hasattr(d[1], 'command')]

    return dls


def get_help_text_formatted_list():
    text = ''
    for d in sorted(get_supported_outlets(), key=lambda x: x[1].outlet.lower()):
        text += '{:<5} {}\n'.format(d[1].command, d[1].outlet)

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

    selector.add_argument('-d', '--date', nargs='*', metavar='',
                          help='a specific puzzle date to select',
                          default=[])

    parser.add_argument('-a', '--authenticate',
                        help=textwrap.dedent("""\
                            when used with the nyt puzzle keyword,
                            stores an authenticated New York Times cookie
                            without downloading a puzzle. If username
                            or password are not provided as flags,
                            xword-dl will prompt for those values
                            at runtime"""),
                        action='store_true',
                        default=False)

    parser.add_argument('-u', '--username',
                        help=textwrap.dedent("""\
                            username for a site that requires credentials
                            (currently only the New York Times)"""),
                        default=None)

    parser.add_argument('-p', '--password',
                        help=textwrap.dedent("""\
                            password for a site that requires credentials
                            (currently only the New York Times)"""),
                        default=None)

    parser.add_argument('-o', '--output',
                        help=textwrap.dedent("""\
                            the filename for the saved puzzle
                            (if not provided, a default value will be used)"""),
                        default=None)


    args = parser.parse_args()
    if args.authenticate and args.source == 'nyt':
        username = args.username or input("New York Times username: ")
        password = args.password or getpass("Password: ")

        try:
            dl = NewYorkTimesDownloader(username=username, password=password)
            sys.exit('Authentication successful.')
        except Exception as e:
            sys.exit(' '.join(['Authentication failed:', str(e)]))
    elif args.authenticate:
        sys.exit('Authentication flag must use a puzzle outlet keyword.')

    if not args.source:
        sys.exit(parser.print_help())

    options = {}
    if args.username:
        options['username'] = args.username
    if args.password:
        options['password'] = args.password
    if args.output:
        options['filename'] = args.output
    if args.date:
        options['date'] = ''.join(args.date)

    try:
        if args.source.startswith('http'):
            puzzle, filename = by_url(args.source,
                                      filename=args.output)
        else:
            puzzle, filename = by_keyword(args.source, **options)
    except XWordDLException as e:
        sys.exit(e)

    # specialcase the output file '-'
    if args.output == '-':
        sys.stdout.buffer.write (puzzle.tobytes())
    else:
        if not filename.endswith('.puz'):
            filename = filename + '.puz'
        save_puzzle(puzzle, filename)


if __name__ == '__main__':
    main()
