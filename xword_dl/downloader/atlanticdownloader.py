import datetime

from .amuselabsdownloader import AmuseLabsDownloader

class AtlanticDownloader(AmuseLabsDownloader):
    command = 'atl'
    outlet = 'Atlantic'
    outlet_prefix = 'Atlantic'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn3.amuselabs.com/atlantic/date-picker?set=atlantic'
        self.url_from_id = 'https://cdn3.amuselabs.com/atlantic/crossword?id={puzzle_id}&set=atlantic'

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%Y%m%d')
        self.id = 'atlantic_' + url_formatted_date

        return self.find_puzzle_url_from_id(self.id)

    def guess_date_from_id(self, puzzle_id):
        self.date = datetime.datetime.strptime(puzzle_id.split('_')[1],
                                               '%Y%m%d')
