import puz
import requests
import xmltodict

from .basedownloader import BaseDownloader
from ..util import unidecode

class CrosswordCompilerDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.date = None

    def find_solver(self, url):
        return url

    def fetch_jsencoded_data(self, url):
        res = requests.get(url, headers={'User-Agent': 'xword-dl'})
        xw_data = res.text[len('var CrosswordPuzzleData = "'):-len('";')]
        xw_data = xw_data.replace('\\','')

        return xw_data

    def fetch_data(self, url, js_encoded=False):
        if js_encoded:
            return fetch_jsencoded_data(url)

        res = requests.get(url, headers={'User-Agent': 'xword-dl'})
        xw_data = res.text

        return xw_data

    def parse_xword(self, xword_data, enumeration=True):
        xw = xmltodict.parse(xword_data)
        xw_root = xw.get('crossword-compiler') or xw.get('crossword-compiler-applet')
        xw_puzzle = xw_root['rectangular-puzzle']
        xw_metadata = xw_puzzle['metadata']
        xw_grid = xw_puzzle['crossword']['grid']

        puzzle = puz.Puzzle()

        puzzle.title = unidecode(xw_metadata.get('title') or '')
        puzzle.author = unidecode(xw_metadata.get('creator') or '')
        puzzle.copyright = unidecode(xw_metadata.get('copyright') or '')

        puzzle.width = int(xw_grid.get('@width'))
        puzzle.height = int(xw_grid.get('@height'))

        solution = ''
        fill = ''
        markup = b''

        cells = {(int(cell.get('@x')), int(cell.get('@y'))): cell for cell in xw_grid.get('cell')}

        for y in range(1, puzzle.height + 1):
            for x in range(1, puzzle.width + 1):
                cell = cells.get((x, y))
                solution += cell.get('@solution', '.')
                fill += '.' if cell.get('@type') == 'block' else '-'
                markup += (b'\x80' if (cell.get('@background-shape') == 'circle') else b'\x00')

        puzzle.solution = solution
        puzzle.fill = fill

        xw_clues = xw_puzzle['crossword']['clues']

        all_clues = xw_clues[0]['clue'] + xw_clues[1]['clue']

        clues = [unidecode(c.get('#text')) + (f' ({c.get("@format", "")})'
                    if c.get("@format") and enumeration else '') for c in
                    sorted(all_clues, key=lambda x: int(x.get('@number')))]

        puzzle.clues = clues

        has_markup = b'\x80' in markup

        if has_markup:
            puzzle.extensions[b'GEXT'] = markup
            puzzle._extensions_order.append(b'GEXT')
            puzzle.markup()

        return puzzle
