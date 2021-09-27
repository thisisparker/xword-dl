#!/usr/bin/env python3

import argparse
import base64
import datetime
import inspect
import json
import os
import sys
import textwrap
import time
import urllib

import dateparser
import puz
import requests
import yaml

from bs4 import BeautifulSoup
from html2text import html2text
from unidecode import unidecode

__version__ = '2021.9.26rc1'
CONFIG_PATH = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
CONFIG_PATH = os.path.join(CONFIG_PATH, 'xword-dl/xword-dl.yaml')

if not os.path.exists(CONFIG_PATH):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    open(CONFIG_PATH, 'a').close()


def by_keyword(keyword, **kwargs):
    keyword_dict = {d[1].command: d[1] for d in get_supported_outlets()}
    selected_downloader = keyword_dict.get(keyword, None)

    if selected_downloader:
        dl = selected_downloader(**kwargs)
    else:
        raise ValueError('Keyword {} not recognized.'.format(keyword))

    date = kwargs.get('date')

    if not date:
        puzzle_url = dl.find_latest()
    elif date and hasattr(dl, 'find_by_date'):
        parsed_date = parse_date_or_exit(date)
        dl.date = parsed_date
        puzzle_url = dl.find_by_date(parsed_date)
    else:
        raise ValueError(
            'Selection by date not available for {}.'.format(dl.outlet))

    puzzle = dl.download(puzzle_url)

    filename = kwargs.get('filename') or dl.pick_filename(puzzle)

    return puzzle, filename


def by_url(url, filename=None):
    netloc = urllib.parse.urlparse(url).netloc

    supported_sites = [('wsj.com', WSJDownloader),
                       ('newyorker.com', NewYorkerDownloader),
                       ('amuselabs.com', AmuseLabsDownloader)]

    dl = None

    supported_downloader = next((site[1] for site in supported_sites
                                 if site[0] in netloc), None)

    if supported_downloader:
        dl = supported_downloader()
        puzzle_url = url
    else:
        amuse_url = None
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')

        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if 'amuselabs.com' in src:
                amuse_url = src
                break

        if amuse_url:
            dl = AmuseLabsDownloader()
            puzzle_url = amuse_url

    if dl:
        puzzle = dl.download(puzzle_url)
    else:
        raise ValueError('Unable to find a puzzle at {}.'.format(url))

    filename = filename or dl.pick_filename(puzzle)

    return puzzle, filename


def get_supported_outlets():
    all_classes = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    downloaders = [d for d in all_classes if issubclass(d[1], BaseDownloader)
                   and hasattr(d[1], 'command')]

    return downloaders


def get_help_text_formatted_list():
    text = ''
    for d in sorted(get_supported_outlets(), key=lambda x: x[1].outlet.lower()):
        text += '{:<5} {}\n'.format(d[1].command, d[1].outlet)

    return text


def save_puzzle(puzzle, filename):
    if not os.path.exists(filename):
        puzzle.save(filename)
        msg = ("Puzzle downloaded and saved as {}.".format(filename)
               if sys.stdout.isatty()
               else filename)
        print(msg)
    else:
        print("Not saving: a file named {} already exists.".format(filename),
              file=sys.stderr)


def remove_invalid_chars_from_filename(filename):
    invalid_chars = '<>"/\|?*'

    for char in invalid_chars:
        filename = filename.replace(char, '')

    return filename


def parse_date(entered_date):
    return dateparser.parse(entered_date, settings={'PREFER_DATES_FROM':'past'})


def parse_date_or_exit(entered_date):
    guessed_dt = parse_date(entered_date)

    if not guessed_dt:
        raise ValueError(
            'Unable to determine a date from "{}".'.format(entered_date))

    return guessed_dt


def update_config_file(heading, new_values_dict):
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f) or {}

    if heading not in config:
        config[heading] = {}

    config[heading].update(new_values_dict)

    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f)


