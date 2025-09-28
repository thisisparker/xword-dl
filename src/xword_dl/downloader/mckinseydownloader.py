import urllib.parse

import dateparser

from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException


class McKinseyDownloader(AmuseLabsDownloader):
    # command = "mck"
    # Disabling as of 2025-09-27, because of anti-scraping tech used on McKinsey.com
    # For posterity: they appear to be closing inbound requests by sniffing something
    # on the SSL handshake to exclude non-browser user agents.
    # Testing with curl showed results similar to https://github.com/curl/curl/issues/18608
    outlet = "The McKinsey Crossword"
    outlet_prefix = "McKinsey"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = (
            "https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=mckinsey"
        )

    @classmethod
    def matches_url(cls, url_components):
        # return (
        #     "mckinsey.com" in url_components.netloc
        #     and "/featured-insights/the-mckinsey-crossword" in url_components.path
        # )
        return False

    def find_by_date(self, dt):
        """
        date format: month-day-year (e.g. november-15-2022)
        no leading zeros on dates (so: e.g., august-1-2023)
        crosswords are published every tuesday (as of november 2022)
        """
        month_names = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]
        url_format = f"{month_names[dt.month - 1]}-{dt.day}-{dt.year}"
        guessed_url = urllib.parse.urljoin(
            "https://www.mckinsey.com/featured-insights/the-mckinsey-crossword/",
            url_format,
        )
        return guessed_url

    def find_latest(self):
        index_url = "https://www.mckinsey.com/featured-insights/the-mckinsey-crossword/"
        try:
            index_res = self.session.get(index_url, timeout=10)
            index_res.raise_for_status()
        except RequestException:
            raise XWordDLException(f"Unable to connect to {index_url}")

        index_soup = BeautifulSoup(index_res.text, "html.parser")

        xword_selector = 'a[href^="/featured-insights/the-mckinsey-crossword/"]'
        latest_fragment = next(
            (a for a in index_soup.select(xword_selector) if a.find("div")), {}
        ).get("href")

        if not isinstance(latest_fragment, str):
            raise XWordDLException(
                "Could not get latest crossword. No crossword fragment."
            )

        latest_absolute = urllib.parse.urljoin(
            "https://www.mckinsey.com", latest_fragment
        )

        landing_page_url = latest_absolute

        return landing_page_url

    def find_solver(self, url):
        try:
            res = self.session.get(url, timeout=10)
            res.raise_for_status()
        except RequestException:
            raise XWordDLException("Unable to load {}".format(url))

        soup = BeautifulSoup(res.text, "html.parser")

        iframe_tag = soup.select('iframe[src*="amuselabs.com"]')

        if len(iframe_tag) == 0:
            raise XWordDLException("Cannot find puzzle iframe node at {}.".format(url))

        iframe_url = str(iframe_tag[0].get("src"))

        try:
            query = urllib.parse.urlparse(iframe_url).query
            query_id = urllib.parse.parse_qs(query)["id"]
            self.id = query_id[0]
        except KeyError:
            raise XWordDLException("Cannot find puzzle at {}.".format(url))

        pubdate = url.split("/")[-1].replace("-", " ").capitalize()
        pubdate_dt = dateparser.parse(pubdate)
        self.date = pubdate_dt

        return self.find_puzzle_url_from_id(self.id)
