#!/usr/bin/env python3

import argparse
import base64
import json
import os
import sys
import urllib

import dateparser
import puz
import requests

from datetime import datetime

from bs4 import BeautifulSoup
from html2text import html2text
from unidecode import unidecode

COMODO_INTERMEDIATE_PEM = """
-----BEGIN CERTIFICATE-----
MIIGCDCCA/CgAwIBAgIQKy5u6tl1NmwUim7bo3yMBzANBgkqhkiG9w0BAQwFADCB
hTELMAkGA1UEBhMCR0IxGzAZBgNVBAgTEkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4G
A1UEBxMHU2FsZm9yZDEaMBgGA1UEChMRQ09NT0RPIENBIExpbWl0ZWQxKzApBgNV
BAMTIkNPTU9ETyBSU0EgQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkwHhcNMTQwMjEy
MDAwMDAwWhcNMjkwMjExMjM1OTU5WjCBkDELMAkGA1UEBhMCR0IxGzAZBgNVBAgT
EkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4GA1UEBxMHU2FsZm9yZDEaMBgGA1UEChMR
Q09NT0RPIENBIExpbWl0ZWQxNjA0BgNVBAMTLUNPTU9ETyBSU0EgRG9tYWluIFZh
bGlkYXRpb24gU2VjdXJlIFNlcnZlciBDQTCCASIwDQYJKoZIhvcNAQEBBQADggEP
ADCCAQoCggEBAI7CAhnhoFmk6zg1jSz9AdDTScBkxwtiBUUWOqigwAwCfx3M28Sh
bXcDow+G+eMGnD4LgYqbSRutA776S9uMIO3Vzl5ljj4Nr0zCsLdFXlIvNN5IJGS0
Qa4Al/e+Z96e0HqnU4A7fK31llVvl0cKfIWLIpeNs4TgllfQcBhglo/uLQeTnaG6
ytHNe+nEKpooIZFNb5JPJaXyejXdJtxGpdCsWTWM/06RQ1A/WZMebFEh7lgUq/51
UHg+TLAchhP6a5i84DuUHoVS3AOTJBhuyydRReZw3iVDpA3hSqXttn7IzW3uLh0n
c13cRTCAquOyQQuvvUSH2rnlG51/ruWFgqUCAwEAAaOCAWUwggFhMB8GA1UdIwQY
MBaAFLuvfgI9+qbxPISOre44mOzZMjLUMB0GA1UdDgQWBBSQr2o6lFoL2JDqElZz
30O0Oija5zAOBgNVHQ8BAf8EBAMCAYYwEgYDVR0TAQH/BAgwBgEB/wIBADAdBgNV
HSUEFjAUBggrBgEFBQcDAQYIKwYBBQUHAwIwGwYDVR0gBBQwEjAGBgRVHSAAMAgG
BmeBDAECATBMBgNVHR8ERTBDMEGgP6A9hjtodHRwOi8vY3JsLmNvbW9kb2NhLmNv
bS9DT01PRE9SU0FDZXJ0aWZpY2F0aW9uQXV0aG9yaXR5LmNybDBxBggrBgEFBQcB
AQRlMGMwOwYIKwYBBQUHMAKGL2h0dHA6Ly9jcnQuY29tb2RvY2EuY29tL0NPTU9E
T1JTQUFkZFRydXN0Q0EuY3J0MCQGCCsGAQUFBzABhhhodHRwOi8vb2NzcC5jb21v
ZG9jYS5jb20wDQYJKoZIhvcNAQEMBQADggIBAE4rdk+SHGI2ibp3wScF9BzWRJ2p
mj6q1WZmAT7qSeaiNbz69t2Vjpk1mA42GHWx3d1Qcnyu3HeIzg/3kCDKo2cuH1Z/
e+FE6kKVxF0NAVBGFfKBiVlsit2M8RKhjTpCipj4SzR7JzsItG8kO3KdY3RYPBps
P0/HEZrIqPW1N+8QRcZs2eBelSaz662jue5/DJpmNXMyYE7l3YphLG5SEXdoltMY
dVEVABt0iN3hxzgEQyjpFv3ZBdRdRydg1vs4O2xyopT4Qhrf7W8GjEXCBgCq5Ojc
2bXhc3js9iPc0d1sjhqPpepUfJa3w/5Vjo1JXvxku88+vZbrac2/4EjxYoIQ5QxG
V/Iz2tDIY+3GH5QFlkoakdH368+PUq4NCNk+qKBR6cGHdNXJ93SrLlP7u3r7l+L4
HyaPs9Kg4DdbKDsx5Q5XLVq4rXmsXiBmGqW5prU5wfWYQ//u+aen/e7KJD2AFsQX
j4rBYKEMrltDR5FL1ZoXX/nUh8HCjLfn4g8wGTeGrODcQgPmlKidrv0PJFGUzpII
0fxQ8ANAe4hZ7Q7drNJ3gjTcBpUC2JD5Leo31Rpg0Gcg19hCC0Wvgmje3WYkN5Ap
lBlGGSW4gNfL1IYoakRwJiNiqZ+Gb7+6kHDSVneFeO/qJakXzlByjAA6quPbYzSf
+AZxAeKCINT+b72x
-----END CERTIFICATE-----
"""

class AdditionalRootCertificateAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, cadata):
        self.cadata = cadata
        super().__init__()

    def init_poolmanager(self, num_pools, maxsize, block=False, *args, **kwargs):
        context = requests.packages.urllib3.util.ssl_.create_urllib3_context()
        context.load_verify_locations(cadata=self.cadata)
        kwargs["ssl_context"] = context
        self.poolmanager = requests.packages.urllib3.poolmanager.PoolManager(
            num_pools=num_pools,
            maxsize=maxsize,
            block=block,
            *args,
            **kwargs
        )

class BaseDownloader:
    def __init__(self, output=None):
        self.output = output
        if self.output and not self.output.endswith('.puz'):
            self.output = self.output + '.puz'
        self.puzfile = puz.Puzzle()

    def find_by_date(self, entered_date):
        guessed_dt = dateparser.parse(entered_date)
        if guessed_dt:
            readable_date = guessed_dt.strftime('%A, %B %d')
            print("Attempting to download a puzzle for {}".format(readable_date))
        else:
            sys.exit('Unable to determine a date from "{}".'.format(entered_date))

        self.guess_url_from_date(guessed_dt)

    def save_puz(self):
        self.puzfile.save(self.output)
        print("Puzzle downloaded and saved as {}.".format(self.output))


class AmuseLabsDownloader(BaseDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output)

    def download(self):
        # AmuseLabs has misconfigured its SSL and doesn't provide a complete
        # certificate chain. This adds the missing intermediate certificate
        # as a trust anchor.
        session = requests.Session()
        comodo_intermediate_adapter = AdditionalRootCertificateAdapter(COMODO_INTERMEDIATE_PEM)
        session.mount("https://cdn1.amuselabs.com", comodo_intermediate_adapter)
        session.mount("https://cdn2.amuselabs.com", comodo_intermediate_adapter)
        session.mount("https://cdn3.amuselabs.com", comodo_intermediate_adapter)
        res = session.get(self.url)
        rawc = next((line.strip() for line in res.text.splitlines()
                        if 'window.rawc' in line), None)

        if not rawc:
            sys.exit("Crossword puzzle not found.")

        rawc = rawc.split("'")[1]

        xword_data = json.loads(base64.b64decode(rawc))

        self.puzfile.title = xword_data.get('title', '')
        self.puzfile.author = xword_data.get('author', '')
        self.puzfile.copyright = xword_data.get('copyright', '')
        self.puzfile.width = xword_data.get('w')
        self.puzfile.height = xword_data.get('h')

        solution = ''
        fill = ''
        box = xword_data['box']
        for row_num in range(xword_data.get('h')):
            for column in box:
                cell = column[row_num]
                if cell == '\x00':
                    solution += '.'
                    fill += '.'
                else:
                    solution += cell
                    fill += '-'
        self.puzfile.solution = solution
        self.puzfile.fill = fill

        placed_words = xword_data['placedWords']
        across_words = [word for word in placed_words if word['acrossNotDown']]
        down_words = [word for word in placed_words if not word['acrossNotDown']]

        weirdass_puz_clue_sorting = sorted(placed_words, key=
                                                lambda word: (word['y'], word['x'],
                                                not word['acrossNotDown']))

        clues = [word['clue']['clue'] for word in weirdass_puz_clue_sorting]

        normalized_clues = [html2text(unidecode(clue), bodywidth=0) for clue in clues]
        self.puzfile.clues.extend(normalized_clues)

        self.save_puz()


