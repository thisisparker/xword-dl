#!/usr/bin/env python3

import argparse
import base64
import json
import os
import sys
import time
import urllib

import dateparser
import puz
import requests
import xmltodict

from bs4 import BeautifulSoup
from html2text import html2text
from unidecode import unidecode

class BaseDownloader:
    def __init__(self, output=None):
        self.output = output
        if self.output and not self.output.endswith('.puz'):
            self.output = self.output + '.puz'
        self.puzfile = puz.Puzzle()

        self.outlet_prefix = None
        self.date = None

    def find_by_date(self, entered_date):
        guessed_dt = dateparser.parse(entered_date)
        if guessed_dt:
            readable_date = guessed_dt.strftime('%A, %B %d')
            print("Attempting to download a puzzle for {}.".format(readable_date))
            self.dt = guessed_dt
            self.date = self.dt.strftime('%Y%m%d')
        else:
            sys.exit('Unable to determine a date from "{}".'.format(entered_date))

        self.guess_url_from_date()

    def pick_filename(self):
        filename_components = [component for component in
                                            [self.outlet_prefix, self.date,
                                             self.puzfile.title] if component]
        self.output =  " - ".join(filename_components) + '.puz'

    def save_puz(self):
        if not self.output:
            self.pick_filename()

        invalid_chars = '<>:"/\|?*'

        for char in invalid_chars:
            self.output = self.output.replace(char, '')

        if not os.path.exists(self.output):
            self.puzfile.save(self.output)
            print("Puzzle downloaded and saved as {}.".format(self.output))
        else:
            print("Not saving: a file named {} already exists.".format(self.output))


