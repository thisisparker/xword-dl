import datetime
import json
import urllib

import requests

from bs4 import BeautifulSoup

from .compilerdownloader import CrosswordCompilerDownloader

class TheModernDownloader(CrosswordCompilerDownloader):
    command = 'mod'
    outlet = 'The Modern'
    outlet_prefix = 'The Modern'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def matches_url(url_components):
        return 'puzzlesociety.com' in url_components.netloc and 'modern-crossword' in url_components.path
        
    def find_by_date(self, dt):
        url_format = dt.strftime('%Y/%m/%d')
        guessed_url = urllib.parse.urljoin(
            'https://www.puzzlesociety.com/crossword-puzzles/modern-crossword/',
            url_format)
        return guessed_url

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

    def fetch_data(self, url):
        res = requests.get(url)
        xw_data = res.content.decode('utf-8-sig')

        return xw_data

    def parse_xword(self, xword_data):
        puzzle = super().parse_xword(xword_data, enumeration=False)

        if not puzzle.author:
            puzzle.author = puzzle.title[3:]
            puzzle.title = self.date.strftime('%A, %B %d, %Y')

        across = [dict({'dir':'A'}, **c) for c in puzzle.clue_numbering().across]
        down =   [dict({'dir':'D'}, **c) for c in puzzle.clue_numbering().down]
        all_clues_numbered = sorted(across + down, key=lambda x: x['num'])
        constructor_notes = []
        alternate_clues   = []
        for i in range(len(puzzle.clues)):
            clue_dict = all_clues_numbered.pop(0)
            clue_id = str(clue_dict['num']) + clue_dict['dir'] + ': '
            puzzle.clues[i] = urllib.parse.unquote(puzzle.clues[i])
            if '@@' in puzzle.clues[i]:
                clue, note = puzzle.clues[i].split('@@')
                constructor_notes.append(clue_id + note.strip())
                puzzle.clues[i] = clue.strip()
            if '||' in puzzle.clues[i]:
                clue, alt = puzzle.clues[i].split('||')
                alternate_clues.append(clue_id + alt.strip())
                puzzle.clues[i] = clue.strip()

        if alternate_clues:
            puzzle.notes += 'ALTERNATE CLUES:\n'
            for c in alternate_clues:
                puzzle.notes += c + '\n'
        if constructor_notes:
            puzzle.notes += 'CONSTRUCTOR NOTES:\n'
            for n in constructor_notes:
                puzzle.notes += n + '\n'

        puzzle.notes.rstrip('\n')

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        if puzzle.title == self.date.strftime('%A, %B %d, %Y'):
            title = ''
        else:
            title = puzzle.title

        return super().pick_filename(puzzle, title=title, **kwargs)
