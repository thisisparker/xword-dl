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

from datetime import datetime

from bs4 import BeautifulSoup
from html2text import html2text
from unidecode import unidecode

DIRNAME = os.path.dirname(os.path.realpath(__file__))

def get_amuse_puzzle(url, output):
    # AmuseLabs has misconfigured its SSL and doesn't provide a complete
    # certificate chain. So this is the full chain with root and intermediates,
    # sourced from:
    # https://ssl.comodo.com/support/which-is-root-which-is-intermediate.php and
    # https://support.comodo.com/index.php?/comodo/Knowledgebase/Article/View/979/108/domain-validation-sha-2
    cert_bundle = os.path.join(DIRNAME, 'certs',
                    'comodo-rsa-domain-validation-sha-2-w-root.ca-bundle')

    res= requests.get(url, verify=cert_bundle)

    rawc = next((line.strip() for line in res.text.splitlines()
                    if 'window.rawc' in line), None)

    if not rawc:
        sys.exit("Crossword puzzle not found.")

    rawc = rawc.lstrip("window.rawc = '")
    rawc = rawc.rstrip("';")
    
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

    print("Puzzle downloaded and saved as {}.".format(output))


def get_newyorker_puzzle(url, output):
    puzzle_res = requests.get(url)

    if puzzle_res.status_code == 404:
        sys.exit('Unable to find a puzzle at {}'.format(url))
 
    puzzle_soup = BeautifulSoup(puzzle_res.text, "html.parser")

    amuse_url = puzzle_soup.find('iframe', attrs={'id':'crossword'})['data-src']

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

    latest_fragment = next(a for a in index_soup.findAll('a') if a.find('h4'))['href']

    latest_absolute = urllib.parse.urljoin('https://www.newyorker.com',
                                            latest_fragment)

    get_newyorker_puzzle(url=latest_absolute, output=output)

def get_newsday_puzzle(url, output=None):
    if not output.endswith('.puz'):
        output = ''.join([output, '.puz'])

    get_amuse_puzzle(url=url, output=output)

def get_latest_newsday_puzzle(output=None):
    datepicker_url = "https://cdn2.amuselabs.com/pmm/date-picker?set=creatorsweb"
    res = requests.get(datepicker_url)
    soup = BeautifulSoup(res.text, 'html.parser')

    data_id = soup.find('li', attrs={'class':'tile'})['data-id']

    if not output:
        output = 'nd' + data_id.split('_')[-1] + '.puz'

    url = "https://cdn2.amuselabs.com/pmm/crossword?id={}&set=creatorsweb".format(data_id)

    get_newsday_puzzle(url=url, output=output)


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
    date_selector.add_argument('-d', '--date', nargs='*',
                            help='a specific puzzle date to select')

    extractor_parent.add_argument('-o', '--output',
                            help="""
                            the filename for the saved puzzle
                            (if not provided, a default value will be used)""",
                            default=None)

    extractor_url_parent = argparse.ArgumentParser(add_help=False)
    extractor_url_parent.add_argument('-u', '--url',
                            help='a specific puzzle URL to download')

    subparsers = parser.add_subparsers(title='sites',
                            description='Supported puzzle sources',
                            dest='subparser_name')

    newyorker_parser = subparsers.add_parser('tny',
                            aliases=['newyorker', 'nyer'],
                            parents=[extractor_parent,
                                     extractor_url_parent],
                            help="download a New Yorker puzzle")

    newsday_puzzle = subparsers.add_parser('nd',
                            aliases=['newsday'],
                            parents=[extractor_parent],
                            help="download a Newsday puzzle")

    parser.add_argument('--url', help='URL of puzzle to download')

    args = parser.parse_args()

    guessed_date = ''

    if args.date:
        entered_date = ' '.join(args.date)
        guessed_date = dateparser.parse(entered_date)
        if guessed_date:
            human_format = guessed_date.strftime('%a, %b %d')
        else:
            sys.exit('Unable to determine a date from "{}".'.format(entered_date))

    if args.subparser_name == 'tny':
        if guessed_date:
            print("Attempting to download a puzzle for {}.".format(human_format))
            url_format = guessed_date.strftime('%Y/%m/%d')
            guessed_url = urllib.parse.urljoin(
                   'https://www.newyorker.com/crossword/puzzles-dept/',
                   url_format)
            get_newyorker_puzzle(url=guessed_url, output=args.output)
                
        elif args.url:
            get_newyorker_puzzle(url=args.url, output=args.output)
        elif args.latest:
            get_latest_newyorker_puzzle(output=args.output)

    elif args.subparser_name == 'nd':
        if guessed_date:
            print("Attempting to download a puzzle for {}.".format(human_format))
            url_format = guessed_date.strftime('%Y%m%d')
            guessed_url = ''.join([
                'https://cdn2.amuselabs.com/pmm/crossword?id=Creators_WEB_',
                url_format, '&set=creatorsweb'])
            output = args.output if args.output else ''.join(
                ['nd', url_format, '.puz'])
            get_newsday_puzzle(url=guessed_url, output=output)
        elif args.latest:
            get_latest_newsday_puzzle(args.output)

if __name__ == '__main__':
    main()
