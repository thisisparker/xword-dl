from .amuselabsdownloader import AmuseLabsDownloader


class WalrusDownloader(AmuseLabsDownloader):
    command = "wal"
    outlet = "The Walrus"
    outlet_prefix = "The Walrus"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.picker_url = (
            "https://cdn2.amuselabs.com/pmm/date-picker?set=walrus-weekly-crossword"
        )
        self.url_from_id = "https://cdn2.amuselabs.com/pmm/crossword?id={puzzle_id}&set=walrus-weekly-crossword"
