from datetime import datetime
import urllib

from .compilerdownloader import CrosswordCompilerDownloader

class SimplyDailyDownloader(CrosswordCompilerDownloader):
    command = 'sdp'
    website = 'simplydailypuzzles.com'
    outlet = 'Simply Daily Puzzles'
    outlet_prefix = 'Simply Daily'
    url_subdir = 'daily-crossword'
    qs_prefix = 'dc1'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.fetch_data = self.fetch_jsencoded_data
        self.date = None

        if 'url' in kwargs and not self.date:
            self.date = self.parse_date_from_url(kwargs.get('url'))

    @classmethod
    def matches_url(cls, url_components):
         return (cls.website in url_components.netloc and
                f'/{cls.url_subdir}/' in url_components.path)

    def parse_date_from_url(self, url):
        query_str = urllib.parse.urlparse(url).query
        query_dict = urllib.parse.parse_qs(query_str)
        
        try:
            puzz = query_dict['puzz'][0]
        except KeyError:
            date = datetime.today()
        else:
            date = datetime.strptime(puzz, f'{self.qs_prefix}-%Y-%m-%d')
            
        return date

    def find_solver(self, url):
        date = self.parse_date_from_url(url)
            
        pd = f'{date.strftime("%Y-%m")}'
        js = f'{self.qs_prefix}-{date.strftime("%Y-%m-%d")}.js'
        return f'https://{self.website}/{self.url_subdir}/puzzles/{pd}/{js}'

    def find_by_date(self, dt):
        self.date = dt # self.date used by BaseDownloader.pick_filename()
        
        qs = f'puzz={self.qs_prefix}-{dt.strftime("%Y-%m-%d")}'
        return f'https://{self.website}/{self.url_subdir}/index.html?{qs}'

    def find_latest(self):
        return self.find_by_date(datetime.today())

class SimplyDailyCrypticDownloader(SimplyDailyDownloader):
    command = 'sdpc'
    outlet = 'Simply Daily Puzzles Cryptic'
    outlet_prefix = 'Simply Daily Cryptic'
    url_subdir = 'daily-cryptic'
    qs_prefix = 'dc1'

class SimplyDailyQuickDownloader(SimplyDailyDownloader):
    command = 'sdpq'
    outlet = 'Simply Daily Puzzles Quick'
    outlet_prefix = 'Simply Daily Quick'
    url_subdir = 'daily-quick-crossword'
    qs_prefix = 'dq1'
