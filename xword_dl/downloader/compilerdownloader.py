import puz
import requests
import urllib.parse
import xmltodict
from bs4 import BeautifulSoup

from .basedownloader import BaseDownloader

class CrosswordCompilerDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.date = None

    def find_solver(self, url):
        return url

    @staticmethod
    def _fetch_data(solver_url, js_encoded=False, headers=None):
        headers = headers or {'User-Agent': 'xword-dl'}
        res = requests.get(solver_url, headers=headers)

        if js_encoded:
            xw_data = res.text[len('var CrosswordPuzzleData = "'):-len('";')]
            return xw_data.replace('\\','')

        return res.text

    @staticmethod
    def matches_embed_url(src):
        res = requests.get(src)
        if not res.ok:
            return None
        soup = BeautifulSoup(res.text, 'lxml')

        for script in [s for s in soup.find_all('script') if s.get('src')]:
            js_url = urllib.parse.urljoin(src, script.get('src'))
            res = requests.get(js_url, headers={'User-Agent':'xword-dl'})
            if res.text.startswith('var CrosswordPuzzleData'):
                return js_url

    # subclasses of CCD may want to override this method with different defaults
    def fetch_data(self, solver_url):
        return self._fetch_data(solver_url)

    def parse_xword(self, xw_data, enumeration=True):
        xw = xmltodict.parse(xw_data)
        xw_root = xw.get('crossword-compiler') or xw['crossword-compiler-applet']
        xw_puzzle = xw_root['rectangular-puzzle']
        xw_metadata = xw_puzzle['metadata']
        xw_grid = xw_puzzle['crossword']['grid']

        puzzle = puz.Puzzle()

        puzzle.title = xw_metadata.get('title') or ''
        puzzle.author = xw_metadata.get('creator') or ''
        puzzle.copyright = xw_metadata.get('copyright') or ''

        puzzle.width = int(xw_grid['@width'])
        puzzle.height = int(xw_grid['@height'])

        solution = ''
        fill = ''
        markup = b''

        cells = {(int(cell['@x']), int(cell['@y'])): cell for cell in xw_grid['cell']}

        for y in range(1, puzzle.height + 1):
            for x in range(1, puzzle.width + 1):
                cell = cells[(x, y)]
                solution += cell.get('@solution', '.')
                fill += '.' if cell.get('@type') == 'block' else '-'
                markup += (b'\x80' if (cell.get('@background-shape') == 'circle') else b'\x00')

        puzzle.solution = solution
        puzzle.fill = fill

        xw_clues = xw_puzzle['crossword']['clues']

        all_clues = xw_clues[0]['clue'] + xw_clues[1]['clue']

        clues = [c.get('#text', '') + (f' ({c.get("@format", "")})'
                    if c.get("@format") and enumeration else '') for c in
                    sorted(all_clues, key=lambda x: int(x['@number']))]

        puzzle.clues = clues

        has_markup = b'\x80' in markup

        if has_markup:
            puzzle.extensions[b'GEXT'] = markup
            puzzle._extensions_order.append(b'GEXT')
            puzzle.markup()

        return puzzle
