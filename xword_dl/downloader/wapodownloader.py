import datetime

from .amuselabsdownloader import AmuseLabsDownloader

class WaPoDownloader(AmuseLabsDownloader):
    command = 'wp'
    outlet = 'Washington Post'
    outlet_prefix = 'WaPo'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn1.amuselabs.com/wapo/wp-picker?set=wapo-eb'
        self.url_from_id = 'https://cdn1.amuselabs.com/wapo/crossword?id={puzzle_id}&set=wapo-eb'

    def guess_date_from_id(self, puzzle_id):
        self.date = datetime.datetime.strptime('20'
                                               + puzzle_id.split('_')[1], '%Y%m%d')

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%y%m%d')
        self.id = 'ebirnholz_' + url_formatted_date

        return self.find_puzzle_url_from_id(self.id)
