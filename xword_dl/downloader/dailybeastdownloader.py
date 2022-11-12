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

        # Daily Beast puzzle IDs, unusually for AmuseLabs puzzles, don't include
        # the date. This pulls it out of the puzzle title, which will work
        # as long as that stays consistent.

        possible_dates = dateparser.search.search_dates(puzzle.title)

        if possible_dates:
            self.date = possible_dates[-1][1]
        else:
            self.date = datetime.datetime.today()

        return puzzle
