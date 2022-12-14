import datetime
import json

import requests

from bs4 import BeautifulSoup

from .compilerdownloader import CrosswordCompilerDownloader

class TheModernDownloader(CrosswordCompilerDownloader):
    command = 'mod'
    outlet = 'The Modern'
    outlet_prefix = 'The Modern'

    def init(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def matches_url(url_components):
        return 'puzzlesociety.com' in url_components.netloc and 'modern-crossword' in url_components.path

    def find_latest(self):
        return 'https://www.puzzlesociety.com/crossword-puzzles/modern-crossword'

    def find_solver(self, url):
        res = requests.get(url)

        soup = BeautifulSoup(res.text, 'lxml')
        page_props = json.loads(soup.find('script',
                                {'type':'application/json'}).get_text())

        sets = page_props['props']['pageProps']\
                            ['gameContent']['gameLevelDataSets']

        self.date = datetime.datetime.strptime(sets[0]['issueDate'], '%Y-%m-%d')
        url = sets[0]['files'][0]['url']

        return url

    def parse_xword(self, xword_data):
        puzzle = super().parse_xword(xword_data)

        if not puzzle.author:
            puzzle.author = puzzle.title[3:]
            puzzle.title = self.date.strftime('%A, %B %d, %Y')

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        if puzzle.title == self.date.strftime('%A, %B %d, %Y'):
            title = ''
        else:
            title = puzzle.title

        return super().pick_filename(puzzle, title=title, **kwargs)
