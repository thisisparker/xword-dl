import datetime

from .amuselabsdownloader import AmuseLabsDownloader

class LATimesDownloader(AmuseLabsDownloader):
    command = 'lat'
    outlet = 'Los Angeles Times'
    outlet_prefix = 'LA Times'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn4.amuselabs.com/lat/date-picker?set=latimes'
        self.url_from_id = 'https://cdn4.amuselabs.com/lat/crossword?id={puzzle_id}&set=latimes'

    def guess_date_from_id(self, puzzle_id):
        date_string = ''.join([char for char in puzzle_id if char.isdigit()])
        self.date = datetime.datetime.strptime(date_string, '%y%m%d')

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%y%m%d')
        self.id = 'tca' + url_formatted_date

        self.get_and_add_picker_token()

        return self.find_puzzle_url_from_id(self.id)

    def pick_filename(self, puzzle, **kwargs):
        split_on_dashes = puzzle.title.split(' - ')
        if len(split_on_dashes) > 1:
            title = split_on_dashes[-1].strip()
        else:
            title = ''

        return super().pick_filename(puzzle, title=title, **kwargs)
