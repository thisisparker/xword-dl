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

class BaseDownloader:
    def __init__(self, output=None):
        self.output = output
        if self.output and not self.output.endswith('.puz'):
            self.output = self.output + '.puz'
        self.puzfile = puz.Puzzle()

    def find_by_date(self, entered_date):
        guessed_dt = dateparser.parse(entered_date)
        if guessed_dt:
            readable_date = guessed_dt.strftime('%A, %B %d')
            print("Attempting to download a puzzle for {}".format(readable_date))
        else:
            sys.exit('Unable to determine a date from "{}".'.format(entered_date))

        self.guess_url_from_date(guessed_dt)

    def save_puz(self):
        self.puzfile.save(self.output)
        print("Puzzle downloaded and saved as {}.".format(self.output))


class AmuseLabsDownloader(BaseDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output)

    def download(self):
        # AmuseLabs has misconfigured its SSL and doesn't provide a complete
        # certificate chain. So this is the full chain with root and intermediates,
        # sourced from:
        # https://ssl.comodo.com/support/which-is-root-which-is-intermediate.php and
        # https://support.comodo.com/index.php?/comodo/Knowledgebase/Article/View
        # /979/108/domain-validation-sha-2
        cert_bundle = os.path.join(DIRNAME, 'certs',
                        'comodo-rsa-domain-validation-sha-2-w-root.ca-bundle')

        res = requests.get(self.url, verify=cert_bundle)
        rawc = next((line.strip() for line in res.text.splitlines()
                        if 'window.rawc' in line), None)

        if not rawc:
            sys.exit("Crossword puzzle not found.")

        rawc = rawc.split("'")[1]

        xword_data = json.loads(base64.b64decode(rawc).decode("utf-8"))

        self.puzfile.title = xword_data.get('title', '')
        self.puzfile.author = xword_data.get('author', '')
        self.puzfile.copyright = xword_data.get('copyright', '')
        self.puzfile.width = xword_data.get('w')
        self.puzfile.height = xword_data.get('h')

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
        self.puzfile.solution = solution
        self.puzfile.fill = fill

        placed_words = xword_data['placedWords']
        across_words = [word for word in placed_words if word['acrossNotDown']]
        down_words = [word for word in placed_words if not word['acrossNotDown']]

        weirdass_puz_clue_sorting = sorted(placed_words, key=
                                                lambda word: (word['y'], word['x'],
                                                not word['acrossNotDown']))

        clues = [word['clue']['clue'] for word in weirdass_puz_clue_sorting]

        normalized_clues = [html2text(unidecode(clue), bodywidth=0) for clue in clues]
        self.puzfile.clues.extend(normalized_clues)

        self.save_puz()


