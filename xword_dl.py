#!/usr/bin/env python3

import argparse
import base64
import json
import puz
import requests

from html2text import html2text
from unidecode import unidecode

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='URL of puzzle to download')
    args = parser.parse_args()
    url = args.url

    res = requests.get(url, verify=False)

    rawc = next((line.strip() for line in res.text.splitlines()
                    if 'window.rawc' in line), None)

    rawc = rawc.lstrip("window.rawc = '")
    rawc = rawc.rstrip("';")

    if not rawc:
        sys.exit("crossword puzzle data not found")
    
    xword_data = json.loads(base64.b64decode(rawc))

    p = puz.Puzzle()

    p.title = xword_data.get('title', '')
    p.author = xword_data.get('author', '')
    p.copyright = xword_data.get('copyright', '')
    p.width = xword_data.get('w')
    p.height = xword_data.get('h')

    solution = ''
    fill = ''
    box = xword_data['box']
    for row_num in range(xword_data.get('h')):
        for column in box:
            cell = column[row_num]
            if cell == '\x00':
                solution += '.'
                fill += '.' 
            else:
                solution += cell
                fill += '-'
    p.solution = solution
    p.fill = fill

    placed_words = xword_data['placedWords']
    across_words = [word for word in placed_words if word['acrossNotDown']]
    down_words = [word for word in placed_words if not word['acrossNotDown']]

    weirdass_puz_clue_sorting = sorted(placed_words, key=
                                            lambda word: (word['y'], word['x'],
                                            not word['acrossNotDown']))

    clues = [word['clue']['clue'] for word in weirdass_puz_clue_sorting]


    normalized_clues = [html2text(unidecode(clue), bodywidth=0) for clue in clues]

    p.clues.extend(normalized_clues)

    filename = input("And what shall we call it? ")
    
    if not filename:
        filename = 'output.puz'
    elif filename[-4:] != '.puz':
        filename += '.puz'

    p.save(filename)


if __name__ == '__main__':
    main()
