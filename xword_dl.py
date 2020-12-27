#!/usr/bin/env python3

import argparse
import base64
import datetime
import inspect
import json
import os
import sys
import time
import urllib

import dateparser
import puz
import requests

from bs4 import BeautifulSoup
from html2text import html2text
from unidecode import unidecode

__version__ = '2020.12.27'

def save_puzzle(puzzle, filename):
    if not os.path.exists(filename):
        puzzle.save(filename)
        print("Puzzle downloaded and saved as {}.".format(filename))
    else:
        print("Not saving: a file named {} already exists.".format(filename))

def remove_invalid_chars_from_filename(filename):
    invalid_chars = '<>:"/\|?*'

    for char in invalid_chars:
        filename = filename.replace(char, '')

    return filename

def parse_date(entered_date):
    return dateparser.parse(entered_date)

def parse_date_or_exit(entered_date):
    guessed_dt = parse_date(entered_date)

    if not guessed_dt:
        sys.exit('Unable to determine a date from "{}".'.format(entered_date))

    return guessed_dt


class BaseDownloader:
    def __init__(self):
        self.date = None

    def pick_filename(self, puzzle, **kwargs):
        title = kwargs.get('title', puzzle.title)
        date = kwargs.get('date', self.date)

        date = date.strftime('%Y%m%d') if date else None

        filename_components = [component for component in
                                            [self.outlet_prefix,
                                             date,
                                             title] if component]

        return " - ".join(filename_components) + '.puz'

    def find_solver(self, url):
        """Given a URL for a puzzle, returns the essential 'solver' URL.

        This is implemented in subclasses, and in instances where there is no
        separate 'landing page' URL for a puzzle, it may be a very transparent
        pass-through.
        """
        raise NotImplementedError

    def fetch_data(self, solver_url):
        """Given a URL from the find_solver function, return JSON crossword data

        This is implemented in subclasses and the returned data will not be
        standardized until later.
        """
        raise NotImplementedError

    def parse_xword(self, xword_data):
        """Given a blob of crossword data, parse and stuff into puz format.

        This method is implemented in subclasses based on the differences in
        the data format in situ.
        """
        raise NotImplementedError

    def download(self, url):
        """Download, parse, and return a puzzle at a given URL."""

        solver_url = self.find_solver(url)
        xword_data = self.fetch_data(solver_url)
        puzzle = self.parse_xword(xword_data)

        return puzzle


class AmuseLabsDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        super().__init__()

        self.id = None

    def find_latest(self):
        res = requests.get(self.picker_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        puzzles = soup.find('div', attrs={'class':'puzzles'})
        puzzle_ids = puzzles.findAll('div', attrs={'class':'tile'})
        if not puzzle_ids:
            puzzle_ids = puzzles.findAll('li', attrs={'class':'tile'})
        self.id = puzzle_ids[0].get('data-id','')

        return self.find_puzzle_url_from_id(self.id)

    def find_puzzle_url_from_id(self, puzzle_id):
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
        rawc = next((line.strip() for line in res.text.splitlines()
                        if 'window.rawc' in line), None)

        if not rawc:
            sys.exit("Crossword puzzle not found.")

        rawc = rawc.split("'")[1]

        xword_data = json.loads(base64.b64decode(rawc).decode("utf-8"))

        return xword_data

    def parse_xword(self, xword_data):
        puzzle = puz.Puzzle()
        puzzle.title = xword_data.get('title', '').strip()
        puzzle.author = xword_data.get('author', '').strip()
        puzzle.copyright = xword_data.get('copyright', '').strip()
        puzzle.width = xword_data.get('w')
        puzzle.height = xword_data.get('h')

        markup_data = xword_data.get('cellInfos', '')

        circled = [(square['x'], square['y']) for square in markup_data
                                                      if square['isCircled']]

        solution = ''
        fill = ''
        markup = b''
        rebus_board = []
        rebus_index = 0
        rebus_table = ''

        box = xword_data['box']
        for row_num in range(xword_data.get('h')):
            for col_num, column in enumerate(box):
                cell = column[row_num]
                if cell == '\x00':
                    solution += '.'
                    fill += '.'
                    markup += b'\x00'
                    rebus_board.append(0)
                elif len(cell) == 1:
                    solution += cell
                    fill += '-'
                    markup += b'\x80' if (col_num, row_num) in circled else b'\x00'
                    rebus_board.append(0)
                else:
                    solution += cell[0]
                    fill += '-'
                    rebus_board.append(rebus_index + 1)
                    rebus_table += '{:2d}:{};'.format(rebus_index, cell)
                    rebus_index += 1

        puzzle.solution = solution
        puzzle.fill = fill

        placed_words = xword_data['placedWords']
        across_words = [word for word in placed_words if word['acrossNotDown']]
        down_words = [word for word in placed_words if not word['acrossNotDown']]

        weirdass_puz_clue_sorting = sorted(placed_words, key=
                                            lambda word: (word['y'], word['x'],
                                                    not word['acrossNotDown']))

        clues = [word['clue']['clue'] for word in weirdass_puz_clue_sorting]

        normalized_clues = [html2text(unidecode(clue), bodywidth=0)
                                for clue in clues]
        puzzle.clues.extend(normalized_clues)

        has_markup = b'\x80' in markup
        has_rebus = any(rebus_board)

        if has_markup:
            puzzle.extensions[b'GEXT'] = markup
            puzzle._extensions_order.append(b'GEXT')
            puzzle.markup()

        if has_rebus:
            puzzle.extensions[b'GRBS'] = bytes(rebus_board)
            puzzle.extensions[b'RTBL'] = rebus_table.encode(puz.ENCODING)
            puzzle._extensions_order.extend([b'GRBS', b'RTBL'])
            puzzle.rebus()

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        if not self.date and self.id:
            self.guess_date_from_id(self.id)
        return super().pick_filename(puzzle, **kwargs)


class WaPoDownloader(AmuseLabsDownloader):
    command = 'wp'
    outlet = 'Washington Post'
    outlet_prefix = 'WaPo'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn1.amuselabs.com/wapo/wp-picker?set=wapo-eb'
        self.url_from_id = 'https://cdn1.amuselabs.com/wapo/crossword?id={puzzle_id}&set=wapo-eb'

    def guess_date_from_id(self, puzzle_id):
        self.date = datetime.datetime.strptime('20'
                + puzzle_id.split('_')[1], '%Y%m%d')

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%y%m%d')
        self.id = 'ebirnholz_' + url_formatted_date

        return self.find_puzzle_url_from_id(self.id)


class AtlanticDownloader(AmuseLabsDownloader):
    command = 'atl'
    outlet = 'Atlantic'
    outlet_prefix = 'Atlantic'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn3.amuselabs.com/atlantic/date-picker?set=atlantic'
        self.url_from_id = 'https://cdn3.amuselabs.com/atlantic/crossword?id={puzzle_id}&set=atlantic'

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%Y%m%d')
        self.id = 'atlantic_' + url_formatted_date

        return self.find_puzzle_url_from_id(self.id)


class NewsdayDownloader(AmuseLabsDownloader):
    command = 'nd'
    outlet = 'Newsday'
    outlet_prefix = 'Newsday'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn2.amuselabs.com/pmm/date-picker?set=creatorsweb'
        self.url_from_id = 'https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=creatorsweb'

    def guess_date_from_id(self, puzzle_id):
        date_string = puzzle_id.split('_')[2]
        self.date = datetime.datetime.strptime(date_string, '%Y%m%d')

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%Y%m%d')
        self.id = 'Creators_WEB_' + url_formatted_date

        return self.find_puzzle_url_from_id(self.id)


class LATimesDownloader(AmuseLabsDownloader):
    command = 'lat'
    outlet = 'Los Angeles Times'
    outlet_prefix = 'LA Times'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn4.amuselabs.com/lat/date-picker?set=latimes'
        self.url_from_id = 'https://cdn4.amuselabs.com/lat/crossword?id={puzzle_id}&set=latimes'

    def guess_date_from_id(self, puzzle_id):
        date_string = ''.join([char for char in puzzle_id if char.isdigit()])
        self.date = datetime.datetime.strptime(date_string, '%y%m%d')

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%y%m%d')
        self.id = 'tca' + url_formatted_date

        return self.find_puzzle_url_from_id(self.id)

    def pick_filename(self, puzzle, **kwargs):
        split_on_dashes = puzzle.title.split(' - ')
        if len(split_on_dashes) > 1:
            use_title = split_on_dashes[-1].strip()
        else:
            use_title = ''

        return super().pick_filename(puzzle, title=use_title)


class NewYorkerDownloader(AmuseLabsDownloader):
    command = 'tny'
    outlet = 'New Yorker'
    outlet_prefix = 'New Yorker'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = 'https://cdn3.amuselabs.com/tny/crossword?id={puzzle_id}&set=tny-weekly'

    def guess_date_from_id(self, puzzle_id):
        self.date = datetime.datetime.strftime(puzzle_id.split('_')[-1])

    def find_by_date(self, dt):
        url_format = dt.strftime('%Y/%m/%d')
        guessed_url = urllib.parse.urljoin(
                'https://www.newyorker.com/puzzles-and-games-dept/crossword/',
                url_format)
        return guessed_url

    def find_latest(self):
        index_url = "https://www.newyorker.com/puzzles-and-games-dept/crossword"
        index_res = requests.get(index_url)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_fragment = next(a for a in index_soup.findAll('a') if a.find('h4'))['href']
        latest_absolute = urllib.parse.urljoin('https://www.newyorker.com',
                                                latest_fragment)

        landing_page_url = latest_absolute

        return landing_page_url

    def find_solver(self, url):
        res = requests.get(url)

        if res.status_code == 404:
            sys.exit('Unable to find a puzzle at {}'.format(url))
 
        soup = BeautifulSoup(res.text, "html.parser")

        script_tag = soup.find('script', attrs={'type': 'application/ld+json'})

        json_data = json.loads(script_tag.contents[0])

        iframe_url = json_data['articleBody'].strip().strip('[]')[len('#crossword: '):]

        query = urllib.parse.urlparse(iframe_url).query
        query_id = urllib.parse.parse_qs(query)['id']
        self.id = query_id[0]

        pubdate = soup.find('time').get_text()
        pubdate_dt = dateparser.parse(pubdate)

        self.date = pubdate_dt

        return self.find_puzzle_url_from_id(self.id)

    def pick_filename(self, puzzle, **kwargs):
        try:
            supra, main = puzzle.title.split(':')
            if supra == 'The Crossword' and dateparser.parse(main):
                title = ''
            else:
                title = main.strip()
        except ValueError:
            title = puzzle.title
        return super().pick_filename(puzzle, title=title)


class WSJDownloader(BaseDownloader):
    command = 'wsj'
    outlet = 'Wall Street Journal'
    outlet_prefix = 'WSJ'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.headers = {'User-Agent':'xword-dl'}

    def find_latest(self):
        url = "https://www.wsj.com/news/types/crossword"

        headlines = ''
        attempts = 5

        while attempts and not headlines:
            res = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            headlines = soup.find('main').find('h3')

            if headlines:
                break
            else:
                print('Unable to find latest puzzle. Trying again.')
                time.sleep(2)
                attempts -= 1
        else:
            sys.exit('Unable to find latest puzzle.')

        latest_url = headlines.find('a').get('href', None)

        return latest_url

    def find_solver(self, url):
        if '/puzzles/crossword/' in url:
            return url
        else:
            res = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            puzzle_link = soup.find('iframe').get('src')
            return self.find_solver(puzzle_link)

    def fetch_data(self, solver_url):
        data_url = solver_url.replace('index.html', 'data.json')
        return requests.get(data_url, headers=self.headers).json()['data']

    def parse_xword(self, xword_data):
        xword_metadata = xword_data.get('copy', '')
        xword_data = xword_data.get('grid','')

        date_string = xword_metadata.get('date-publish-analytics').split()[0]

        self.date = datetime.datetime.strptime(date_string, '%Y/%m/%d')

        fetched = {}
        for field in ['title', 'byline', 'publisher']:
            fetched[field] = html2text(xword_metadata.get(field, ''), bodywidth=0).strip()

        puzzle = puz.Puzzle()
        puzzle.title = fetched.get('title')
        puzzle.author = fetched.get('byline')
        puzzle.copyright = fetched.get('publisher')
        puzzle.width = int(xword_metadata.get('gridsize').get('cols'))
        puzzle.height = int(xword_metadata.get('gridsize').get('rows'))


        solution = ''
        fill = ''
        markup = b''

        for row in xword_data:
            for cell in row:
                if not cell['Letter']:
                    fill += '.'
                    solution += '.'
                    markup += b'\x00'
                else:
                    fill += '-'
                    solution += cell['Letter']
                    markup += (b'\x80' if (cell.get('style','')
                                           and cell['style']['shapebg']
                                           == 'circle') \
                                       else b'\x00')

        puzzle.fill = fill
        puzzle.solution = solution

        clue_list = xword_metadata['clues'][0]['clues'] + xword_metadata['clues'][1]['clues']
        sorted_clue_list = sorted(clue_list, key=lambda x: int(x['number']))

        clues = [clue['clue'] for clue in sorted_clue_list]
        normalized_clues = [html2text(unidecode(clue), bodywidth=0) for clue in clues]

        puzzle.clues = normalized_clues

        has_markup = b'\x80' in markup

        if has_markup:
            puzzle.extensions[b'GEXT'] = markup
            puzzle._extensions_order.append(b'GEXT')
            puzzle.markup()

        return puzzle


class USATodayDownloader(BaseDownloader):
    command = 'usa'
    outlet = 'USA Today'
    outlet_prefix = 'USA Today'

    def __init__(self, **kwargs):
        super().__init__()

    def find_by_date(self, dt):
        self.date = dt

        hardcoded_blob = 'https://gamedata.services.amuniversal.com/c/uupuz/l/U2FsdGVkX18CR3EauHsCV8JgqcLh1ptpjBeQ%2Bnjkzhu8zNO00WYK6b%2BaiZHnKcAD%0A9vwtmWJp2uHE9XU1bRw2gA%3D%3D/g/usaon/d/'

        url_format = dt.strftime('%Y-%m-%d')
        return hardcoded_blob + url_format + '/data.json'

    def find_latest(self):
        dt = datetime.datetime.today()
        return self.find_by_date(dt)

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url):
        attempts = 3
        while attempts:
            try:
                res = requests.get(solver_url)
                xword_data = res.json()
                break
            except json.JSONDecodeError:
                print('Unable to download puzzle data. Trying again.')
                time.sleep(2)
                attempts -= 1
        else:
            sys.exit('Unable to download puzzle data.')
        return xword_data

    def parse_xword(self, xword_data):
        puzzle = puz.Puzzle()
        puzzle.title = xword_data.get('Title', '')
        puzzle.author = ''.join([xword_data.get('Author', ''),
                                       ' / Ed. ',
                                       xword_data.get('Editor', '')])
        puzzle.copyright = xword_data.get('Copyright', '')
        puzzle.width = int(xword_data.get('Width'))
        puzzle.height = int(xword_data.get('Height'))

        solution = xword_data.get('AllAnswer').replace('-','.')

        puzzle.solution = solution

        fill = ''
        for letter in solution:
            if letter == '.':
                fill += '.'
            else:
                fill += '-'
        puzzle.fill = fill

        across_clues = xword_data['AcrossClue'].splitlines()
        down_clues = xword_data['DownClue'].splitlines()[:-1]

        clues_list = across_clues + down_clues

        clues_list_stripped = [{'number':clue.split('|')[0],
                                'clue':clue.split('|')[1]} for clue in clues_list]

        clues_sorted = sorted(clues_list_stripped, key=lambda x: x['number'])

        clues = [clue['clue'] for clue in clues_sorted]

        puzzle.clues = clues

        return puzzle


