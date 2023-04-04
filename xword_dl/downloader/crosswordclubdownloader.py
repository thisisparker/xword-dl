import urllib

import dateparser
import requests

from bs4 import BeautifulSoup

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException

class CrosswordClubDownloader(AmuseLabsDownloader):
    command = 'club'
    outlet = 'Crossword Club'
    outlet_prefix = 'Crossword Club'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = 'https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=pardon-crossword'

    @staticmethod
    def matches_url(url_components):
        return ('crosswordclub.com' in url_components.netloc
                and '/puzzles' in url_components.path)

    def find_by_date(self, dt):
        """
        date format: weekday-month-day-year (e.g. thursday-february-09-2023)
        crosswords are published daily
        """
        url_format = str(dt.strftime('%A-%B-%d-%Y')).lower()
        guessed_url = urllib.parse.urljoin(
            'https://crosswordclub.com/puzzles/',
            url_format)
        return guessed_url

    def find_latest(self):
        index_url = "https://crosswordclub.com/puzzles/"
        index_res = requests.get(index_url)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_url = next(a for a in index_soup.select('.all-puzzle-list a[href^="https://crosswordclub.com/puzzles/"]'))['href']
        
        return latest_url

    def find_solver(self, url):
        res = requests.get(url)

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            raise XWordDLException('Unable to load {}'.format(url))

        soup = BeautifulSoup(res.text, "html.parser")

        iframe_tag = soup.select('iframe[src*="amuselabs.com/pmm/"]')

        iframe_url = str(iframe_tag[0].get('src'))

        try:
            query = urllib.parse.urlparse(iframe_url).query
            query_id = urllib.parse.parse_qs(query)['id']
            self.id = query_id[0]
        except KeyError:
            raise XWordDLException('Cannot find puzzle at {}.'.format(url))

        pubdate_url_component = url.split('/')[-1] or url.split('/')[-2]
        pubdate = pubdate_url_component.replace('-', ' ')
        pubdate_dt = dateparser.parse(pubdate)
        self.date = pubdate_dt

        return super().find_solver(self.find_puzzle_url_from_id(self.id))
