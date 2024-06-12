from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .amuselabsdownloader import AmuseLabsDownloader


class XtraDownloader(AmuseLabsDownloader):
    command = "xtra"
    outlet = "Xtra Magazine"
    outlet_prefix = "Xtra"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = "https://cdn3.amuselabs.com/pmm/date-picker?set=ptpmedia-crossword"
        self.url_from_id = "https://cdn3.amuselabs.com/pmm/crossword?id={puzzle_id}&set=ptpmedia-crossword"

    @staticmethod
    def matches_url(url_components):
        return "xtramagazine.com" == url_components.netloc

    def find_solver(self, url):
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        puzzle_embed = soup.find("div", {"data-set": "ptpmedia-crossword"})
        puzzle_id = puzzle_embed["data-id"]
        return super().find_puzzle_url_from_id(puzzle_id)

    # inject into solver download to extract publish date
    def fetch_data(self, solver_url):
        xword_data = super().fetch_data(solver_url)
        if "publishTime" in xword_data:
            p_ts = xword_data["publishTime"] / 1000
            self.date = datetime.fromtimestamp(p_ts, timezone.utc)
        return xword_data
