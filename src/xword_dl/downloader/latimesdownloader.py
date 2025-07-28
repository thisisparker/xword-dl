import datetime

import dateparser

from .amuselabsdownloader import AmuseLabsDownloader


class LATimesDownloader(AmuseLabsDownloader):
    command = "lat"
    outlet = "Los Angeles Times"
    outlet_prefix = "LA Times"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = "https://lat.amuselabs.com/lat/date-picker?set=latimes"
        self.url_from_id = (
            "https://lat.amuselabs.com/lat/crossword?id={puzzle_id}&set=latimes"
        )

    def guess_date_from_id(self, puzzle_id):
        date_string = "".join([char for char in puzzle_id if char.isdigit()])
        # Historically the Amuse ID has very consistently been tca_yyyymmdd
        # but if it's not (as on 2025-07-05) this breaks without the try/except
        try:
            self.date = datetime.datetime.strptime(date_string, "%y%m%d")
        except ValueError:
            pass

    def guess_date_from_puzzle_title(self, title):
        self.date = dateparser.parse(title.split(",", maxsplit=1)[-1].strip())

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime("%y%m%d")
        self.id = "tca" + url_formatted_date

        self.get_and_add_picker_token()

        return self.find_puzzle_url_from_id(self.id)

    def pick_filename(self, puzzle, **kwargs):
        if not self.date and self.id:
            self.guess_date_from_id(self.id)

        if not self.date and puzzle.title:
            self.guess_date_from_puzzle_title(puzzle.title)

        split_on_dashes = puzzle.title.split(" - ")
        if len(split_on_dashes) > 1:
            title = split_on_dashes[-1].strip()
        elif self.date:
            title = ""
        else:
            title = puzzle.title

        return super().pick_filename(puzzle, title=title, **kwargs)


class LATimesMiniDownloader(LATimesDownloader):
    command = "latm"
    outlet = "Los Angeles Times Mini"
    outlet_prefix = "LA Times Mini"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = "https://lat.amuselabs.com/lat/date-picker?set=latimes-mini"
        self.url_from_id = (
            "https://lat.amuselabs.com/lat/crossword?id={puzzle_id}&set=latimes-mini"
        )

    def guess_date_from_puzzle_title(self, title):
        self.date = dateparser.parse(title)

    def find_by_date(self, dt):
        self.date = dt

        url_formatted_date = dt.strftime("%Y%m%d")
        self.id = f"latimes-mini-{url_formatted_date}"

        self.get_and_add_picker_token()

        return self.find_puzzle_url_from_id(self.id)
