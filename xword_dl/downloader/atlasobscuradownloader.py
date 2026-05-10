import urllib

import dateparser
import requests

from bs4 import BeautifulSoup

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException


class AtlasObscuraDownloader(AmuseLabsDownloader):
    command = "ao"
    outlet = "Atlas Obscura Crossword"
    outlet_prefix = "AtlasObscura"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = (
            "https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=atlasobscura"
        )

    @staticmethod
    def matches_url(url_components):
        return (
            "atlasobscura.com" in url_components.netloc
            and "/articles/crossword-" in url_components.path
        )

    def find_latest(self):
        index_host = "https://www.atlasobscura.com"
        index_url = f"{index_host}/categories/crosswords"
        index_res = requests.get(index_url)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_fragment = next(
            a for a in index_soup.select('a[href^="/articles/crossword-"]')
        )["href"]
        latest_absolute = urllib.parse.urljoin(index_host, latest_fragment)

        landing_page_url = latest_absolute

        return landing_page_url

    def find_solver(self, url):
        res = requests.get(url)

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
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

        pubdate = soup.select('meta[property="article:published_time"]')[0].get(
            "content"
        )
        pubdate_dt = dateparser.parse(pubdate)
        self.date = pubdate_dt

        return self.find_puzzle_url_from_id(self.id)