class BaseDownloader:
    outlet = None
    outlet_prefix = None

    def __init__(self, **kwargs):
        self.date = None

        self.settings = {}

        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f) or {}

        self.settings.update(config.get('general', {}))
        self.settings.update(config.get(self.command, {}))
        self.settings.update(kwargs)

    def pick_filename(self, puzzle, **kwargs):
        title = kwargs.get('title', puzzle.title)
        date = kwargs.get('date', self.date)

        date = date.strftime('%Y%m%d') if date else None

        filename_components = [component for component in
                               [self.outlet_prefix or puzzle.author,
                                date,
                                title] if component]

        filename = " - ".join(filename_components) + '.puz'
        filename = remove_invalid_chars_from_filename(filename)

        return filename

    def find_solver(self, url):
        """Given a URL for a puzzle, returns the essential 'solver' URL.

        This is implemented in subclasses, and in instances where there is no
        separate 'landing page' URL for a puzzle, it may be a very transparent
        pass-through.
        """
        raise NotImplementedError

    def fetch_data(self, solver_url):
        """Given a URL from the find_solver function, return JSON crossword data

        This is implemented in subclasses and the returned data will not be
        standardized until later.
        """
        raise NotImplementedError

    def parse_xword(self, xword_data):
        """Given a blob of crossword data, parse and stuff into puz format.

        This method is implemented in subclasses based on the differences in
        the data format in situ.
        """
        raise NotImplementedError

    def download(self, url):
        """Download, parse, and return a puzzle at a given URL."""

        solver_url = self.find_solver(url)
        xword_data = self.fetch_data(solver_url)
        puzzle = self.parse_xword(xword_data)

        return puzzle


class AmuseLabsDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        super().__init__()

        self.id = None

    def find_latest(self):
        res = requests.get(self.picker_url)
        soup = BeautifulSoup(res.text, 'html.parser')
        puzzles = soup.find('div', attrs={'class': 'puzzles'})
        puzzle_ids = puzzles.findAll('div', attrs={'class': 'tile'})
        if not puzzle_ids:
            puzzle_ids = puzzles.findAll('li', attrs={'class': 'tile'})
        self.id = puzzle_ids[0].get('data-id', '')

        self.get_and_add_picker_token(res.text)

        return self.find_puzzle_url_from_id(self.id)

    def get_and_add_picker_token(self, picker_source=None):
        if not picker_source:
            res = requests.get(self.picker_url)
            picker_source = res.text

        rawsps = next((line.strip() for line in picker_source.splitlines()
                     if 'pickerParams.rawsps' in line), None)

        if rawsps:
            rawsps = rawsps.split("'")[1]
            picker_params = json.loads(base64.b64decode(rawsps).decode("utf-8"))
            token = picker_params.get('pickerToken', None)
            if token:
                self.url_from_id += '&pickerToken=' + token

    def find_puzzle_url_from_id(self, puzzle_id):
        return self.url_from_id.format(puzzle_id=puzzle_id)

    def guess_date_from_id(self, puzzle_id):
        """Subclass method to set date from an AmuseLabs id, if possible.

        If a date can be derived from the id, it is set as a datetime object in
        the date property of the downloader object. This method is called when
        picking a filename for AmuseLabs-type puzzles.
        """

        pass

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url):
        res = requests.get(solver_url)
        rawc = next((line.strip() for line in res.text.splitlines()
                     if 'window.rawc' in line), None)

        if not rawc:
            raise Exception("Crossword puzzle not found.")

        rawc = rawc.split("'")[1]

        xword_data = json.loads(base64.b64decode(rawc).decode("utf-8"))

        return xword_data

    def parse_xword(self, xword_data):
        puzzle = puz.Puzzle()
        puzzle.title = unidecode(xword_data.get('title', '').strip())
        puzzle.author = xword_data.get('author', '').strip()
        puzzle.copyright = xword_data.get('copyright', '').strip()
        puzzle.width = xword_data.get('w')
        puzzle.height = xword_data.get('h')

        markup_data = xword_data.get('cellInfos', '')

        circled = [(square['x'], square['y']) for square in markup_data
                   if square['isCircled']]

        solution = ''
        fill = ''
        markup = b''
        rebus_board = []
        rebus_index = 0
        rebus_table = ''

        box = xword_data['box']
        for row_num in range(xword_data.get('h')):
            for col_num, column in enumerate(box):
                cell = column[row_num]
                if cell == '\x00':
                    solution += '.'
                    fill += '.'
                    markup += b'\x00'
                    rebus_board.append(0)
                elif len(cell) == 1:
                    solution += cell
                    fill += '-'
                    markup += b'\x80' if (col_num,
                                          row_num) in circled else b'\x00'
                    rebus_board.append(0)
                else:
                    solution += cell[0]
                    fill += '-'
                    rebus_board.append(rebus_index + 1)
                    rebus_table += '{:2d}:{};'.format(rebus_index, cell)
                    rebus_index += 1

        puzzle.solution = solution
        puzzle.fill = fill

        placed_words = xword_data['placedWords']
        across_words = [word for word in placed_words if word['acrossNotDown']]
        down_words = [
            word for word in placed_words if not word['acrossNotDown']]

        weirdass_puz_clue_sorting = sorted(placed_words, key=lambda word: (word['y'], word['x'],
                                                                           not word['acrossNotDown']))

        clues = [word['clue']['clue'] for word in weirdass_puz_clue_sorting]

        normalized_clues = [html2text(unidecode(clue), bodywidth=0)
                            for clue in clues]
        puzzle.clues.extend(normalized_clues)

        has_markup = b'\x80' in markup
        has_rebus = any(rebus_board)

        if has_markup:
            puzzle.extensions[b'GEXT'] = markup
            puzzle._extensions_order.append(b'GEXT')
            puzzle.markup()

        if has_rebus:
            puzzle.extensions[b'GRBS'] = bytes(rebus_board)
            puzzle.extensions[b'RTBL'] = rebus_table.encode(puz.ENCODING)
            puzzle._extensions_order.extend([b'GRBS', b'RTBL'])
            puzzle.rebus()

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        if not self.date and self.id:
            self.guess_date_from_id(self.id)
        return super().pick_filename(puzzle, **kwargs)


