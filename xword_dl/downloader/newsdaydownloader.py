import datetime

from .amuselabsdownloader import AmuseLabsDownloader

class NewsdayDownloader(AmuseLabsDownloader):
    command = 'nd'
    outlet = 'Newsday'
    outlet_prefix = 'Newsday'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn2.amuselabs.com/pmm/date-picker?set=creatorsweb'
        self.url_from_id = 'https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=creatorsweb'

    def guess_date_from_id(self, puzzle_id):
        date_string = puzzle_id.split('_')[2]
        self.date = datetime.datetime.strptime(date_string, '%Y%m%d')

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%Y%m%d')
        self.id = 'Creators_WEB_' + url_formatted_date

        self.get_and_add_picker_token()

        return self.find_puzzle_url_from_id(self.id)
