import datetime
import json
import urllib

import dateparser
import requests

from bs4 import BeautifulSoup

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import unidecode, XWordDLException

class NewYorkerDownloader(AmuseLabsDownloader):
    command = 'tny'
    outlet = 'New Yorker'
    outlet_prefix = 'New Yorker'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = 'https://cdn3.amuselabs.com/tny/crossword?id={puzzle_id}&set=tny-weekly'

        self.theme_title = ''

    @staticmethod
    def matches_url(url_components):
        return ('newyorker.com' in url_components.netloc and '/puzzles-and-games-dept/crossword' in url_components.path)

    def guess_date_from_id(self, puzzle_id):
        self.date = datetime.datetime.strftime(puzzle_id.split('_')[-1])

    def find_by_date(self, dt):
        url_format = dt.strftime('%Y/%m/%d')
        guessed_url = urllib.parse.urljoin(
            'https://www.newyorker.com/puzzles-and-games-dept/crossword/',
            url_format)
        return guessed_url

    def find_latest(self):
        index_url = "https://www.newyorker.com/puzzles-and-games-dept/crossword"
        index_res = requests.get(index_url)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_fragment = next(a for a in index_soup.findAll('a')
                               if a.find('h4'))['href']
        latest_absolute = urllib.parse.urljoin('https://www.newyorker.com',
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

        iframe_tag = soup.find('iframe', id='crossword')

        try:
            iframe_url = iframe_tag['data-src']
            query = urllib.parse.urlparse(iframe_url).query
            query_id = urllib.parse.parse_qs(query)['id']
            self.id = query_id[0]

        # Will hit this KeyError if there's no matching iframe
        # or if there's no 'id' query string
        except KeyError:
            raise XWordDLException('Cannot find puzzle at {}.'.format(url))

        pubdate = soup.find('time').get_text()
        pubdate_dt = dateparser.parse(pubdate)

        self.date = pubdate_dt

        theme_supra = "Today’s theme: "
        desc = soup.find('meta',attrs={'property':
                                       'og:description'}).get('content', '')
        if desc.startswith(theme_supra):
            self.theme_title = unidecode(desc[len(theme_supra):].rstrip('.'))

        return self.find_puzzle_url_from_id(self.id)
        
    def parse_xword(self, xword_data):
        puzzle = super().parse_xword(xword_data)

        if '<' in puzzle.title:
            puzzle.title = puzzle.title.split('<')[0]

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        try:
            supra, main = puzzle.title.split(':', 1)
            if supra == 'The Crossword' and dateparser.parse(main):
                if self.theme_title:
                    title = self.theme_title
                    puzzle.title += f' - {self.theme_title}'
                else:
                    title = ''
            else:
                title = main.strip()
        except XWordDLException:
            title = puzzle.title
        return super().pick_filename(puzzle, title=title, **kwargs)