class WaPoDownloader(AmuseLabsDownloader):
    command = 'wp'
    outlet = 'Washington Post'
    outlet_prefix = 'WaPo'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn1.amuselabs.com/wapo/wp-picker?set=wapo-eb'
        self.url_from_id = 'https://cdn1.amuselabs.com/wapo/crossword?id={puzzle_id}&set=wapo-eb'

    def guess_date_from_id(self, puzzle_id):
        self.date = datetime.datetime.strptime('20'
                                               + puzzle_id.split('_')[1], '%Y%m%d')

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%y%m%d')
        self.id = 'ebirnholz_' + url_formatted_date

        return self.find_puzzle_url_from_id(self.id)


class AtlanticDownloader(AmuseLabsDownloader):
    command = 'atl'
    outlet = 'Atlantic'
    outlet_prefix = 'Atlantic'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn3.amuselabs.com/atlantic/date-picker?set=atlantic'
        self.url_from_id = 'https://cdn3.amuselabs.com/atlantic/crossword?id={puzzle_id}&set=atlantic'

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%Y%m%d')
        self.id = 'atlantic_' + url_formatted_date

        return self.find_puzzle_url_from_id(self.id)


class NewsdayDownloader(AmuseLabsDownloader):
    command = 'nd'
    outlet = 'Newsday'
    outlet_prefix = 'Newsday'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn2.amuselabs.com/pmm/date-picker?set=creatorsweb'
        self.url_from_id = 'https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=creatorsweb'

    def guess_date_from_id(self, puzzle_id):
        date_string = puzzle_id.split('_')[2]
        self.date = datetime.datetime.strptime(date_string, '%Y%m%d')

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%Y%m%d')
        self.id = 'Creators_WEB_' + url_formatted_date

        return self.find_puzzle_url_from_id(self.id)


class LATimesDownloader(AmuseLabsDownloader):
    command = 'lat'
    outlet = 'Los Angeles Times'
    outlet_prefix = 'LA Times'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn4.amuselabs.com/lat/date-picker?set=latimes'
        self.url_from_id = 'https://cdn4.amuselabs.com/lat/crossword?id={puzzle_id}&set=latimes'

    def guess_date_from_id(self, puzzle_id):
        date_string = ''.join([char for char in puzzle_id if char.isdigit()])
        self.date = datetime.datetime.strptime(date_string, '%y%m%d')

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%y%m%d')
        self.id = 'tca' + url_formatted_date

        self.get_and_add_picker_token()

        return self.find_puzzle_url_from_id(self.id)

    def pick_filename(self, puzzle, **kwargs):
        split_on_dashes = puzzle.title.split(' - ')
        if len(split_on_dashes) > 1:
            use_title = split_on_dashes[-1].strip()
        else:
            use_title = ''

        return super().pick_filename(puzzle, title=use_title)


