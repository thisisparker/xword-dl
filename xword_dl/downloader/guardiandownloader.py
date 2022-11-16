import datetime
import json

import puz
import requests

from bs4 import BeautifulSoup

from .basedownloader import BaseDownloader
from ..util import unidecode, XWordDLException

class GuardianDownloader(BaseDownloader):
    outlet = 'Guardian'
    outlet_prefix = 'Guardian'

    def __init__(self, **kwargs):
        super().__init__(inherit_settings='guardian', **kwargs)

        self.landing_page = 'https://www.theguardian.com/crosswords'

    def find_latest(self):
        res = requests.get(self.landing_page)
        soup = BeautifulSoup(res.text, 'html.parser')

        url = soup.find('a', attrs={'data-link-name': 'article'}).get('href')

        return url

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url):
        res = requests.get(solver_url)
        soup = BeautifulSoup(res.text, 'html.parser')

        xw_data = json.loads(soup.find('div', 
                    attrs={'class':'js-crossword'}).get('data-crossword-data'))

        return xw_data

    def parse_xword(self, xword_data):
        puzzle = puz.Puzzle()

        puzzle.author = unidecode(xword_data.get('creator',{}).get('name',''))
        puzzle.height = xword_data.get('dimensions').get('rows')
        puzzle.width  = xword_data.get('dimensions').get('cols')

        puzzle.title = unidecode(xword_data.get('name', ''))

        if not xword_data.get('solutionAvailable'):
            puzzle.title += ' - no solution provided'

        self.date = datetime.datetime.fromtimestamp(
                                        xword_data.get('date') // 1000)

        grid_dict = {}

        for e in xword_data.get('entries'):
            pos = (e.get('position').get('x'), e.get('position').get('y'))
            for index in range(e.get('length')):
                grid_dict[pos] = e.get('solution', 'X' * e.get('length'))[index]
                pos = ((pos[0] + 1, pos[1]) if e.get('direction') == 'across'
                        else (pos[0], pos[1] + 1))

        solution = ''
        fill = ''

        for y in range(puzzle.height):
            for x in range(puzzle.width):
                sol_at_space = grid_dict.get((x,y), '.')
                solution += sol_at_space
                fill += '.' if sol_at_space == '.' else '-'

        puzzle.solution = solution
        puzzle.fill = fill

        clues = [unidecode(e.get('clue')) for e in
                    sorted(xword_data.get('entries'), 
                    key=lambda x: (x.get('number'), x.get('direction')))]

        puzzle.clues = clues

        return puzzle


class GuardianCrypticDownloader(GuardianDownloader):
    command = 'grdc'
    outlet = 'Guardian Cryptic'
    outlet_prefix = 'Guardian Cryptic'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.landing_page += '/series/cryptic'


class GuardianEverymanDownloader(GuardianDownloader):
    command = 'grde'
    outlet = 'Guardian Everyman'
    outlet_prefix = 'Guardian Everyman'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.landing_page += '/series/everyman'


class GuardianSpeedyDownloader(GuardianDownloader):
    command = 'grds'
    outlet = 'Guardian Speedy'
    outlet_prefix = 'Guardian Speedy'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.landing_page += '/series/speedy'


class GuardianQuickDownloader(GuardianDownloader):
    command = 'grdq'
    outlet = 'Guardian Quick'
    outlet_prefix = 'Guardian Quick'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.landing_page += '/series/quick'


class GuardianPrizeDownloader(GuardianDownloader):
    command = 'grdp'
    outlet = 'Guardian Prize'
    outlet_prefix = 'Guardian Prize'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.landing_page += '/series/prize'


class GuardianWeekendDownloader(GuardianDownloader):
    command = 'grdw'
    outlet = 'Guardian Weekend Crossword'
    outlet_prefix = 'Guardian Weekend'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.landing_page += '/series/weekend-crossword'


class GuardianQuipticDownloader(GuardianDownloader):
    command = 'grdu'
    outlet = 'Guardian Quiptic'
    outlet_prefix = 'Guardian Quiptic'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.landing_page += '/series/quiptic'
