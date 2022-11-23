import datetime
import urllib

import puz
import requests

from .basedownloader import BaseDownloader
from ..util import *

class NewYorkTimesDownloader(BaseDownloader):
    command = 'nyt'
    outlet = 'New York Times'
    outlet_prefix = 'NY Times'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = 'https://www.nytimes.com/svc/crosswords/v2/puzzle/{}.json'
        self.url_from_date = 'https://www.nytimes.com/svc/crosswords/v6/puzzle/daily/{}.json'

        if 'url' in kwargs and not self.date:
            self.date = self.parse_date_from_url(kwargs.get('url'))

        self.headers = {}
        self.cookies = {}

        username = self.settings.get('username')
        password = self.settings.get('password')

        if username and password:
            nyts_token = self.authenticate(username, password)
            update_config_file('nyt', {'NYT-S': nyts_token})
        else:
            nyts_token = self.settings.get('NYT-S')

        if not nyts_token:
            raise XWordDLException('No credentials provided or stored. Try running xword-dl nyt --authenticate')
        else:
            self.cookies.update({'NYT-S': nyts_token})

    @staticmethod
    def matches_url(url_components):
        return ('nytimes.com' in url_components.netloc
                    and 'crosswords/game/daily' in url_components.path)

    def authenticate(self, username, password):
        """Given a NYT username and password, returns the NYT-S cookie value"""

        res = requests.post('https://myaccount.nytimes.com/svc/ios/v2/login',
                data={'login': username, 'password': password},
                headers={'User-Agent':
                    'Crossword/1844.220922 CFNetwork/1335.0.3 Darwin/21.6.0',
                    'client_id': 'ios.crosswords',})

        res.raise_for_status()

        nyts_token = ''

        for cookie in res.json()['data']['cookies']:
            if cookie['name'] == 'NYT-S':
                nyts_token = cookie['cipheredValue']

        if nyts_token:
            return nyts_token
        else:
            raise XWordDLException('NYT-S cookie not found.')

    def parse_date_from_url(self, url):
        path = urllib.parse.urlparse(url).path
        date_string = ''.join(path.split('/')[-3:])

        return datetime.datetime.strptime(date_string, '%Y%m%d')

    def find_latest(self):
        oracle = "https://www.nytimes.com/svc/crosswords/v2/oracle/daily.json"

        res = requests.get(oracle)
        puzzle_date = res.json()['results']['current']['print_date']

        url = self.url_from_date.format(puzzle_date)

        return url

    def find_by_date(self, dt):
        return self.url_from_date.format(dt.strftime('%Y-%m-%d'))

    def find_solver(self, url):
        if not url.endswith('.json'):
            url = self.find_by_date(self.parse_date_from_url(url))

        return url

    def fetch_data(self, solver_url):
        res = requests.get(solver_url, cookies=self.cookies)

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if res.status_code == 403:
                raise XWordDLException('Puzzle data not available. Try re-authenticating with xword-dl nyt --authenticate')
            elif res.status_code == 404:
                raise XWordDLException('Puzzle data not found.')
            else:
                raise XWordDLException('HTTP error:', e)

        xword_data = res.json()
        return xword_data

    def parse_xword(self, xword_data):
        puzzle = puz.Puzzle()

        puzzle.author = ', '.join(xword_data['constructors']).strip()
        puzzle.copyright = xword_data['copyright'].strip()
        puzzle.height = int(xword_data['body'][0]['dimensions']['height'])
        puzzle.width =  int(xword_data['body'][0]['dimensions']['width'])

        if not self.date:
            self.date = datetime.datetime.strptime(xword_data['publicationDate'],
                                          '%Y-%m-%d')

        puzzle.title = xword_data.get('title') or self.date.strftime(
                '%A, %B %d, %Y')

        if xword_data.get('notes'):
            puzzle.notes = unidecode(xword_data.get('notes')[0]['text']).strip()

        solution = ''
        fill = ''
        markup = b''
        rebus_board = []
        rebus_index = 0
        rebus_table = ''

        for idx, square in enumerate(xword_data['body'][0]['cells']):
            if not square:
                solution += '.'
                fill += '.'
                rebus_board.append(0)
            elif square and len(square['answer']) == 1:
                solution += square['answer']
                fill += '-'
                rebus_board.append(0)
            else:
                solution += square['answer'][0]
                fill += '-'
                rebus_board.append(rebus_index + 1)
                rebus_table += '{:2d}:{};'.format(rebus_index, square['answer'])
                rebus_index += 1

            markup += (b'\x00' if square.get('type') == 1 else b'\x80')

        puzzle.solution = solution
        puzzle.fill = fill

        if b'\x80' in markup:
            puzzle.extensions[b'GEXT'] = markup
            puzzle._extensions_order.append(b'GEXT')
            puzzle.markup()

        if any(rebus_board):
            puzzle.extensions[b'GRBS'] = bytes(rebus_board)
            puzzle.extensions[b'RTBL'] = rebus_table.encode(puz.ENCODING)
            puzzle._extensions_order.extend([b'GRBS', b'RTBL'])
            puzzle.rebus()

        clue_list = xword_data['body'][0]['clues']
        clue_list.sort(key=lambda c: (int(c['label']), c['direction']))

        puzzle.clues = [unidecode(c['text'][0]['plain']) for c in clue_list]

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        if puzzle.title == self.date.strftime('%A, %B %d, %Y'):
            title = ''
        else:
            title = puzzle.title

        return super().pick_filename(puzzle, title=title, **kwargs)


class NewYorkTimesVarietyDownloader(NewYorkTimesDownloader):
    command = 'nytv'
    outlet = 'New York Times Variety'
    outlet_prefix = 'NY Times Variety'

    def __init__(self, **kwargs):
        super().__init__(inherit_settings='nyt', **kwargs)

        self.url_from_date = 'https://www.nytimes.com/svc/crosswords/v6/puzzle/variety/{}.json'

    @staticmethod
    def matches_url(url_components):
        return ('nytimes.com' in url_components.netloc
                    and 'variety' in url_components.path)

    def find_latest(self):
        latest_puzzles = 'https://www.nytimes.com/svc/crosswords/v3/puzzles.json?format_type=pdf%2Cnormal%2Cdiagramless&publish_type=variety%2Cassorted&sort_order=asc&sort_by=print_date&date_start={}&date_end={}'

        today_string = datetime.datetime.today().strftime('%Y-%m-%d')
        a_while_back = (datetime.datetime.today()
                            - datetime.timedelta(days=90)).strftime('%Y-%m-%d')

        res = requests.get(latest_puzzles.format(a_while_back, today_string))
        normal_puzzles = [p for p in res.json()['results']
                                if p['format_type'] == 'Normal']

        return self.url_from_date.format(normal_puzzles[-1]['print_date'])

    def parse_xword(self, xword_data):
        try:
            return super().parse_xword(xword_data)
        except ValueError:
            raise XWordDLException('Encountered error while parsing data. Maybe the selected puzzle is not a crossword?')