class NewYorkerDownloader(AmuseLabsDownloader):
    command = 'tny'
    outlet = 'New Yorker'
    outlet_prefix = 'New Yorker'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = 'https://cdn3.amuselabs.com/tny/crossword?id={puzzle_id}&set=tny-weekly'

    def guess_date_from_id(self, puzzle_id):
        self.date = datetime.datetime.strftime(puzzle_id.split('_')[-1])

    def find_by_date(self, dt):
        url_format = dt.strftime('%Y/%m/%d')
        guessed_url = urllib.parse.urljoin(
            'https://www.newyorker.com/puzzles-and-games-dept/crossword/',
            url_format)
        return guessed_url

    def find_latest(self):
        index_url = "https://www.newyorker.com/puzzles-and-games-dept/crossword"
        index_res = requests.get(index_url)
        index_soup = BeautifulSoup(index_res.text, "html.parser")

        latest_fragment = next(a for a in index_soup.findAll('a')
                               if a.find('h4'))['href']
        latest_absolute = urllib.parse.urljoin('https://www.newyorker.com',
                                               latest_fragment)

        landing_page_url = latest_absolute

        return landing_page_url

    def find_solver(self, url):
        res = requests.get(url)

        if res.status_code == 404:
            raise ConnectionError('Unable to find a puzzle at {}'.format(url))

        soup = BeautifulSoup(res.text, "html.parser")

        script_tag = soup.find('script', attrs={'type': 'application/ld+json'})

        json_data = json.loads(script_tag.contents[0])

        iframe_url = json_data[0]['articleBody'].strip().strip('[]')[
            len('#crossword: '):]

        try:
            query = urllib.parse.urlparse(iframe_url).query
            query_id = urllib.parse.parse_qs(query)['id']
            self.id = query_id[0]
        except KeyError:
            raise ValueError('Cannot find puzzle at {}.'.format(url))

        pubdate = soup.find('time').get_text()
        pubdate_dt = dateparser.parse(pubdate)

        self.date = pubdate_dt

        return self.find_puzzle_url_from_id(self.id)

    def pick_filename(self, puzzle, **kwargs):
        try:
            supra, main = puzzle.title.split(':')
            if supra == 'The Crossword' and dateparser.parse(main):
                title = ''
            else:
                title = main.strip()
        except ValueError:
            title = puzzle.title
        return super().pick_filename(puzzle, title=title)


class VoxDownloader(AmuseLabsDownloader):
    command = 'vox'
    outlet = 'Vox'
    outlet_prefix = 'Vox'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn3.amuselabs.com/vox/date-picker?set=vox'
        self.url_from_id = 'https://cdn3.amuselabs.com/vox/crossword?id={puzzle_id}&set=vox'

    def guess_date_from_id(self, puzzle_id):
        self.date = datetime.datetime.strptime(puzzle_id.split('_')[1],
                                               '%Y%m%d')

class DailyBeastDownloader(AmuseLabsDownloader):
    command = 'db'
    outlet = 'Daily Beast'
    outlet_prefix = 'Daily Beast'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn3.amuselabs.com/tdb/date-picker?set=tdb'
        self.url_from_id = 'https://cdn3.amuselabs.com/tdb/crossword?id={puzzle_id}&set=tdb'

    def parse_xword(self, xword_data):
        puzzle = super().parse_xword(xword_data)

        # Daily Beast puzzle IDs, unusually for AmuseLabs puzzles, don't include
        # the date. This pulls it out of the puzzle title, which will work
        # as long as that stays consistent.

        datestring = ', '.join([c.strip()
                                for c in puzzle.title.split(',', )[-2:]])
        self.date = datetime.datetime.strptime(datestring, '%b %d, %Y')

        return puzzle


