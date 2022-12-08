import datetime
import requests
import urllib

from .compilerdownloader import CrosswordCompilerDownloader
from ..util import XWordDLException

class DailyPopDownloader(CrosswordCompilerDownloader):
    outlet = 'Daily Pop'
    command = 'pop'
    outlet_prefix = 'Daily Pop'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.api_url = 'https://api.puzzlenation.com/dailyPopCrosswords/puzzles/daily/'

        self.settings['headers'] = self.settings.get('headers', {})
        if 'x-api-key' not in self.settings['headers']:
            self.settings['headers']['x-api-key'] = self.get_api_key()

    def get_api_key(self):
        res = requests.get('http://dailypopcrosswordsweb.puzzlenation.com/crosswordSetup.js')

        api_key = None

        for l in res.text.splitlines():
            if l.startswith('const API_KEY = '):
                api_key = l[len('const API_KEY = "'):-2]

        if not api_key:
            raise XWordDLException('Could not find Daily Pop API Key.')

        return api_key

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%y%m%d')
        self.date = dt
        return urllib.parse.urljoin(self.api_url, url_formatted_date)

    def find_latest(self):
        dt = datetime.datetime.today()
        return self.find_by_date(dt)

    def fetch_data(self, url):
        res = requests.get(url, headers=self.settings['headers'])

        return res.text
