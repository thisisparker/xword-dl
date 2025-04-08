import datetime

import dateparser.search

from .amuselabsdownloader import AmuseLabsDownloader

class DailyBeastDownloader(AmuseLabsDownloader):
    command = 'db'
    outlet = 'Daily Beast'
    outlet_prefix = 'Daily Beast'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn3.amuselabs.com/tdb/date-picker?set=tdb'
        self.url_from_id = 'https://cdn3.amuselabs.com/tdb/crossword?id={puzzle_id}&set=tdb'

    def parse_xword(self, xword_data):
        puzzle = super().parse_xword(xword_data)

        # Daily Beast puzzle IDs don't include the date.
        # This pulls it out of the puzzle title (with periods removed because
        # they mess with the date parser)

        possible_dates = dateparser.search.search_dates(
                            puzzle.title.replace('.',''))

        if possible_dates:
            self.date = possible_dates[-1][1]
        else:
            self.date = datetime.datetime.today()

        return puzzle
