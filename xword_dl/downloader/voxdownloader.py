import datetime

from .amuselabsdownloader import AmuseLabsDownloader

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

    def find_by_date(self, dt):
        url_formatted_date = dt.strftime('%Y%m%d')
        authors = ['', 'PB', 'AP', 'WN', 'AOK', 'JG', 'AJR']  # The author varies by day, and their initials may or may not be present as a prefix
        suffixes = ['1000', '1100', '1000%20(1)']  # The suffix is always one of these. I can't determine the pattern.
        self.get_and_add_picker_token()
        candidate_urls = []
        for suffix in suffixes:  # On average, it will be faster to search by the most frequent suffixes first
            for author in authors:
                self.id = author + 'vox_' + url_formatted_date + '_' + suffix
                candidate_urls.append(self.find_puzzle_url_from_id(self.id))
        return candidate_urls
