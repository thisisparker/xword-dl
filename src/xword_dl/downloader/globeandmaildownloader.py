# type: ignore

# Skip type checking while this downloader is inactive, but hopefully will fix someday!

import datetime
import urllib.parse
from functools import partial

from .compilerdownloader import CrosswordCompilerDownloader
from ..util import XWordDLException


class GlobeAndMailDownloader(CrosswordCompilerDownloader):
    # command = 'tgam'       # Removing because as of Jan 2025, TGAM has stopped publishing its own puzzle
    # and instead syndicates The Times on a 6 week delay.
    # Leaving this file because it's small and might be a useful reference for
    # other Compiler children.
    outlet = "The Globe And Mail (Cryptic)"
    outlet_prefix = "Globe And Mail"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.fetch_data = partial(self._fetch_data, js_encoded=True)
        self.date = None

        if "url" in kwargs and not self.date:
            self.date = self.parse_date_from_url(kwargs.get("url"))

        self.url_format = "https://www.theglobeandmail.com/puzzles-and-crosswords/cryptic-crossword/?date={url_encoded_date}"

    @classmethod
    def matches_url(cls, url_components):
        return "theglobeandmail.com" in url_components.netloc

    def parse_date_from_url(self, url):
        queries = urllib.parse.urlparse(url).query
        date = urllib.parse.parse_qs(queries).get("date", "")

        return (
            datetime.datetime.strptime(date[0], "%d%m%y")
            if date
            else self.latest_published_date(datetime.datetime.today())
        )

    def latest_published_date(self, dt):
        return dt if dt.weekday() != 6 else dt - datetime.timedelta(1)

    def find_latest(self):
        latest_date = self.latest_published_date(datetime.datetime.today())

        return self.find_by_date(latest_date)

    def find_by_date(self, dt):
        self.date = dt

        if self.date.weekday() == 6:
            raise XWordDLException("Invalid date: No Globe And Mail puzzle on Sundays.")

        return self.url_format.format(url_encoded_date=dt.strftime("%d%m%y"))

    def find_solver(self, url):
        start_date = datetime.datetime(2011, 1, 2)

        if not isinstance(self.date, datetime.datetime):
            raise XWordDLException("No solver date provided. This is a bug.")

        date_diff = self.date - start_date
        weeks_diff, extra_days = divmod(date_diff.days, 7)

        puzzle_id = 6 * weeks_diff + 8927 + 4519 + extra_days

        puzzle_url = f"https://xwords.net/xwordjs/files/html5/{puzzle_id}crp.js"

        return puzzle_url