class NewYorkerDownloader(AmuseLabsDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

    def guess_url_from_date(self, dt):
        url_format = dt.strftime('%Y/%m/%d')
        guessed_url = urllib.parse.urljoin(
                'https://www.newyorker.com/crossword/puzzles-dept/',
                url_format)
        self.find_solver(url=guessed_url)

    def find_latest(self):
        index_url = "https://www.newyorker.com/crossword/puzzles-dept"
        index_res = requests.get(index_url)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_fragment = next(a for a in index_soup.findAll('a') if a.find('h4'))['href']
        latest_absolute = urllib.parse.urljoin('https://www.newyorker.com',
                                                latest_fragment)

        self.find_solver(url=latest_absolute)

    def find_solver(self, url):
        res = requests.get(url)

        if res.status_code == 404:
            sys.exit('Unable to find a puzzle at {}'.format(url))
 
        soup = BeautifulSoup(res.text, "html.parser")

        self.url = soup.find('iframe', attrs={'id':'crossword'})['data-src']

        if not self.output:
            path = urllib.parse.urlsplit(url).path
            date_frags = path.split('/')[-3:]
            date_mash = ''.join(date_frags)
            self.output = ''.join(['tny', date_mash, '.puz'])


class NewsdayDownloader(AmuseLabsDownloader):
    def __init__(self, output=None, **kwargs):
        super().__init__(output, **kwargs)

    def guess_url_from_date(self, dt):
        url_format = dt.strftime('%Y%m%d')
        guessed_url = ''.join([
            'https://cdn2.amuselabs.com/pmm/crossword?id=Creators_WEB_',
            url_format, '&set=creatorsweb'])
        if not self.output:
            self.output = ''.join(['nd', url_format, '.puz'])
        self.find_solver(url=guessed_url)

    def find_latest(self):
        datepicker_url = "https://cdn2.amuselabs.com/pmm/date-picker?set=creatorsweb"
        res = requests.get(datepicker_url)
        soup = BeautifulSoup(res.text, 'html.parser')

        data_id = soup.find('li', attrs={'class':'tile'})['data-id']

        if not self.output:
            self.output = 'nd' + data_id.split('_')[-1] + '.puz'

        url = "https://cdn2.amuselabs.com/pmm/crossword?id={}&set=creatorsweb".format(
                data_id)

        self.find_solver(url=url)

    def find_solver(self, url):
        self.url = url


def main():
    parser = argparse.ArgumentParser()

    extractor_parent = argparse.ArgumentParser(add_help=False)
    date_selector = extractor_parent.add_mutually_exclusive_group()
    date_selector.add_argument('-l', '--latest',
                            help="""
                                select most recent available puzzle
                                (this is the default behavior)""",
                            action='store_true',
                            default=True)
    date_selector.add_argument('-d', '--date', nargs='*',
                            help='a specific puzzle date to select')

    extractor_parent.add_argument('-o', '--output',
                            help="""
                            the filename for the saved puzzle
                            (if not provided, a default value will be used)""",
                            default=None)

    extractor_url_parent = argparse.ArgumentParser(add_help=False)
    extractor_url_parent.add_argument('-u', '--url',
                            help='a specific puzzle URL to download')

    subparsers = parser.add_subparsers(title='sites',
                            description='Supported puzzle sources',
                            dest='subparser_name')

    newyorker_parser = subparsers.add_parser('tny',
                            aliases=['newyorker', 'nyer'],
                            parents=[extractor_parent,
                                     extractor_url_parent],
                            help="download a New Yorker puzzle")
    newyorker_parser.set_defaults(downloader_class=NewYorkerDownloader)

    newsday_parser = subparsers.add_parser('nd',
                            aliases=['newsday'],
                            parents=[extractor_parent],
                            help="download a Newsday puzzle")
    newsday_parser.set_defaults(downloader_class=NewsdayDownloader)

    parser.add_argument('--url', help='URL of puzzle to download')

    args = parser.parse_args()

    dl = args.downloader_class(output=args.output)

    if args.date:
        entered_date = ' '.join(args.date)
        dl.find_by_date(entered_date)

    elif args.url:
        dl.find_solver(args.url)

    elif args.latest:
        dl.find_latest()

    dl.download()


if __name__ == '__main__':
    main()
