import datetime

import dateparser.search

from .amuselabsdownloader import AmuseLabsDownloader


class DailyBeastDownloader(AmuseLabsDownloader):
    command = "stat"
    outlet = "STAT Mini"
    outlet_prefix = "STAT Mini"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.picker_url = "https://tbg.amuselabs.com/bostonglobe/date-picker?set=bostonglobe-stat-mini"
        self.url_from_id = (
            "https://tbg.amuselabs.com/bostonglobe/crossword?id={puzzle_id}&set=bostonglobe-stat-mini"
        )

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime("%Y%m%d")
        self.id = "STAT_" + url_formatted_date

        self.get_and_add_picker_token()

        return self.find_puzzle_url_from_id(self.id)