def main():
    parser = argparse.ArgumentParser(prog='xword-dl', description="""
        xword-dl is a tool to download online crossword puzzles and save them
        locally as AcrossLite-compatible .puz files. It only works with
        supported sites, a list of which is found below.

        By default, xword-dl will download the most recent puzzle available at
        a given outlet, but some outlets support specifying by date or by URL.
        Add --help (or -h) to an outlet command to see which options are
        available.
        """)
    parser.set_defaults(downloader_class=None)

    fullpath = os.path.abspath(os.path.dirname(__file__))

    parser.add_argument('-v', '--version', action='version', version=__version__)

    # I don't remember why this was in here, but it probably shouldn't be
    # parser.add_argument('url', nargs="?",
    #                        help='URL of puzzle to download')

    extractor_parent = argparse.ArgumentParser(add_help=False)
    extractor_parent.add_argument('-o', '--output',
                            help="""
                            the filename for the saved puzzle
                            (if not provided, a default value will be used)""",
                            default=None)
    extractor_parent.set_defaults(date=None, spec_url=None, latest=None)

    latest_parent = argparse.ArgumentParser(add_help=False)
    latest_parent.add_argument('-l', '--latest',
                            help="""
                                select most recent available puzzle
                                (this is the default behavior)""",
                            action='store_true',
                            default=True)

    date_parent = argparse.ArgumentParser(add_help=False)
    date_parent.add_argument('-d', '--date', nargs='*', metavar='',
                            help='a specific puzzle date to select')


    url_parent = argparse.ArgumentParser(add_help=False)
    url_parent.add_argument('-u', '--url', metavar='URL', dest='spec_url',
                            help='a specific puzzle URL to download')

    subparsers = parser.add_subparsers(title='sites',
                            description='Supported puzzle sources',
                            dest='subparser_name')

    all_classes = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    downloaders = [d for d in all_classes if issubclass(d[1], BaseDownloader)
                                          and hasattr(d[1], 'command')]
    for d in downloaders:
        parents = [latest_parent, extractor_parent]
        if hasattr(d[1], 'find_by_date'):
            parents.insert(1, date_parent)
        if d[0] in ['WSJDownloader', 'NewYorkerDownloader']:
            parents.insert(1, url_parent)
        sp = subparsers.add_parser(d[1].command,
                              parents=parents,
                              help='download {} puzzle'.format(d[1].outlet))
        sp.set_defaults(downloader_class=d[1])

    args = parser.parse_args()

    if not args.downloader_class:
        sys.exit(parser.print_help())

    dl = args.downloader_class()

    if args.date:
        parsed_date = parse_date_or_exit(''.join(args.date))
        dl.date = parsed_date
        puzzle_url = dl.find_by_date(parsed_date)

    elif args.spec_url:
        puzzle_url = args.spec_url

    elif args.latest:
        puzzle_url = dl.find_latest()

    puzzle = dl.download(puzzle_url)

    filename = args.output or dl.pick_filename(puzzle=puzzle)

    if not filename.endswith('.puz'):
        filename = filename + '.puz'

    filename = remove_invalid_chars_from_filename(filename)

    save_puzzle(puzzle, filename)

if __name__ == '__main__':
    main()
