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
