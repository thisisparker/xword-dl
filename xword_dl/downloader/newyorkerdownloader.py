import datetime
import json
import urllib

import dateparser
import requests

from bs4 import BeautifulSoup

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException

class NewYorkerDownloader(AmuseLabsDownloader):
    command = 'tny'
    outlet = 'New Yorker'
    outlet_prefix = 'New Yorker'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = 'https://cdn3.amuselabs.com/tny/crossword?id={puzzle_id}&set=tny-weekly'

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

        script_tag = soup.find('script', attrs={'type': 'application/ld+json'})

        json_data = json.loads(script_tag.contents[0])

        iframe_url = json_data['articleBody'].strip().strip('[]')[
            len('#crossword: '):]

        try:
            query = urllib.parse.urlparse(iframe_url).query
            query_id = urllib.parse.parse_qs(query)['id']
            self.id = query_id[0]
        except KeyError:
            raise XWordDLException('Cannot find puzzle at {}.'.format(url))

        pubdate = soup.find('time').get_text()
        pubdate_dt = dateparser.parse(pubdate)

        self.date = pubdate_dt

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
                title = ''
            else:
                title = main.strip()
        except XWordDLException:
            title = puzzle.title
        return super().pick_filename(puzzle, title=title, **kwargs)
