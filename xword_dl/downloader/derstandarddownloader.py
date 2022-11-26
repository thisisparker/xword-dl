import datetime
import json
import re
import urllib

import dateparser
import requests

from bs4 import BeautifulSoup

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException

class DerStandardDownloader(AmuseLabsDownloader):
    command = 'std'
    outlet = 'Der Standard'
    outlet_prefix = 'Der Standard'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = 'https://cdn-eu1.amuselabs.com/pmm/crossword?id={puzzle_id}&set=phoenixen'
        self.headers = {
            'User-Agent':'Googlebot', # needed to get around privacy consent screen
            'DNT':'1'
        }

    @staticmethod
    def matches_url(url_components):
        return ('derstandard.at' in url_components.netloc and '/kreuzwortraetsel' in url_components.path)

    def find_latest(self):
        index_url = "https://www.derstandard.at/lifestyle/raetsel-sudoku/kreuzwortraetsel"
        index_res = requests.get(index_url, headers=self.headers, timeout=10)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_fragment = next(a for a in index_soup.select('.teaser-inner > a'))['href']
        latest_absolute = urllib.parse.urljoin('https://www.derstandard.at',
                                               latest_fragment)

        landing_page_url = latest_absolute

        return landing_page_url

    def find_solver(self, url):
        res = requests.get(url, headers=self.headers, timeout=10)

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            raise XWordDLException('Unable to load {}'.format(url))

        try:
            # html embed content is encoded -> beautifulsoup parsing would not work
            query_id = list(re.findall(r'(http)(s)*(:\/\/cdn\-eu1\.amuselabs\.com\/pmm\/crossword)(\?id\=)([0-9a-z]{8})', str(res.text)))
            
            if len(query_id) == 0:
                raise XWordDLException('Cannot find puzzle at {} -> failed to retrieve amuselabs url from encoded html.'.format(url))
            
            self.id = str(query_id[0][-1])
        except KeyError:
            raise XWordDLException('Cannot find puzzle at {}.'.format(url))

        return self.find_puzzle_url_from_id(self.id)

    def pick_filename(self, puzzle, **kwargs):
        """
        replace umlauts in puzzle title and return filename
        """
        umlauts = {
            'Ä':'AE',
            'Ü':'UE',
            'Ö':'UE',
            'ä':'ae',
            'ö':'oe',
            'ü':'ue',
            'ß':'ss'
        }

        title = str(puzzle.title)
        for umlaut, rep in umlauts.items():
            title = title.replace(umlaut, rep)

        return super().pick_filename(puzzle, title=title, **kwargs)
