import datetime
import json
import urllib

import dateparser
import requests

from bs4 import BeautifulSoup

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException, remove_invalid_chars_from_filename

class NewYorkerDownloader(AmuseLabsDownloader):
    command = 'tny'
    outlet = 'New Yorker'
    outlet_prefix = 'New Yorker'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_from_id = 'https://cdn3.amuselabs.com/tny/crossword?id={puzzle_id}&set=tny-weekly'

        self.theme_title = ''

    @staticmethod
    def matches_url(url_components):
        return ('newyorker.com' in url_components.netloc and '/puzzles-and-games-dept/crossword' in url_components.path)

    def guess_date_from_id(self, puzzle_id):
        self.date = datetime.datetime.strftime(puzzle_id.split('_')[-1])

    def find_by_date(self, dt):
        url_format = dt.strftime('%Y/%m/%d')
        guessed_url = urllib.parse.urljoin(
            'https://www.newyorker.com/puzzles-and-games-dept/crossword/',
            url_format)
        return guessed_url

    def find_latest(self, search_string='/crossword/'):
        url = "https://www.newyorker.com/puzzles-and-games-dept/crossword"
        res = self.session.get(url)
        soup = BeautifulSoup(res.text, "html.parser")

        puzzle_list = json.loads(soup.find('script',
                                           attrs={'type':'application/ld+json'})
                                           .get_text()).get('itemListElement',{})
        latest_url = next((item for item in puzzle_list
                            if search_string in item.get('url', '')),
                          {}).get('url')

        if not latest_url:
            raise XWordDLException('Could not identify the latest puzzle at {}'.format(url))

        return latest_url

    def find_solver(self, url):
        res = requests.get(url)

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError:
            raise XWordDLException('Unable to load {}'.format(url))

        soup = BeautifulSoup(res.text, "html.parser")

        iframe_tag = soup.find('iframe', id='crossword')

        try:
            iframe_url = iframe_tag['data-src']
            query = urllib.parse.urlparse(iframe_url).query
            query_id = urllib.parse.parse_qs(query)['id']
            self.id = query_id[0]

        # Will hit this KeyError if there's no matching iframe
        # or if there's no 'id' query string
        except KeyError:
            raise XWordDLException('Cannot find puzzle at {}.'.format(url))

        pubdate = soup.find('time').get_text()
        pubdate_dt = dateparser.parse(pubdate)

        self.date = pubdate_dt

        theme_supra = "Today’s theme: "
        desc = soup.find('meta',attrs={'property':
                                       'og:description'}).get('content', '')
        if desc.startswith(theme_supra):
            self.theme_title = desc[len(theme_supra):].rstrip('.')

        return self.find_puzzle_url_from_id(self.id)
        
    def parse_xword(self, xword_data):
        puzzle = super().parse_xword(xword_data)

        if '<' in puzzle.title:
            puzzle.title = puzzle.title.split('<')[0]

        if self.theme_title:
            puzzle.title += f' - {self.theme_title}'

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        try:
            supra, main = puzzle.title.split(':', 1)
            if self.theme_title:
                main = main.rsplit(' - ')[0]
            if supra == 'The Crossword' and dateparser.parse(main):
                title = self.theme_title
            else:
                title = main.strip()
        except XWordDLException:
            title = puzzle.title
        return super().pick_filename(puzzle, title=title, **kwargs)

class NewYorkerMiniDownloader(NewYorkerDownloader):
    command = 'tnym'
    outlet = 'New Yorker Mini'
    outlet_prefix = 'New Yorker Mini'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.url_from_id is inherited and correct:
        # 'https://cdn3.amuselabs.com/tny/crossword?id={puzzle_id}&set=tny-weekly'

    @staticmethod
    def matches_url(url_components):
        # Matches specific mini puzzle pages like /YYYY/MM/DD, not the archive page itself.
        return ('newyorker.com' in url_components.netloc and
                '/puzzles-and-games-dept/mini-crossword/' in url_components.path and
                any(char.isdigit() for char in url_components.path.split('/')[-1]))


    def find_latest(self):
        archive_url = "https://www.newyorker.com/puzzles-and-games-dept/mini-crossword"
        try:
            res = self.session.get(archive_url)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            puzzle_list_script = soup.find('script', attrs={'type': 'application/ld+json'})
            if puzzle_list_script:
                try:
                    data = json.loads(puzzle_list_script.get_text())
                    item_list = data.get('itemListElement', [])

                    if not item_list:
                        # Handle cases where the root object might be the list itself
                        if isinstance(data, list):
                            item_list = data
                        # Or if the structure is different, e.g. under a different key like 'mainEntity'
                        elif isinstance(data.get('mainEntity'), list):
                             item_list = data['mainEntity']


                    latest_puzzle_item = None
                    # Find the item with position 1, or fallback to the first if positions aren't reliable
                    for item in item_list:
                        if item.get('@type') == 'ListItem' and item.get('position') == 1:
                            latest_puzzle_item = item
                            break
                    
                    if not latest_puzzle_item and item_list: # Fallback to first item
                        latest_puzzle_item = item_list[0]


                    if latest_puzzle_item and 'url' in latest_puzzle_item:
                        latest_url = latest_puzzle_item['url']
                        # Basic validation that it's a mini crossword URL
                        if "/puzzles-and-games-dept/mini-crossword/" in latest_url:
                            # Try to parse date from URL to set self.date for filename
                            try:
                                # Extract date part, e.g., "2025/05/16"
                                date_str_from_url = latest_url.split('mini-crossword/')[-1]
                                self.date = dateparser.parse(date_str_from_url)
                            except Exception as e_date:
                                print(f"Warning: Could not parse date from latest TNY Mini URL {latest_url}: {e_date}", file=sys.stderr)
                            return latest_url
                        else:
                            raise XWordDLException(f"Found URL in JSON-LD ({latest_url}) does not appear to be a TNY Mini puzzle.")
                    else:
                        raise XWordDLException("No suitable 'itemListElement' with a URL found in JSON-LD for TNY Mini.")

                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    raise XWordDLException(f"Error parsing JSON-LD for TNY Mini: {e}. Check the page structure.")
            else:
                raise XWordDLException("No JSON-LD script found on the TNY Mini archive page.")

        except requests.exceptions.RequestException as e:
            raise XWordDLException(f"Error fetching TNY Mini archive page '{archive_url}': {e}")
        except XWordDLException: # Re-raise XWordDLExceptions from parsing logic
            raise
        except Exception as e: # Catch any other unexpected errors
            raise XWordDLException(f"An unexpected error occurred while finding the latest TNY Mini: {e}")


    def find_by_date(self, dt):
        # This constructs the URL for a specific date.
        # self.date will be set by the core logic in xword_dl.py if -d is used.
        # If this method is called directly, ensure dt is a datetime object.
        url_format = dt.strftime('%Y/%m/%d')
        guessed_url = urllib.parse.urljoin(
            'https://www.newyorker.com/puzzles-and-games-dept/mini-crossword/',
            url_format)
        return guessed_url

    # find_solver() is inherited from NewYorkerDownloader.

    def pick_filename(self, puzzle, **kwargs):
        date_for_filename = self.date or datetime.date.today()


        base_kwargs = {
            'date': date_for_filename,
            'title': ''  # Pass an empty string for the title token
        }

        return super(NewYorkerDownloader, self).pick_filename(puzzle, **base_kwargs)