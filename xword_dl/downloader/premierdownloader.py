# premierdownloader.py
#
# Author: Eric Cloninger (github: ehcloninger)
# Issue: https://github.com/thisisparker/xword-dl/issues/115#
#
# The format of the request for the King puzzles is as follows
# https://puzzles.kingdigital.com/jpz/[feature]/YYYYMMDD.jpz
# Where [feature] is one of Premier, Joseph, Sheffer.
#
# Sheffer and Joseph are a daily, Monday thru Saturday
# https://puzzles.kingdigital.com/jpz/Joseph/20230811.jpz
# https://puzzles.kingdigital.com/jpz/Joseph/20230812.jpz
# https://puzzles.kingdigital.com/jpz/Sheffer/20230811.jpz
#
# Premier is a weekly on Sunday
# https://puzzles.kingdigital.com/jpz/Premier/20230806.jpz
# https://puzzles.kingdigital.com/jpz/Premier/20230813.jpz

from .compilerdownloader import CrosswordCompilerDownloader
from ..util import XWordDLException

class PremierePuzzlesBaseDownloader(CrosswordCompilerDownloader):
    feature_url = None
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def find_solver(self, url):
        if (self.feature_url is None):
            raise XWordDLException('Invalid feature name.')
        url_encoded_date=self.date.strftime('%Y%m%d')
        puzzle_url = 'https://puzzles.kingdigital.com/jpz/' + self.feature_url + '/' + url_encoded_date + '.jpz'
        return puzzle_url

class PremierPuzzlesDownloader (PremierePuzzlesBaseDownloader):
    command = 'pre'
    outlet = 'Premier Puzzles'
    outlet_prefix = 'Premier Puzzles'
    feature_url = 'Premier'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def find_by_date(self, dt):
        self.date = dt
        if self.date.weekday() != 6:
            raise XWordDLException('Invalid date: Premier puzzle is only available on Sundays.')
        url_encoded_date=dt.strftime('%Y%m%d')

class PremierPuzzlesJosephDownloader (PremierePuzzlesBaseDownloader):
    command = 'jos'
    outlet = 'Premier Puzzles Joseph'
    outlet_prefix = 'Premier Joseph'
    feature_url = 'Joseph'

    def find_by_date(self, dt):
        self.date = dt
        if self.date.weekday() == 6:
            raise XWordDLException('Invalid date: Joseph puzzle is not available on Sundays.')
        url_encoded_date=dt.strftime('%Y%m%d')

class PremierPuzzlesShefferDownloader (PremierePuzzlesBaseDownloader):
    command = 'she'
    outlet = 'Premier Puzzles Sheffer'
    outlet_prefix = 'Premier Sheffer'
    feature_url = 'Sheffer'

    def find_by_date(self, dt):
        self.date = dt
        if self.date.weekday() == 6:
            raise XWordDLException('Invalid date: Sheffer puzzle is not available on Sundays.')
        url_encoded_date=dt.strftime('%Y%m%d')
