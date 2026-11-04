import re
import dateparser

from .puzzmodownloader import PuzzmoDownloader
from ..util import join_bylines

class PuzzmoBigDownloader(PuzzmoDownloader):
    command = "sfg"
    outlet = "SFGATE California Mini"
    outlet_prefix = "SFGATE California Mini"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.finder_key += "/california"

    @classmethod
    def matches_url(cls, url_components):
        return "puzzmo.com" in url_components.netloc and bool(
            re.match(
                r"^/puzzle/\d{4}-\d{2}-\d{2}/crossword/california/?$", url_components.path
            )
        )

    def find_latest(self):
        puzzmo_date = self._get_puzzmo_date()

        return self.find_by_date(puzzmo_date) + "/california"
    
    def parse_xword(self, xw_data):
        xd_data = xw_data["puzzle"]

        # California-based clues are marked by an inline image, change to text
        xd_data = re.sub(r'\{\!.*?california bear.*?\}', ':california bear:', xd_data)
        print(xd_data)
        puzzle = self.parse_xd_format(xd_data)

        # Override xd metadata with more reliable API results
        self.date = dateparser.parse(xw_data["dailyTitle"]) or dateparser.parse(
            xw_data["dailyTitle"].split("-")[0]
        )

        # Typical 'Name' field is None for the California Mini, use formatted date from dailyTitle instead
        puzzle.title = xw_data.get("dailyTitle", "")

        puzzle.author = join_bylines(
            [a.get("publishingName") or a.get("name") for a in xw_data["authors"]]
        )

        return puzzle
