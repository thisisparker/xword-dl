import datetime
import json
import jq
import urllib

import dateparser
import requests

from bs4 import BeautifulSoup

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException

class DefectorDownloader(AmuseLabsDownloader):
    command = 'def'
    outlet = 'Defector'
    outlet_prefix = 'Defector'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn3.amuselabs.com/pmm/date-picker?set=defectormedia'
        self.url_from_id = 'https://cdn3.amuselabs.com/pmm/crossword?id={puzzle_id}&set=defectormedia'

    @staticmethod
    def matches_url(url_components):
        return ('defector.com' in url_components.netloc and '/the-crossword-' in url_components.path)

    def find_solver(self, url):
        res = requests.get(url)

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            raise XWordDLException('Unable to load {}'.format(url))

        soup_html = BeautifulSoup(res.text, "html.parser")

        nextdata_json = json.loads(soup_html.find('script',
                                                  id='__NEXT_DATA__')
                                                  .get_text())

        jq_query = '.props.pageProps.blocks[].attributes[] | select(.name == "HTMLContent").value'

        print("jq_query")
        print(jq_query)

        iframe_html = jq.compile(jq_query).input_value(nextdata_json).first()

        print("iframe_html")
        print(iframe_html)

        soup_iframe = BeautifulSoup(iframe_html, "html.parser")

        print("soup_iframe")
        print(soup_iframe)

        print("soup_iframe.find_all('iframe')")
        print(soup_iframe.find_all('iframe'))

        iframe_tag = soup_iframe.select_one('iframe[src^="https://cdn2.amuselabs.com/pmm/crossword"]')

        print("iframe_tag")
        print(iframe_tag)

        try:
            iframe_url = iframe_tag['src']
            query = urllib.parse.urlparse(iframe_url).query
            query_id = urllib.parse.parse_qs(query)['id']
            self.id = query_id[0]

        # Will hit this KeyError if there's no matching iframe
        # or if there's no 'src' attribute
        except KeyError:
            raise XWordDLException('Cannot find puzzle at {}.'.format(url))

        pubdate = jq.compile('.props.pageProps.post.date').input_value(nextdata_json).first()
        pubdate_dt = dateparser.parse(pubdate)

        self.date = pubdate_dt

        return self.find_puzzle_url_from_id(self.id)