class AmuseLabsDownloader(BaseDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output)

    def find_latest(self):
        res = requests.get(self.picker_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        puzzles = soup.find('div', attrs={'class':'puzzles'})
        puzzle_ids = puzzles.findAll('div', attrs={'class':'tile'})
        if not puzzle_ids:
            puzzle_ids = puzzles.findAll('li', attrs={'class':'tile'})
        self.id = puzzle_ids[0].get('data-id','')

        self.find_puzzle_url_from_id()

    def find_puzzle_url_from_id(self):
        self.url = self.url_from_id.format(puzzle_id = self.id)

    def guess_date_from_id(self):
        self.date = self.id.split('_')[-1]

    def download(self):
        res = requests.get(self.url)
        rawc = next((line.strip() for line in res.text.splitlines()
                        if 'window.rawc' in line), None)

        if not rawc:
            sys.exit("Crossword puzzle not found.")

        rawc = rawc.split("'")[1]

        xword_data = json.loads(base64.b64decode(rawc).decode("utf-8"))

        self.puzfile.title = xword_data.get('title', '')
        self.puzfile.author = xword_data.get('author', '')
        self.puzfile.copyright = xword_data.get('copyright', '')
        self.puzfile.width = xword_data.get('w')
        self.puzfile.height = xword_data.get('h')

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

        self.puzfile.solution = solution
        self.puzfile.fill = fill

        placed_words = xword_data['placedWords']
        across_words = [word for word in placed_words if word['acrossNotDown']]
        down_words = [word for word in placed_words if not word['acrossNotDown']]

        weirdass_puz_clue_sorting = sorted(placed_words, key=
                                                lambda word: (word['y'], word['x'],
                                                not word['acrossNotDown']))

        clues = [word['clue']['clue'] for word in weirdass_puz_clue_sorting]

        normalized_clues = [html2text(unidecode(clue), bodywidth=0) for clue in clues]
        self.puzfile.clues.extend(normalized_clues)

        has_markup = b'\x80' in markup
        has_rebus = any(rebus_board)

        if has_markup:
            self.puzfile.extensions[b'GEXT'] = markup
            self.puzfile._extensions_order.append(b'GEXT')
            self.puzfile.markup()

        if has_rebus:
            self.puzfile.extensions[b'GRBS'] = bytes(rebus_board)
            self.puzfile.extensions[b'RTBL'] = rebus_table.encode(puz.ENCODING)
            self.puzfile._extensions_order.extend([b'GRBS', b'RTBL'])
            self.puzfile.rebus()

    def save_puz(self):
        if not self.output and not self.date:
            self.guess_date_from_id()
        super().save_puz()


class WaPoDownloader(AmuseLabsDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

        self.picker_url = 'https://cdn1.amuselabs.com/wapo/wp-picker?set=wapo-eb'
        self.url_from_id = 'https://cdn1.amuselabs.com/wapo/crossword?id={puzzle_id}&set=wapo-eb'

        self.outlet_prefix = 'WaPo'

    def guess_date_from_id(self):
        self.date = '20' + self.id.split('_')[1]

    def guess_url_from_date(self):
        url_formatted_date = self.dt.strftime('%y%m%d')
        self.id = 'ebirnholz_' + url_formatted_date

        self.find_puzzle_url_from_id()

    def find_solver(self, url):
        self.url = url


class AtlanticDownloader(AmuseLabsDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

        self.picker_url = 'https://cdn3.amuselabs.com/atlantic/date-picker?set=atlantic'
        self.url_from_id = 'https://cdn3.amuselabs.com/atlantic/crossword?id={puzzle_id}&set=atlantic'

        self.outlet_prefix = 'Atlantic'

    def guess_url_from_date(self):
        url_formatted_date = self.dt.strftime('%Y%m%d')
        self.id = 'atlantic_' + url_formatted_date

        self.find_puzzle_url_from_id()

    def find_solver(self, url):
        self.url = url


class NewsdayDownloader(AmuseLabsDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

        self.picker_url = 'https://cdn2.amuselabs.com/pmm/date-picker?set=creatorsweb'
        self.url_from_id = 'https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=creatorsweb'

        self.outlet_prefix = 'Newsday'

    def guess_url_from_date(self):
        url_formatted_date = self.dt.strftime('%Y%m%d')
        self.id = 'Creators_WEB_' + url_formatted_date

        self.find_puzzle_url_from_id()

    def find_solver(self, url):
        self.url = url


class LATimesDownloader(AmuseLabsDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

        self.picker_url = 'https://cdn4.amuselabs.com/lat/date-picker?set=latimes'
        self.url_from_id = 'https://cdn4.amuselabs.com/lat/crossword?id={puzzle_id}&set=latimes'

        self.outlet_prefix = 'LA Times'

    def guess_date_from_id(self):
        self.date = '20' + ''.join([char for char in self.id if char.isdigit()])

    def guess_url_from_date(self):
        url_formatted_date = self.dt.strftime('%y%m%d')
        self.id = 'tca' + url_formatted_date

        self.find_puzzle_url_from_id()

    def find_solver(self, url):
        self.url = url

    def pick_filename(self):
        split_on_dashes = self.puzfile.title.split(' - ')
        if len(split_on_dashes) > 1:
            use_title = split_on_dashes[-1].strip()
        else:
            use_title = ''

        filename_components = [component for component in
                                            [self.outlet_prefix, self.date,
                                             use_title] if component]
        self.output =  " - ".join(filename_components) + '.puz'


class NewYorkerDownloader(AmuseLabsDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

        self.url_from_id = 'https://cdn3.amuselabs.com/tny/crossword?id={puzzle_id}&set=tny-weekly'

        self.outlet_prefix = 'New Yorker'

    def guess_url_from_date(self):
        url_format = self.dt.strftime('%Y/%m/%d')
        guessed_url = urllib.parse.urljoin(
                'https://www.newyorker.com/puzzles-and-games-dept/crossword/',
                url_format)
        self.find_solver(url=guessed_url)

    def find_latest(self):
        index_url = "https://www.newyorker.com/puzzles-and-games-dept/crossword"
        index_res = requests.get(index_url)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_fragment = next(a for a in index_soup.findAll('a') if a.find('h4'))['href']
        latest_absolute = urllib.parse.urljoin('https://www.newyorker.com',
                                                latest_fragment)

        self.landing_page_url = latest_absolute

        self.find_solver(self.landing_page_url)

    def find_solver(self, url):
        res = requests.get(url)

        if res.status_code == 404:
            sys.exit('Unable to find a puzzle at {}'.format(url))
 
        soup = BeautifulSoup(res.text, "html.parser")

        iframe_url = soup.find('iframe', attrs={'id':'crossword'})['data-src']

        query = urllib.parse.urlparse(iframe_url).query
        query_id = urllib.parse.parse_qs(query)['id']
        self.id = query_id[0]

        pubdate = soup.find('time').get_text()
        pubdate_dt = dateparser.parse(pubdate)

        self.date = pubdate_dt.strftime('%Y%m%d')

        self.find_puzzle_url_from_id()

    def pick_filename(self):
        self.output =  " - ".join([self.outlet_prefix, self.date]) + '.puz'


class WSJDownloader(BaseDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

        self.outlet_prefix = 'WSJ'
        self.headers = {'User-Agent':'xword-dl'}

    def guess_url_from_date(self):
        pass

    def find_latest(self):
        url = "https://blogs.wsj.com/puzzle/category/crossword/"
        res = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        latest_url = soup.find('h4',
                attrs={'class':'headline'}).find('a').get('href', None)

        self.find_solver(url=latest_url)

    def find_solver(self, url):
        if '/puzzle/crossword/' in url:
            self.url = url
        else:
            res = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            puzzle_link = 'https:' + soup.find('a',
                    attrs={'class':'puzzle-link'}).get('href')
            self.find_solver(puzzle_link)

    def download(self):
        self.url = self.url.replace('index.html', 'data.json')
        json_data = requests.get(self.url, headers=self.headers).json()['data']
        xword_metadata = json_data.get('copy', '')
        xword_data = json_data.get('grid','')

        self.date = xword_metadata.get('date-publish-analytics').split()[0].replace('/','')

        fetched = {}
        for field in ['title', 'byline', 'publisher']:
            fetched[field] = html2text(xword_metadata.get(field, ''), bodywidth=0).strip()

        self.puzfile.title = fetched.get('title')
        self.puzfile.author = fetched.get('byline')
        self.puzfile.copyright = fetched.get('publisher')
        self.puzfile.width = int(xword_metadata.get('gridsize').get('cols'))
        self.puzfile.height = int(xword_metadata.get('gridsize').get('rows'))


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
                                           and cell['style']['shapebg'] == 'circle') \
                                       else b'\x00')

        self.puzfile.fill = fill
        self.puzfile.solution = solution

        clue_list = xword_metadata['clues'][0]['clues'] + xword_metadata['clues'][1]['clues']
        sorted_clue_list = sorted(clue_list, key=lambda x: int(x['number']))

        clues = [clue['clue'] for clue in sorted_clue_list]
        normalized_clues = [html2text(unidecode(clue), bodywidth=0) for clue in clues]

        self.puzfile.clues = normalized_clues

        has_markup = b'\x80' in markup

        if has_markup:
            self.puzfile.extensions[b'GEXT'] = markup
            self.puzfile._extensions_order.append(b'GEXT')
            self.puzfile.markup()


class USATodayDownloader(BaseDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output)

        self.outlet_prefix = 'USA Today'

    def guess_url_from_date(self):
        hardcoded_blob = 'https://gamedata.services.amuniversal.com/c/uupuz/l/U2FsdGVkX18CR3EauHsCV8JgqcLh1ptpjBeQ%2Bnjkzhu8zNO00WYK6b%2BaiZHnKcAD%0A9vwtmWJp2uHE9XU1bRw2gA%3D%3D/g/usaon/d/'

        url_format = self.dt.strftime('%Y-%m-%d')
        self.url = hardcoded_blob + url_format + '/data.json'

    def find_latest(self):
        self.find_by_date('today')

    def find_solver(self):
        pass

    def download(self):
        attempts = 3
        while attempts:
            try:
                res = requests.get(self.url)
                xword_data = res.json()
                break
            except json.JSONDecodeError:
                print('Failed to download puzzle. Trying again.')
                attempts -= 1
                time.sleep(1)
        else:
            print('Failed to download puzzle.')

        self.puzfile.title = xword_data.get('Title', '')
        self.puzfile.author = ''.join([xword_data.get('Author', ''),
                                       ' / Ed. ',
                                       xword_data.get('Editor', '')])
        self.puzfile.copyright = xword_data.get('Copyright', '')
        self.puzfile.width = int(xword_data.get('Width'))
        self.puzfile.height = int(xword_data.get('Height'))

        solution = xword_data.get('AllAnswer').replace('-','.')

        self.puzfile.solution = solution

        fill = ''
        for letter in solution:
            if letter == '.':
                fill += '.'
            else:
                fill += '-'
        self.puzfile.fill = fill

        across_clues = xword_data['AcrossClue'].splitlines()
        down_clues = xword_data['DownClue'].splitlines()[:-1]

        clues_list = across_clues + down_clues

        clues_list_stripped = [{'number':clue.split('|')[0],
                                'clue':clue.split('|')[1]} for clue in clues_list]

        clues_sorted = sorted(clues_list_stripped, key=lambda x: x['number'])

        clues = [clue['clue'] for clue in clues_sorted]

        self.puzfile.clues = clues


def main():
    parser = argparse.ArgumentParser(prog='xword-dl', description="""
        xword-dl is a tool to download online crossword puzzles and save them
        locally as .puz files. It only works with supported sites, a list of which
        is found below.
        """)
    parser.set_defaults(downloader_class=None)

    fullpath = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(fullpath, 'version')) as f:
        version = f.read().strip()

    parser.add_argument('-v', '--version', action='version', version=version)

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

    newyorker_parser = subparsers.add_parser('tny',
                            aliases=['newyorker', 'nyer'],
                            parents=[latest_parent,
                                     date_parent,
                                     url_parent,
                                     extractor_parent],
                            help="download a New Yorker puzzle")
    newyorker_parser.set_defaults(downloader_class=NewYorkerDownloader)

    newsday_parser = subparsers.add_parser('nd',
                            aliases=['newsday'],
                            parents=[latest_parent,
                                     date_parent,
                                     extractor_parent],
                            help="download a Newsday puzzle")
    newsday_parser.set_defaults(downloader_class=NewsdayDownloader)

    wsj_parser = subparsers.add_parser('wsj',
                            aliases=['wallstreet'],
                            parents=[latest_parent,
                                     url_parent,
                                     extractor_parent],
                            help="download a Wall Street Journal puzzle")
    wsj_parser.set_defaults(downloader_class=WSJDownloader)

    lat_parser = subparsers.add_parser('lat',
                            aliases=['latimes'],
                            parents=[latest_parent,
                                     date_parent,
                                     extractor_parent],
                            help="download an LA Times Puzzle")
    lat_parser.set_defaults(downloader_class=LATimesDownloader)

    wapo_parser = subparsers.add_parser('wapo',
                            aliases=['wp'],
                            parents=[latest_parent,
                                      date_parent,
                                      extractor_parent],
                            help="download a Washington Post Sunday puzzle")
    wapo_parser.set_defaults(downloader_class=WaPoDownloader)

    usatoday_parser = subparsers.add_parser('usa',
                            aliases=[],
                            parents=[latest_parent,
                                      date_parent,
                                      extractor_parent],
                            help="download a USA Today puzzle")
    usatoday_parser.set_defaults(downloader_class=USATodayDownloader)

    atlantic_parser = subparsers.add_parser('atl',
                            aliases=['atlantic'],
                            parents=[latest_parent,
                                      date_parent,
                                      extractor_parent],
                            help="download an Atlantic puzzle")
    atlantic_parser.set_defaults(downloader_class=AtlanticDownloader)

    args = parser.parse_args()

    if not args.downloader_class:
        sys.exit(parser.print_help())

    dl = args.downloader_class(output=args.output)

    if args.date:
        entered_date = ' '.join(args.date)
        dl.find_by_date(entered_date)

    elif args.spec_url:
        dl.find_solver(args.spec_url)

    elif args.latest:
        dl.find_latest()

    dl.download()
    dl.save_puz()


if __name__ == '__main__':
    main()
