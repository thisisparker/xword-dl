import urllib

from ..util import *

class BaseDownloader:
    outlet = None
    outlet_prefix = None

    def __init__(self, **kwargs):
        self.date = kwargs.get('date', None)
        self.netloc = urllib.parse.urlparse(kwargs.get('url','')).netloc
        self.filename = kwargs.get('filename', None)

        self.settings = {}

        self.settings.update(read_config_values('general'))

        if hasattr(self, 'command') or 'inherit_settings' in kwargs:
            self.settings.update(read_config_values(
                                    kwargs.get('inherit_settings')))
            self.settings.update(read_config_values(
                                    getattr(self, 'command', '')))
        elif 'url' in kwargs:
            self.settings.update(read_config_values('url'))
            self.settings.update(read_config_values(self.netloc))

        self.settings.update(kwargs)

    def pick_filename(self, puzzle, **kwargs):
        tokens = {'outlet':  self.outlet or '',
                  'prefix':  self.outlet_prefix or '',
                  'title':   puzzle.title or '',
                  'author':  puzzle.author or '',
                  'cmd':     (self.command if hasattr(self, 'command')
                              else self.netloc or ''),
                  'netloc':  self.netloc or '',
                 }

        tokens = {t:kwargs[t] if t in kwargs else tokens[t] for t in tokens}

        date = kwargs.get('date', self.date)

        template = self.filename or self.settings.get('filename') or ''

        if not template:
            template += '%prefix' if tokens.get('prefix') else '%author'
            template += ' - %Y%m%d' if date  else ''
            template += ' - %title' if tokens.get('title') else ''

        for token in tokens.keys():
            replacement = (kwargs.get(token) if token in kwargs
                           else tokens[token])
            replacement = remove_invalid_chars_from_filename(replacement)
            template = template.replace('%' + token, replacement)

        if date:
            template = date.strftime(template)

        if not template.endswith('.puz'):
            template += '.puz'

        template = ' '.join(template.split())

        return template

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
