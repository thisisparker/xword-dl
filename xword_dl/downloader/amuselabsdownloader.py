import base64
import datetime
import json
import urllib

import puz
import requests

import re

from bs4 import BeautifulSoup
from html2text import html2text

import js2py

from .basedownloader import BaseDownloader
from ..util import *

class AmuseLabsDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.id = None

    @staticmethod
    def matches_url(url_components):
        return 'amuselabs.com' in url_components.netloc

    def find_latest(self):
        res = requests.get(self.picker_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        puzzles = soup.find('div', attrs={'class': 'puzzles'})
        puzzle_ids = puzzles.findAll('div', attrs={'class': 'tile'})
        if not puzzle_ids:
            puzzle_ids = puzzles.findAll('li', attrs={'class': 'tile'})
        self.id = puzzle_ids[0].get('data-id', '')

        self.get_and_add_picker_token(res.text)

        return self.find_puzzle_url_from_id(self.id)

    def get_and_add_picker_token(self, picker_source=None):
        if not picker_source:
            res = requests.get(self.picker_url)
            picker_source = res.text

        rawsps = next((line.strip() for line in picker_source.splitlines()
                     if 'pickerParams.rawsps' in line), None)

        if rawsps:
            rawsps = rawsps.split("'")[1]
            picker_params = json.loads(base64.b64decode(rawsps).decode("utf-8"))
            token = picker_params.get('pickerToken', None)
            if token:
                self.url_from_id += '&pickerToken=' + token

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
                     if ('window.rawc' in line
                        or 'window.puzzleEnv.rawc' in line)), None)

        if not rawc:
            raise XWordDLException("Crossword puzzle not found.")

        rawc = rawc.split("'")[1]

        ## In some cases we need to pull the underlying JavaScript ##
        # Find the JavaScript URL
        amuseKey = None
        m1 = re.search(r'"([^"]+c-min.js[^"]+)"', res.text)
        js_url_fragment = m1.groups()[0]
        js_url = urllib.parse.urljoin(solver_url, js_url_fragment)

        # get the decryption function from the JS URL
        res2 = requests.get(js_url)
        js_text = res2.text
        re_match = re.search(r'rawc\;try\{(var n=function.*?n.join\(""\)\})', js_text)
        jsFunc = re_match.groups()[0]
        context = js2py.EvalJs()
        context.execute(jsFunc)

        # Execute the function on our rawc
        s1 = context.n(rawc)
        xword_data = json.loads(base64.b64decode(s1).decode("utf-8"))

        return xword_data

    def parse_xword(self, xword_data):
        puzzle = puz.Puzzle()
        puzzle.title = unidecode(xword_data.get('title', '').strip())
        puzzle.author = unidecode(xword_data.get('author', '').strip())
        puzzle.copyright = unidecode(xword_data.get('copyright', '').strip())
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
                    markup += b'\x80' if (col_num,
                                          row_num) in circled else b'\x00'
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
        down_words = [
            word for word in placed_words if not word['acrossNotDown']]

        weirdass_puz_clue_sorting = sorted(placed_words, key=lambda word: (word['y'], word['x'],
                                                                           not word['acrossNotDown']))

        clues = [word['clue']['clue'] for word in weirdass_puz_clue_sorting]

        normalized_clues = [html2text(unidecode(clue), bodywidth=0).strip()
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
