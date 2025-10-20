from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException


class BillboardDownloader(AmuseLabsDownloader):
    command = "bill"
    outlet = "Billboard"
    outlet_prefix = "Billboard"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def matches_url(cls, url_components):
        return (
            url_components.netloc == "www.billboard.com"
            and url_components.path.removesuffix("/") == "/p/billboard-crossword"
        )

    def find_latest(self) -> str:
        return "https://www.billboard.com/p/billboard-crossword"

    def find_solver(self, url) -> str:
        res = self.session.get(url)

        if not res.ok:
            raise XWordDLException("Unable to connect to Billboard.")

        solver_url = self.matches_embed_pattern(page_source=res.text)

        if not solver_url:
            raise XWordDLException("Can't find latest Billboard puzzle.")

        return solver_url

    def parse_xword(self, xw_data):
        # Billboard puzzles are typically untitled, and some have the title set to '-'
        # so let's clear that out so it's "truly" untitled after parsing
        # If we see this in other outlets it might be worth promoting to the general Amuse parser
        puzzle = super().parse_xword(xw_data)
        if puzzle.title == "-":
            puzzle.title = ""

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        explicit_title = puzzle.title

        if not explicit_title:
            puzzle.title = f"Billboard Crossword: {self.date:%b {self.date.day}, %Y}"

        return super().pick_filename(puzzle, title=explicit_title, **kwargs)
