import datetime

from .amuselabsdownloader import AmuseLabsDownloader


class SeattleTimesMidiDownloader(AmuseLabsDownloader):
    command = "stm"
    outlet = "Seattle Times Midi"
    outlet_prefix = "Seattle Times Midi"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # TODO: These URLs need to be verified via browser inspection
        # The Seattle Times website uses AmuseLabs infrastructure with
        # the puzzle set "seattletimes-crossword-midi"
        # 
        # To find the correct URLs:
        # 1. Open https://www.seattletimes.com/games-crossword-midi/ in browser
        # 2. Open DevTools > Network tab
        # 3. Load the puzzle and observe the API calls
        # 4. Look for calls to amuselabs.com with "date-picker" or "crossword"
        # 5. Update these URLs with the correct pattern
        
        # Best guess based on AmuseLabs patterns (but returns 404 currently):
        self.picker_url = "https://seattletimes.amuselabs.com/st/date-picker?set=seattletimes-crossword-midi"
        self.url_from_id = (
            "https://seattletimes.amuselabs.com/st/crossword?id={puzzle_id}&set=seattletimes-crossword-midi"
        )

    def guess_date_from_id(self, puzzle_id):
        # Puzzle ID format unknown - likely something like:
        # - stmidi-YYYYMMDD
        # - seattletimes-midi-YYYYMMDD
        # - or similar pattern
        # TODO: Verify actual format from browser inspection
        try:
            # Try extracting date from common patterns
            if "-" in puzzle_id:
                parts = puzzle_id.split("-")
                for part in parts:
                    if len(part) == 8 and part.isdigit():
                        self.date = datetime.datetime.strptime(part, "%Y%m%d")
                        return
        except (IndexError, ValueError):
            pass

    def find_by_date(self, dt):
        self.date = dt
        
        # Puzzle ID format guess - update after browser inspection
        url_formatted_date = dt.strftime("%Y%m%d")
        self.id = f"seattletimes-crossword-midi-{url_formatted_date}"

        self.get_and_add_picker_token()

        return self.find_puzzle_url_from_id(self.id)

    def parse_xword(self, xw_data):
        self.guess_date_from_id(self.id)

        return super().parse_xword(xw_data)