class WSJDownloader(BaseDownloader):
    command = 'wsj'
    outlet = 'Wall Street Journal'
    outlet_prefix = 'WSJ'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.headers = {'User-Agent': 'xword-dl'}

    def find_latest(self):
        url = "https://www.wsj.com/news/puzzle"

        res = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(res.text, 'html.parser')

        for article in soup.find_all('article'):
            if 'crossword' in article.find('span').get_text().lower():
                latest_url = article.find('a').get('href')
                break
        else:
            raise ValueError('Unable to find latest puzzle.')

        return latest_url

    def find_solver(self, url):
        if '/puzzles/crossword/' in url:
            return url
        else:
            res = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            try:
                puzzle_link = soup.find('iframe').get('src')
            except AttributeError:
                raise ValueError('Cannot find puzzle at {}.'.format(url))
            return self.find_solver(puzzle_link)

    def fetch_data(self, solver_url):
        data_url = solver_url.replace('?embed=1', 'data.json')
        return requests.get(data_url, headers=self.headers).json()['data']

    def parse_xword(self, xword_data):
        xword_metadata = xword_data.get('copy', '')
        xword_data = xword_data.get('grid', '')

        date_string = xword_metadata.get('date-publish-analytics').split()[0]

        self.date = datetime.datetime.strptime(date_string, '%Y/%m/%d')

        fetched = {}
        for field in ['title', 'byline', 'publisher']:
            fetched[field] = html2text(xword_metadata.get(field, ''),
                                       bodywidth=0).strip()

        puzzle = puz.Puzzle()
        puzzle.title = fetched.get('title')
        puzzle.author = fetched.get('byline')
        puzzle.copyright = fetched.get('publisher')
        puzzle.width = int(xword_metadata.get('gridsize').get('cols'))
        puzzle.height = int(xword_metadata.get('gridsize').get('rows'))

        solution = ''
        fill = ''
        markup = b''

        for row in xword_data:
            for cell in row:
                if not cell['Letter']:
                    fill += '.'
                    solution += '.'
                    markup += b'\x00'
                else:
                    fill += '-'
                    solution += cell['Letter']
                    markup += (b'\x80' if (cell.get('style', '')
                                           and cell['style']['shapebg']
                                           == 'circle')
                               else b'\x00')

        puzzle.fill = fill
        puzzle.solution = solution

        clue_list = xword_metadata['clues'][0]['clues'] + \
            xword_metadata['clues'][1]['clues']
        sorted_clue_list = sorted(clue_list, key=lambda x: int(x['number']))

        clues = [clue['clue'] for clue in sorted_clue_list]
        normalized_clues = [
            html2text(unidecode(clue), bodywidth=0) for clue in clues]

        puzzle.clues = normalized_clues

        has_markup = b'\x80' in markup

        if has_markup:
            puzzle.extensions[b'GEXT'] = markup
            puzzle._extensions_order.append(b'GEXT')
            puzzle.markup()

        return puzzle


class AMUniversalDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        super().__init__()
        self.url_blob = None

    def find_by_date(self, dt):
        self.date = dt

        url_format = dt.strftime('%Y-%m-%d')
        return self.url_blob + url_format + '/data.json'

    def find_latest(self):
        dt = datetime.datetime.today()
        return self.find_by_date(dt)

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url):
        attempts = 3
        while attempts:
            try:
                res = requests.get(solver_url)
                xword_data = res.json()
                break
            except json.JSONDecodeError:
                print('Unable to download puzzle data. Trying again.',
                      file=sys.stderr)
                time.sleep(2)
                attempts -= 1
        else:
            raise Exception('Unable to download puzzle data.')
        return xword_data

    def process_clues(self, clue_list):
        """Return clue list without any end markers"""

        return clue_list

    def parse_xword(self, xword_data):
        fetched = {}
        for field in ['Title', 'Author', 'Editor', 'Copryight']:
            fetched[field] = urllib.parse.unquote(
                xword_data.get(field, '')).strip()

        puzzle = puz.Puzzle()
        puzzle.title = fetched.get('Title', '')
        puzzle.author = ''.join([fetched.get('Author', ''),
                                 ' / Ed. ',
                                 fetched.get('Editor', '')])
        puzzle.copyright = fetched.get('Copyright', '')
        puzzle.width = int(xword_data.get('Width'))
        puzzle.height = int(xword_data.get('Height'))

        solution = xword_data.get('AllAnswer').replace('-', '.')

        puzzle.solution = solution

        fill = ''
        for letter in solution:
            if letter == '.':
                fill += '.'
            else:
                fill += '-'
        puzzle.fill = fill

        across_clues = xword_data['AcrossClue'].splitlines()
        down_clues = self.process_clues(xword_data['DownClue'].splitlines())

        clues_list = across_clues + down_clues

        clues_list_stripped = [{'number': clue.split('|')[0],
                                'clue':clue.split('|')[1]} for clue in clues_list]

        clues_sorted = sorted(clues_list_stripped, key=lambda x: x['number'])

        clues = [clue['clue'] for clue in clues_sorted]

        puzzle.clues = clues

        return puzzle


