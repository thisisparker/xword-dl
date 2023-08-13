import datetime
import json
import urllib

import dateparser
import requests

from bs4 import BeautifulSoup

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException

class McKinseyDownloader(AmuseLabsDownloader):
    command = 'mck'
    outlet = 'The McKinsey Crossword'
    outlet_prefix = 'McKinsey'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = 'https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=mckinsey'

    @staticmethod
    def matches_url(url_components):
        return ('mckinsey.com' in url_components.netloc and '/featured-insights/the-mckinsey-crossword' in url_components.path)

    def find_by_date(self, dt):
        """
        date format: month-day-year (e.g. november-15-2022)
        no leading zeros on dates (so: e.g., august-1-2023)
        crosswords are published every tuesday (as of november 2022)
        """
        month_names = ['january','february','march','april','may','june','july',
                       'august','septermber','october','november','december']
        url_format = f'{month_names[dt.month-1]}-{dt.day}-{dt.year}'
        guessed_url = urllib.parse.urljoin(
            'https://www.mckinsey.com/featured-insights/the-mckinsey-crossword/',
            url_format)
        return guessed_url

    def find_latest(self):
        index_url = "https://www.mckinsey.com/featured-insights/the-mckinsey-crossword/"
        index_res = requests.get(index_url)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_fragment = next(a for a in index_soup.select('a.mdc-c-link-heading[href^="/featured-insights/the-mckinsey-crossword/"]')
                               if a.find('div'))['href']
        latest_absolute = urllib.parse.urljoin('https://www.mckinsey.com',
                                               latest_fragment)

        landing_page_url = latest_absolute

        return landing_page_url

    def find_solver(self, url):
        res = requests.get(url)

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            raise XWordDLException('Unable to load {}'.format(url))

        soup = BeautifulSoup(res.text, "html.parser")

        iframe_tag = soup.select('iframe[src*="amuselabs.com"]')

        if len(iframe_tag) == 0:
            raise XWordDLException('Cannot find puzzle iframe node at {}.'.format(url))

        iframe_url = str(iframe_tag[0].get('src'))

        try:
            query = urllib.parse.urlparse(iframe_url).query
            query_id = urllib.parse.parse_qs(query)['id']
            self.id = query_id[0]
        except KeyError:
            raise XWordDLException('Cannot find puzzle at {}.'.format(url))

        pubdate = url.split('/')[-1].replace('-',' ').capitalize()
        pubdate_dt = dateparser.parse(pubdate)
        self.date = pubdate_dt

        return self.find_puzzle_url_from_id(self.id)