class NewYorkerDownloader(AmuseLabsDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

    def guess_url_from_date(self, dt):
        url_format = dt.strftime('%Y/%m/%d')
        guessed_url = urllib.parse.urljoin(
                'https://www.newyorker.com/crossword/puzzles-dept/',
                url_format)
        self.find_solver(url=guessed_url)

    def find_latest(self):
        index_url = "https://www.newyorker.com/crossword/puzzles-dept"
        index_res = requests.get(index_url)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_fragment = next(a for a in index_soup.findAll('a') if a.find('h4'))['href']
        latest_absolute = urllib.parse.urljoin('https://www.newyorker.com',
                                                latest_fragment)

        self.find_solver(url=latest_absolute)

    def find_solver(self, url):
        res = requests.get(url)

        if res.status_code == 404:
            sys.exit('Unable to find a puzzle at {}'.format(url))
 
        soup = BeautifulSoup(res.text, "html.parser")

        self.url = soup.find('iframe', attrs={'id':'crossword'})['data-src']

        if not self.output:
            path = urllib.parse.urlsplit(url).path
            date_frags = path.split('/')[-3:]
            date_mash = ''.join(date_frags)
            self.output = ''.join(['tny', date_mash, '.puz'])


class NewsdayDownloader(AmuseLabsDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

    def guess_url_from_date(self, dt):
        url_format = dt.strftime('%Y%m%d')
        guessed_url = ''.join([
            'https://cdn2.amuselabs.com/pmm/crossword?id=Creators_WEB_',
            url_format, '&set=creatorsweb'])
        if not self.output:
            self.output = ''.join(['nd', url_format, '.puz'])
        self.find_solver(url=guessed_url)

    def find_latest(self):
        datepicker_url = "https://cdn2.amuselabs.com/pmm/date-picker?set=creatorsweb"
        res = requests.get(datepicker_url)
        soup = BeautifulSoup(res.text, 'html.parser')

        data_id = soup.find('li', attrs={'class':'tile'})['data-id']

        if not self.output:
            self.output = 'nd' + data_id.split('_')[-1] + '.puz'

        url = "https://cdn2.amuselabs.com/pmm/crossword?id={}&set=creatorsweb".format(
                data_id)

        self.find_solver(url=url)

    def find_solver(self, url):
        self.url = url


class WSJDownloader(BaseDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

    def guess_url_from_date(self, dt):
        pass

    def find_latest(self):
        url = "https://blogs.wsj.com/puzzle/category/crossword/"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
        latest_url = soup.find('h4',
                attrs={'class':'headline'}).find('a').get('href', None)

        self.find_solver(url=latest_url)

    def find_solver(self, url):
        if '/puzzle/crossword/' in url:
            self.url = url
        else:
            res = requests.get(url)
            soup = BeautifulSoup(res.text, 'html.parser')
            puzzle_link = 'https:' + soup.find('a',
                    attrs={'class':'puzzle-link'}).get('href')
            self.url = puzzle_link

    def download(self):
        self.url = self.url.replace('index.html', 'data.json')
        xword_data = requests.get(self.url).json()['data']['copy']

        date = xword_data.get('date-publish-analytics').split()[0].replace('/','')

        if not self.output:
            self.output = 'wsj' + date + '.puz'

        self.puzfile.title = xword_data.get('title', '')
        self.puzfile.author = xword_data.get('byline', '')
        self.puzfile.copyright = xword_data.get('publisher', '')
        self.puzfile.width = int(xword_data.get('gridsize').get('cols'))
        self.puzfile.height = int(xword_data.get('gridsize').get('rows'))

        solution = xword_data.get('settings').get('solution').replace(' ', '.')
        self.puzfile.solution = solution

        fill = ''
        for letter in solution:
            if letter == '.':
                fill += '.'
            else:
                fill += '-'
        self.puzfile.fill = fill

        clue_list = xword_data['clues'][0]['clues'] + xword_data['clues'][1]['clues']
        sorted_clue_list = sorted(clue_list, key=lambda x: int(x['number']))

        clues = [clue['clue'] for clue in sorted_clue_list]

        self.puzfile.clues = clues

        self.save_puz()


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
    newyorker_parser.set_defaults(downloader_class=NewYorkerDownloader)

    newsday_parser = subparsers.add_parser('nd',
                            aliases=['newsday'],
                            parents=[extractor_parent],
                            help="download a Newsday puzzle")
    newsday_parser.set_defaults(downloader_class=NewsdayDownloader)

    wsj_parser = subparsers.add_parser('wsj',
                            aliases=['wallstreet'],
                            parents=[extractor_parent,
                                     extractor_url_parent],
                            help="download a Wall Street Journal puzzle")
    wsj_parser.set_defaults(downloader_class=WSJDownloader)

    parser.add_argument('--url', help='URL of puzzle to download')

    args = parser.parse_args()

    dl = args.downloader_class(output=args.output)

    if args.date:
        entered_date = ' '.join(args.date)
        dl.find_by_date(entered_date)

    elif args.url:
        dl.find_solver(args.url)

    elif args.latest:
        dl.find_latest()

    dl.download()


if __name__ == '__main__':
    main()
