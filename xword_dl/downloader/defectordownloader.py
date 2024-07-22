import datetime
import json
import jq
import re
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

    def find_by_date(self, dt):
        list_url = 'https://defector.com/category/crosswords'
        res = requests.get(list_url)
        picker_dateformat = dt.strftime('%B %-d, %Y')

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            raise XWordDLException('Unable to load {}'.format(self.picker_url))

        soup = BeautifulSoup(res.text, "html.parser")

        date_tag = soup.find('span', string=picker_dateformat) # find full date
        post_tag = date_tag.find_parent(class_=re.compile(r'^PostCard_left')) # traverse up to parent `PostCard`
        link_tag = post_tag.find('a', href=re.compile(r'/the-crossword-')) # then back down to specific puzzle anchor
        puzzle_href = link_tag['href']

        guessed_url = urllib.parse.urljoin(
            list_url,
            puzzle_href)
        return guessed_url

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
        iframe_html = jq.compile(jq_query).input_value(nextdata_json).first()

        soup_iframe = BeautifulSoup(iframe_html, "html.parser")

        iframe_tag = soup_iframe.select_one('iframe[src^="https://cdn2.amuselabs.com/pmm/crossword"]')

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
