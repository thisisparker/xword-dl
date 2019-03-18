#!/usr/bin/env python3

import argparse
import base64
import json
import puz
import requests
import urllib

from bs4 import BeautifulSoup

from html2text import html2text
from unidecode import unidecode

def get_amuse_puzzle(url, output):
    res = requests.get(url)

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

    p.save(output)

    print("Puzzle downloaded and saved as {}".format(output))


def get_newyorker_puzzle(url, output):
    puzzle_res = requests.get(url)
    puzzle_soup = BeautifulSoup(puzzle_res.text, "html.parser")

    amuse_url = puzzle_soup.findAll('iframe', attrs={'id':'crossword'})[0]['data-src']

    if output:
        output = output if output.endswith('.puz') else ''.join([output, '.puz'])
    else:
        path = urllib.parse.urlsplit(url).path
        date_frags = path.split('/')[-3:]
        date_mash = ''.join(date_frags)
        output = ''.join(['tny', date_mash, '.puz'])

    get_amuse_puzzle(amuse_url, output)

def get_latest_newyorker_puzzle(output=None):
    index_url = "https://www.newyorker.com/crossword/puzzles-dept"
    index_res = requests.get(index_url)

    index_soup = BeautifulSoup(index_res.text, "html.parser")

    latest_fragment = [a for a in index_soup.findAll('a') if a.find('h4')][0]['href']

    latest_absolute = urllib.parse.urljoin('https://www.newyorker.com',
                                            latest_fragment)

    get_newyorker_puzzle(url=latest_absolute, output=output)


def main():
    
    parser = argparse.ArgumentParser()

    extractor_parent = argparse.ArgumentParser(add_help=False)
    date_selector = extractor_parent.add_mutually_exclusive_group()
    date_selector.add_argument('-l', '--latest',
                            help="""
                                select most recent available puzzle
                                (this is the default behavior)""",
                            action='store_true',
                            default=True)
    date_selector.add_argument('-d', '--date',
                            help='a specific puzzle date to select')
    date_selector.add_argument('-u', '--url',
                            help='a specific puzzle URL to downlod')
    extractor_parent.add_argument('-o', '--output',
                            help="""
                            the filename for the saved puzzle
                            (if not provided, a default value will be used)""",
                            default=None)

    subparsers = parser.add_subparsers(title='sites',
                            description='supported puzzle sources',
                            dest='subparser_name')

    newyorker_parser = subparsers.add_parser('tny',
                            aliases=['newyorker', 'nyer'],
                            parents=[extractor_parent],
                            help="download a New Yorker puzzle")

    # parser.add_argument('--url', help='URL of puzzle to download')

    args = parser.parse_args()

    if args.subparser_name == 'tny':
        if args.date or args.url:
            print("haven't yet implemented specific puzzle selection")
        elif args.latest:
            get_latest_newyorker_puzzle(output=args.output)

if __name__ == '__main__':
    main()
