from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException


class BillboardDownloader(AmuseLabsDownloader):
    command = "bill"
    outlet = "Billboard"
    outlet_prefix = "Billboard"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def find_latest(self) -> str:
        url = super().matches_embed_pattern(
            url="https://www.billboard.com/p/billboard-crossword/"
        )

        if not url:
            raise XWordDLException("Can't find latest Billboard puzzle.")

        return url

    def pick_filename(self, puzzle, **kwargs):
        explicit_title = puzzle.title

        if not explicit_title:
            puzzle.title = f"Billboard Crossword: {self.date: %b %d, %Y}"

        return super().pick_filename(puzzle, title=explicit_title, **kwargs)
