from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException
from datetime import datetime
import requests


class STATDownloader(AmuseLabsDownloader):
    command = "stat"
    outlet = "STAT News Mini"
    outlet_prefix = "STAT Mini"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.picker_url = "https://tbg.amuselabs.com/bostonglobe/date-picker?set=bostonglobe-stat-mini"
        self.url_from_id = "https://tbg.amuselabs.com/bostonglobe/crossword?id={puzzle_id}&set=bostonglobe-stat-mini"

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime("%Y%m%d")
        self.id = "STAT_" + url_formatted_date

        self.get_and_add_picker_token()
        
        url = self.find_puzzle_url_from_id(self.id)
        
        res = self.session.get(url)

        if (
            not res.ok
            or "The puzzle you are trying to access was not found" in res.text
        ):
            raise XWordDLException(f"No puzzle found for: {dt: %A, %-d %B, %Y}")
    
        return self.find_puzzle_url_from_id(self.id)

