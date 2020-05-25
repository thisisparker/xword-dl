#!/usr/bin/env python3

import argparse
import base64
import json
import os
import sys
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
        self.pick_filename()
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

        box = xword_data['box']
        for row_num in range(xword_data.get('h')):
            for col_num, column in enumerate(box):
                cell = column[row_num]
                if cell == '\x00':
                    solution += '.'
                    fill += '.'
                    markup += b'\x00'
                else:
                    solution += cell
                    fill += '-'
                    markup += b'\x80' if (col_num, row_num) in circled else b'\x00'

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

        if has_markup:
            self.puzfile.extensions[b'GEXT'] = markup
            self.puzfile._extensions_order.append(b'GEXT')
            self.puzfile.markup()

        self.save_puz()

    def save_puz(self):
        if not self.date:
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


class NewYorkerDownloader(AmuseLabsDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

        self.outlet_prefix = 'New Yorker'

    def guess_url_from_date(self, dt):
        url_format = dt.strftime('%Y/%m/%d')
        guessed_url = urllib.parse.urljoin(
                'https://www.newyorker.com/crossword/puzzles-dept/',
                url_format)
        self.find_solver(url=guessed_url)

    def find_latest(self):
        index_url = "https://www.newyorker.com/crossword/puzzles-dept"
        index_res = requests.get(index_url)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_fragment = next(a for a in index_soup.findAll('a') if a.find('h4'))['href']
        latest_absolute = urllib.parse.urljoin('https://www.newyorker.com',
                                                latest_fragment)

        self.find_solver(url=latest_absolute)

    def find_solver(self, url):
        res = requests.get(url)

        if res.status_code == 404:
            sys.exit('Unable to find a puzzle at {}'.format(url))
 
        soup = BeautifulSoup(res.text, "html.parser")

        self.url = soup.find('iframe', attrs={'id':'crossword'})['data-src']

        if not self.output:
            path = urllib.parse.urlsplit(url).path
            date_frags = path.split('/')[-3:]
            date_mash = ''.join(date_frags)
            self.output = ''.join(['tny', date_mash, '.puz'])


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


class WSJDownloader(BaseDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

    def guess_url_from_date(self, dt):
        pass

    def find_latest(self):
        url = "https://blogs.wsj.com/puzzle/category/crossword/"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
        latest_url = soup.find('h4',
                attrs={'class':'headline'}).find('a').get('href', None)

        self.find_solver(url=latest_url)

    def find_solver(self, url):
        if '/puzzle/crossword/' in url:
            self.url = url
        else:
            res = requests.get(url)
            soup = BeautifulSoup(res.text, 'html.parser')
            puzzle_link = 'https:' + soup.find('a',
                    attrs={'class':'puzzle-link'}).get('href')
            self.url = puzzle_link

    def download(self):
        self.url = self.url.replace('index.html', 'data.json')
        xword_data = requests.get(self.url).json()['data']['copy']

        date = xword_data.get('date-publish-analytics').split()[0].replace('/','')

        if not self.output:
            self.output = 'wsj' + date + '.puz'

        self.puzfile.title = xword_data.get('title', '')
        self.puzfile.author = xword_data.get('byline', '')
        self.puzfile.copyright = xword_data.get('publisher', '')
        self.puzfile.width = int(xword_data.get('gridsize').get('cols'))
        self.puzfile.height = int(xword_data.get('gridsize').get('rows'))

        solution = xword_data.get('settings').get('solution').replace(' ', '.')
        self.puzfile.solution = solution

        fill = ''
        for letter in solution:
            if letter == '.':
                fill += '.'
            else:
                fill += '-'
        self.puzfile.fill = fill

        clue_list = xword_data['clues'][0]['clues'] + xword_data['clues'][1]['clues']
        sorted_clue_list = sorted(clue_list, key=lambda x: int(x['number']))

        clues = [clue['clue'] for clue in sorted_clue_list]
        normalized_clues = [html2text(unidecode(clue), bodywidth=0) for clue in clues]

        self.puzfile.clues = normalized_clues

        self.save_puz()


class LATimesDownloader(BaseDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output)

    def guess_url_from_date(self, dt):
        url_format = dt.strftime('%y%m%d')
        self.url = 'http://ams.cdn.arkadiumhosted.com/assets/gamesfeed/latimescrosswords/DailyCrossword/la' + url_format + '.xml'

        output_format = dt.strftime('%Y%m%d')
        self.output = 'lat' + output_format + '.puz'

    def find_latest(self):
        self.find_by_date('today')

    def find_solver(self, url):
        pass

    def download(self):
        res = requests.get(self.url)

        data = xmltodict.parse(res.text)['crossword-compiler']['rectangular-puzzle']

        metadata = data['metadata']

        self.puzfile.title = metadata.get('title','')
        self.puzfile.author = metadata.get('creator','')
        self.puzfile.copyright = metadata.get('copyright','')

        xw_data = data['crossword']

        self.puzfile.width = int(xw_data.get('grid').get('@width'))
        self.puzfile.height = int(xw_data.get('grid').get('@height'))

        solution = ''
        fill = ''
        markup = b''

        cells = xw_data['grid']['cell']
        cells = [{'x':int(cell['@x']),
                  'y':int(cell['@y']),
                  'solution':cell.get('@solution', '.'),
                  'markup':cell.get('@background-shape', '.')} for cell in cells]

        sorted_cells = sorted(cells, key=lambda x: (x['y'], x['x']))

        for cell in sorted_cells:
            if cell['solution'] == '.':
                solution += '.'
                fill += '.'
                markup += b'\x00'
            else:
                solution += cell['solution']
                fill += '-'
                markup += b'\x80' if cell['markup'] == 'circle' else b'\x00'

        self.puzfile.solution = solution
        self.puzfile.fill = fill

        has_markup = b'\x80' in markup
        if has_markup:
            self.puzfile.extensions[b'GEXT'] = markup
            self.puzfile._extensions_order.append(b'GEXT')
            self.puzfile.markup() 

        across_clues = xw_data['clues'][0]['clue']
        down_clues = xw_data['clues'][1]['clue']

        clues_list = across_clues + down_clues
        clues_list_stripped = [{'number':int(clue['@number']),
                                'clue':clue['#text']} for clue in clues_list]

        clues_sorted = sorted(clues_list_stripped, key=lambda x: x['number'])

        clues = [clue['clue'] for clue in clues_sorted]

        self.puzfile.clues = clues

        self.save_puz()


class USATodayDownloader(BaseDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output)

    def guess_url_from_date(self, dt):
        hardcoded_blob = 'https://gamedata.services.amuniversal.com/c/uupuz/l/U2FsdGVkX18CR3EauHsCV8JgqcLh1ptpjBeQ%2Bnjkzhu8zNO00WYK6b%2BaiZHnKcAD%0A9vwtmWJp2uHE9XU1bRw2gA%3D%3D/g/usaon/d/'

        url_format = dt.strftime('%Y-%m-%d')
        self.url = hardcoded_blob + url_format + '/data.json'

        output_format = dt.strftime('%Y%m%d')
        self.output = 'usatoday' + output_format + '.puz'

    def find_latest(self):
        self.find_by_date('today')

    def find_solver(self):
        pass

    def download(self):
        res = requests.get(self.url)

        xword_data = res.json()

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

        self.save_puz()

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('url', nargs="?",
                            help='URL of puzzle to download')

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

    dl = args.downloader_class(output=args.output)

    if args.date:
        entered_date = ' '.join(args.date)
        dl.find_by_date(entered_date)

    elif args.spec_url:
        dl.find_solver(args.spec_url)

    elif args.latest:
        dl.find_latest()

    dl.download()


if __name__ == '__main__':
    main()
