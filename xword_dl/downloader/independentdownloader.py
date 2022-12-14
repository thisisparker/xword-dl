import datetime

from .compilerdownloader import CrosswordCompilerDownloader

class TheIndependentDownloader(CrosswordCompilerDownloader):
    command = 'ind'
    outlet = 'The Independent (cryptic)'
    outlet_prefix = 'The Independent'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.url_format = 'https://ams.cdn.arkadiumhosted.com/assets/gamesfeed/independent/daily-crossword/c_{url_encoded_date}.xml'

    @staticmethod
    def matches_url(url_components):
        return 'puzzles.independent.co.uk' in url_components.netloc and '/games/cryptic-crossword-independent' in url_components.path

    def find_latest(self):
        return self.find_by_date(datetime.datetime.today())

    def find_by_date(self, dt):
        self.date = dt

        return self.url_format.format(url_encoded_date=dt.strftime('%y%m%d'))

    def find_solver(self, url):
        print('solver url', url)
        return url
