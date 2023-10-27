import datetime
import json
import sys
import time
import urllib
import xml

import puz
import requests
import xmltodict

from urllib.parse import unquote

from .basedownloader import BaseDownloader
from ..util import XWordDLException, unidecode

class AMUniversalDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url_blob = None

    def find_by_date(self, dt):
        self.date = dt

        url_format = dt.strftime('%Y-%m-%d')
        return self.url_blob + url_format + '/data.json'

    def find_latest(self):
        dt = datetime.datetime.today()
        return self.find_by_date(dt)

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url):
        attempts = 3
        while attempts:
            try:
                res = requests.get(solver_url)
                xword_data = res.json()
                break
            except json.JSONDecodeError:
                print('Unable to download puzzle data. Trying again.',
                      file=sys.stderr)
                time.sleep(2)
                attempts -= 1
        else:
            raise XWordDLException('Unable to download puzzle data.')
        return xword_data

    def process_clues(self, clue_list):
        """Return clue list without any end markers"""

        return clue_list

    def parse_xword(self, xword_data):
        fetched = {}
        for field in ['Title', 'Author', 'Editor', 'Copryight']:
            fetched[field] = urllib.parse.unquote(
                xword_data.get(field, '')).strip()

        puzzle = puz.Puzzle()
        puzzle.title = fetched.get('Title', '')
        puzzle.author = ''.join([fetched.get('Author', ''),
                                 ' / Ed. ',
                                 fetched.get('Editor', '')])
        puzzle.copyright = fetched.get('Copyright', '')
        puzzle.width = int(xword_data.get('Width'))
        puzzle.height = int(xword_data.get('Height'))

        solution = xword_data.get('AllAnswer').replace('-', '.')

        puzzle.solution = solution

        fill = ''
        for letter in solution:
            if letter == '.':
                fill += '.'
            else:
                fill += '-'
        puzzle.fill = fill

        across_clues = xword_data['AcrossClue'].splitlines()
        down_clues = self.process_clues(xword_data['DownClue'].splitlines())

        clues_list = across_clues + down_clues

        clues_list_stripped = [{'number': clue.split('|')[0],
                                'clue':clue.split('|')[1]} for clue in clues_list]

        clues_sorted = sorted(clues_list_stripped, key=lambda x: x['number'])

        clues = [clue['clue'] for clue in clues_sorted]

        puzzle.clues = clues

        return puzzle

# As of Sept 2023, the JSON data for USA Today is not consistently populated.
# I'd rather use the JSON data if possible, but until that's sorted, we can
# use an alternative approach. As such, commenting out but not deleting the
# earlier version here.
#
#class USATodayDownloader(AMUniversalDownloader):
#    command = 'usa'
#    outlet = 'USA Today'
#    outlet_prefix = 'USA Today'
#
#    def __init__(self, **kwargs):
#        super().__init__(**kwargs)
#
#        self.url_blob = 'https://gamedata.services.amuniversal.com/c/uupuz/l/U2FsdGVkX18CR3EauHsCV8JgqcLh1ptpjBeQ%2Bnjkzhu8zNO00WYK6b%2BaiZHnKcAD%0A9vwtmWJp2uHE9XU1bRw2gA%3D%3D/g/usaon/d/'
#
#    def process_clues(self, clue_list):
#        """Remove the end marker found in USA Today puzzle JSON."""
#
#        return clue_list[:-1]

class USATodayDownloader(BaseDownloader):
    command = 'usa'
    outlet = 'USA Today'
    outlet_prefix = 'USA Today'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def find_by_date(self, dt):
        self.date = dt
        url = f'http://picayune.uclick.com/comics/usaon/data/usaon{dt:%y%m%d}-data.xml'
        try:
            res = requests.head(url)
            res.raise_for_status()
        except:
            raise XWordDLException('Unable to find puzzle for date provided.')

        return url

    def find_latest(self):
        check_date = datetime.datetime.today()
        days_to_check = 3
        while days_to_check:
            try:
                url = self.find_by_date(check_date)
                break
            except XWordDLException:
                days_to_check -= 1
                check_date -= datetime.timedelta(1)
        else:
            raise XWordDLException('Unable to find latest puzzle.')

        return url

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url):
        res = requests.get(solver_url)

        xw_data = res.content.decode()

        return xw_data

    def parse_xword(self, xword_data):
        try:
            xw = xmltodict.parse(xword_data).get('crossword')
        except xml.parsers.expat.ExpatError:
            raise XWordDLException('Puzzle data malformed, cannot parse.')

        puzzle = puz.Puzzle()

        puzzle.title = unquote(xw.get('Title',[]).get('@v') or '')
        puzzle.author = unquote(xw.get('Author',[]).get('@v') or '')
        puzzle.copyright = unquote(xw.get('Copyright',[]).get('@v') or '')

        puzzle.width = int(xw.get('Width')['@v'])
        puzzle.height = int(xw.get('Height')['@v'])

        puzzle.solution = xw.get('AllAnswer',[]).get('@v').replace('-', '.')
        puzzle.fill = ''.join([c if c == '.' else '-' for c in puzzle.solution])

        xw_clues = sorted(list(xw['across'].values()) + list(xw['down'].values()),
                          key=lambda c: int(c['@cn']))

        puzzle.clues = [unidecode(unquote(c.get('@c') or '')) for c in xw_clues]

        return puzzle


class UniversalDownloader(AMUniversalDownloader):
    command = 'uni'
    outlet = 'Universal'
    outlet_prefix = 'Universal'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_blob = 'https://embed.universaluclick.com/c/uucom/l/U2FsdGVkX18YuMv20%2B8cekf85%2Friz1H%2FzlWW4bn0cizt8yclLsp7UYv34S77X0aX%0Axa513fPTc5RoN2wa0h4ED9QWuBURjkqWgHEZey0WFL8%3D/g/fcx/d/'