class USATodayDownloader(AMUniversalDownloader):
    command = 'usa'
    outlet = 'USA Today'
    outlet_prefix = 'USA Today'

    def __init__(self, **kwargs):
        super().__init__()

        self.url_blob = 'https://gamedata.services.amuniversal.com/c/uupuz/l/U2FsdGVkX18CR3EauHsCV8JgqcLh1ptpjBeQ%2Bnjkzhu8zNO00WYK6b%2BaiZHnKcAD%0A9vwtmWJp2uHE9XU1bRw2gA%3D%3D/g/usaon/d/'

    def process_clues(self, clue_list):
        """Remove the end marker found in USA Today puzzle JSON."""

        return clue_list[:-1]


class UniversalDownloader(AMUniversalDownloader):
    command = 'uni'
    outlet = 'Universal'
    outlet_prefix = 'Universal'

    def __init__(self, **kwargs):
        super().__init__()

        self.url_blob = 'https://embed.universaluclick.com/c/uucom/l/U2FsdGVkX18YuMv20%2B8cekf85%2Friz1H%2FzlWW4bn0cizt8yclLsp7UYv34S77X0aX%0Axa513fPTc5RoN2wa0h4ED9QWuBURjkqWgHEZey0WFL8%3D/g/fcx/d/'


class NewYorkTimesDownloader(BaseDownloader):
    command = 'nyt'
    outlet = 'New York Times'
    outlet_prefix = 'NY Times'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = 'https://www.nytimes.com/svc/crosswords/v2/puzzle/{}.json'

        self.headers = {}
        self.cookies = {}

        username = self.settings.get('username')
        password = self.settings.get('password')

        if username and password:
            nyts_token = self.authenticate(username, password)
            update_config_file('nyt', {'NYT-S': nyts_token})
        else:
            nyts_token = self.settings.get('NYT-S')

        if not nyts_token:
            raise ValueError('No credentials provided or stored. Try providing a username and password with the --username and --password flags.')
        else:
            self.cookies.update({'NYT-S': nyts_token})

    def authenticate(self, username, password):
        """Given a NYT username and password, returns the NYT-S cookie value"""
        res = requests.post('https://myaccount.nytimes.com/svc/ios/v2/login',
                            data={'login': username, 'password': password},
                            headers={'User-Agent': 'Mozilla/5.0',
                                     'client-id': 'ios.crosswords'})

        res.raise_for_status()

        nyts_token = ''

        for cookie in res.json()['data']['cookies']:
            if cookie['name'] == 'NYT-S':
                nyts_token = cookie['cipheredValue']

        if nyts_token:
            return nyts_token
        else:
            raise ValueError('NYT-S cookie not found.')

    def find_latest(self):
        oracle = "https://www.nytimes.com/svc/crosswords/v2/oracle/daily.json"

        res = requests.get(oracle)
        puzzle_id = res.json()['results']['current']['puzzle_id']

        url = self.url_from_id.format(puzzle_id)

        return url

    def find_by_date(self, dt):
        lookup_url = 'https://www.nytimes.com/svc/crosswords/v3/puzzles.json?status=published&order=published&sort=asc&pad=false&print_date_start={}&print_date_end={}&publish_type=daily'

        formatted_date = dt.strftime('%Y-%m-%d')

        res = requests.get(lookup_url.format(formatted_date, formatted_date))

        puzzle_id = res.json()['results'][0]['puzzle_id']

        return self.url_from_id.format(puzzle_id)

    def find_solver(self, url):
        return url

    def fetch_data(self, solver_url):
        res = requests.get(solver_url, cookies=self.cookies)
        res.raise_for_status()

        return res.json()['results'][0]

    def parse_xword(self, xword_data):
        puzzle = puz.Puzzle()

        metadata = xword_data.get('puzzle_meta')
        puzzle.author = metadata.get('author').strip()
        puzzle.copyright = metadata.get('copyright').strip()
        puzzle.height = metadata.get('height')
        puzzle.width = metadata.get('width')

        if metadata.get('notes'):
            puzzle.notes = metadata.get('notes')[0]['txt'].strip()

        date_string = metadata.get('printDate')

        self.date = datetime.datetime.strptime(date_string, '%Y-%m-%d')

        puzzle.title = metadata.get('title') or self.date.strftime(
                '%A, %B %-m, %Y')

        puzzle_data = xword_data['puzzle_data']

        solution = ''
        fill = ''
        markup = b''
        rebus_board = []
        rebus_index = 0
        rebus_table = ''

        for idx, square in enumerate(puzzle_data['answers']):
            if not square:
                solution += '.'
                fill += '.'
                rebus_board.append(0)
            elif len(square) == 1:
                solution += square
                fill += '-'
                rebus_board.append(0)
            else:
                solution += square[0][0]
                fill += '-'
                rebus_board.append(rebus_index + 1)
                rebus_table += '{:2d}:{};'.format(rebus_index, square[0])
                rebus_index += 1

            markup += (b'\x80' if puzzle_data['layout'][idx] == 3 else b'\x00')

        puzzle.solution = solution
        puzzle.fill = fill

        clue_list = puzzle_data['clues']['A'] + puzzle_data['clues']['D']
        clue_list.sort(key=lambda c: c['clueNum'])

        puzzle.clues = [unidecode(c['value']).strip() for c in clue_list]

        if b'\x80' in markup:
            puzzle.extensions[b'GEXT'] = markup
            puzzle._extensions_order.append(b'GEXT')
            puzzle.markup()

        if any(rebus_board):
            puzzle.extensions[b'GRBS'] = bytes(rebus_board)
            puzzle.extensions[b'RTBL'] = rebus_table.encode(puz.ENCODING)
            puzzle._extensions_order.extend([b'GRBS', b'RTBL'])
            puzzle.rebus()

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        if puzzle.title == self.date.strftime('%A, %B %-m, %Y'):
            title = ''
        else:
            title = puzzle.title

        return super().pick_filename(puzzle, title=title)


