from .amuselabsdownloader import AmuseLabsDownloader

class DefectorDownloader(AmuseLabsDownloader):
    command = 'def'
    outlet = 'Defector'
    outlet_prefix = 'Defector'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = 'https://cdn3.amuselabs.com/pmm/date-picker?set=defectormedia'
        self.url_from_id = 'https://cdn3.amuselabs.com/pmm/crossword?id={puzzle_id}&set=defectormedia'
