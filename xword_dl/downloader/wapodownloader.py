import datetime

from .amuselabsdownloader import AmuseLabsDownloader

class WaPoDownloader(AmuseLabsDownloader):
    outlet = 'Washington Post'
    outlet_prefix = 'WaPo'

    def __init__(self, puzzle_set, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn1.amuselabs.com/wapo/wp-picker?set=' + puzzle_set
        self.url_from_id = 'https://cdn1.amuselabs.com/wapo/crossword?id={puzzle_id}&set=' + puzzle_set
        self.landing_page = 'https://www.washingtonpost.com/crossword-puzzles/'

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%y%m%d')
        self.id = self.puzzle_set_code + url_formatted_date

        return self.find_puzzle_url_from_id(self.id)

    def guess_date_from_id(self, puzzle_id):
        self.date = datetime.datetime.strptime('20'
                                               + puzzle_id.removeprefix(self.puzzle_set_code), '%Y%m%d')


class WaPoDailyDownloader(WaPoDownloader):
    command = 'wpd'
    outlet = 'Washington Post Daily'
    outlet_prefix = 'WaPo Daily'

    def __init__(self, **kwargs):
        super().__init__(puzzle_set = 'wapo-daily', **kwargs)

        self.landing_page += 'daily/'
        self.puzzle_set_code = 'tca'


class WaPoSundayDownloader(WaPoDownloader):
    command = 'wps'
    outlet = 'Washington Post Sunday'
    outlet_prefix = 'WaPo Sunday'

    def __init__(self, **kwargs):
        super().__init__(puzzle_set = 'wapo-eb', **kwargs)

        self.landing_page += 'sunday-evan-birnholz/'
        self.puzzle_set_code = 'ebirnholz_'