def main():
    parser = argparse.ArgumentParser(prog='xword-dl',
                                     description=textwrap.dedent("""\
        xword-dl is a tool to download online crossword puzzles and save them
        locally as AcrossLite-compatible .puz files. It works with supported
        sites, a list of which can be found below.

        By default, xword-dl will download the most recent puzzle available at
        a given outlet, and some outlets support searching by date.
        """),
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-v', '--version',
                        action='version', version=__version__)

    parser.add_argument('source', nargs="?", help=textwrap.dedent("""\
                                specify a URL or a keyword to select an
                                outlet from which to download a puzzle.

                                Supported outlet keywords are:\n""") +
                        "{}".format(get_help_text_formatted_list()))

    selector = parser.add_mutually_exclusive_group()

    selector.add_argument('-l', '--latest',
                          help=textwrap.dedent("""\
                                select most recent available puzzle
                                (this is the default behavior)"""),
                          action='store_true',
                          default=True)

    selector.add_argument('-d', '--date', nargs='*', metavar='',
                          help='a specific puzzle date to select',
                          default=[])

    parser.add_argument('-a', '--authenticate',
                        help=textwrap.dedent("""\
                            if used with the username and password flags,
                            stores an authenticated New York Times cookie
                            without downloading a puzzle"""),
                        action='store_true',
                        default=False)

    parser.add_argument('-u', '--username',
                        help=textwrap.dedent("""\
                            username for a site that requires credentials
                            (currently only the New York Times)"""),
                        default=None)

    parser.add_argument('-p', '--password',
                        help=textwrap.dedent("""\
                            password for a site that requires credentials
                            (currently only the New York Times)"""),
                        default=None)

    parser.add_argument('-o', '--output',
                        help=textwrap.dedent("""\
                            the filename for the saved puzzle
                            (if not provided, a default value will be used)"""),
                        default=None)


    args = parser.parse_args()
    if args.authenticate:
        if not (args.username and args.password):
            sys.exit('Authentication command must include username and password.')
        try:
            dl = NewYorkTimesDownloader(username=args.username, password=args.password)
            sys.exit('Authentication successful.')
        except Exception as e:
            sys.exit(' '.join(['Authentication failed:', str(e)]))

    if not args.source:
        sys.exit(parser.print_help())

    options = {}
    if args.username:
        options['username'] = args.username
    if args.password:
        options['password'] = args.password
    if args.output:
        options['filename'] = args.output
    if args.date:
        options['date'] = ''.join(args.date)

    try:
        if args.source.startswith('http'):
            puzzle, filename = by_url(args.source,
                                      filename=args.output)
        else:
            puzzle, filename = by_keyword(args.source, **options)
    except ValueError as e:
        sys.exit(e)

    if not filename.endswith('.puz'):
        filename = filename + '.puz'

    save_puzzle(puzzle, filename)


if __name__ == '__main__':
    main()
