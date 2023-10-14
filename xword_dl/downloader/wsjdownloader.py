import datetime

import puz
import requests

from bs4 import BeautifulSoup
from html2text import html2text

from .basedownloader import BaseDownloader
from ..util import XWordDLException, unidecode

class WSJDownloader(BaseDownloader):
    command = 'wsj'
    outlet = 'Wall Street Journal'
    outlet_prefix = 'WSJ'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.headers = {'User-Agent': 'xword-dl'}

    @staticmethod
    def matches_url(url_components):
        return 'wsj.com' in url_components.netloc

    def find_latest(self):
        url = "https://www.wsj.com/news/puzzle"

        res = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(res.text, 'html.parser')

        exclude_urls = ['https://www.wsj.com/articles/contest-crosswords-101-how-to-solve-puzzles-11625757841']

        for article in soup.find_all('article'):
            if 'crossword' in article.find('span').get_text().lower():
                latest_url = article.find('a').get('href')
                if latest_url not in exclude_urls:
                    break
        else:
            raise XWordDLException('Unable to find latest puzzle.')

        return latest_url

    def find_solver(self, url):
        if '/puzzles/crossword/' in url:
            return url
        else:
            res = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            try:
                puzzle_link = soup.find('iframe').get('src')
            except AttributeError:
                raise XWordDLException('Cannot find puzzle at {}.'.format(url))
            return self.find_solver(puzzle_link)

    def fetch_data(self, solver_url):
        data_url = solver_url.rsplit('/', maxsplit=1)[0] + '/data.json'
        return requests.get(data_url, headers=self.headers).json()['data']

    def parse_xword(self, xword_data):
        xword_metadata = xword_data.get('copy', '')
        xword_data = xword_data.get('grid', '')

        date_string = xword_metadata.get('date-publish-analytics').split()[0]

        self.date = datetime.datetime.strptime(date_string, '%Y/%m/%d')

        fetched = {}
        for field in ['title', 'byline', 'publisher', 'crosswordadditionalcopy']:
            fetched[field] = unidecode(html2text(xword_metadata.get(field) or '',
                                       bodywidth=0)).strip()

        puzzle = puz.Puzzle()
        puzzle.title = fetched.get('title')
        puzzle.author = fetched.get('byline')
        puzzle.copyright = fetched.get('publisher')
        puzzle.width = int(xword_metadata.get('gridsize').get('cols'))
        puzzle.height = int(xword_metadata.get('gridsize').get('rows'))

        puzzle.notes = fetched.get('crosswordadditionalcopy')

        solution = ''
        fill = ''
        markup = b''

        for row in xword_data:
            for cell in row:
                if cell.get('Blank'):
                    fill += '.'
                    solution += '.'
                    markup += b'\x00'
                else:
                    fill += '-'
                    solution += cell['Letter'] or 'X'
                    markup += (b'\x80' if (cell.get('style', '')
                                           and cell['style']['shapebg']
                                           == 'circle')
                               else b'\x00')

        puzzle.fill = fill
        puzzle.solution = solution

        if all(c in ['.', 'X'] for c in puzzle.solution):
            puzzle.solution_state = 0x0002

        clue_list = xword_metadata['clues'][0]['clues'] + \
            xword_metadata['clues'][1]['clues']
        sorted_clue_list = sorted(clue_list, key=lambda x: int(x['number']))

        clues = [clue['clue'] for clue in sorted_clue_list]
        normalized_clues = [
            html2text(unidecode(clue), bodywidth=0).strip() for clue in clues]

        puzzle.clues = normalized_clues

        has_markup = b'\x80' in markup

        if has_markup:
            puzzle.extensions[b'GEXT'] = markup
            puzzle._extensions_order.append(b'GEXT')
            puzzle.markup()

        return puzzle
