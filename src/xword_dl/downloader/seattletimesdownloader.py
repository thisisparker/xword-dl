import datetime
import json

from .amuselabsdownloader import AmuseLabsDownloader
from ..util import XWordDLException


class SeattleTimesMidiDownloader(AmuseLabsDownloader):
    command = "stm"
    outlet = "Seattle Times Midi"
    outlet_prefix = "Seattle Times Midi"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Verified URLs from successful API testing
        self.picker_url = "https://seattletimes.amuselabs.com/puzzleme/date-picker?set=seattletimes-crossword-midi"
        self.url_from_id = (
            "https://seattletimes.amuselabs.com/puzzleme/crossword?id={puzzle_id}&set=seattletimes-crossword-midi"
        )

    def guess_date_from_puzzle_title(self, title):
        # Seattle Times Midi puzzles have descriptive titles, not dates
        # Date is stored separately in publication metadata
        pass

    def find_by_date(self, dt):
        """
        Seattle Times Midi puzzles use sequential IDs (midi-crossword-111, etc.)
        rather than date-based IDs. We need to fetch the picker page and find
        the puzzle that matches the requested date.
        """
        self.date = dt
        
        # Fetch the picker page to get the puzzle list
        res = self.session.get(self.picker_url)
        
        # The picker page contains a JSON blob with puzzle metadata
        # Extract it from the <script id="params"> tag
        import re
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(res.text, 'html.parser')
        params_script = soup.find('script', id='params')
        
        if not params_script or not params_script.string:
            raise XWordDLException("Unable to find puzzle metadata in picker page.")
        
        try:
            params = json.loads(params_script.string)
            streak_info = params.get('streakInfo', [])
        except json.JSONDecodeError:
            raise XWordDLException("Unable to parse puzzle metadata.")
        
        if not streak_info:
            raise XWordDLException("No puzzles found in archive.")
        
        # Convert requested date to Unix timestamp (milliseconds)
        # Publication times are in America/Los_Angeles timezone
        requested_timestamp = int(dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        
        # Find puzzle matching the requested date (within 24 hours)
        for puzzle_entry in streak_info:
            puzzle_details = puzzle_entry.get('puzzleDetails', {})
            pub_time = puzzle_details.get('publicationTime', 0)
            puzzle_id = puzzle_details.get('puzzleId')
            
            # Check if publication date matches (within same day)
            if abs(pub_time - requested_timestamp) < 86400000:  # 24 hours in milliseconds
                self.id = puzzle_id
                self.get_and_add_picker_token(picker_source=res.text)
                return self.find_puzzle_url_from_id(self.id)
        
        # Determine available date range for better error message
        if streak_info:
            oldest_time = min(p.get('puzzleDetails', {}).get('publicationTime', float('inf')) for p in streak_info)
            newest_time = max(p.get('puzzleDetails', {}).get('publicationTime', 0) for p in streak_info)
            oldest_date = datetime.datetime.fromtimestamp(oldest_time / 1000).strftime('%Y-%m-%d') if oldest_time != float('inf') else 'unknown'
            newest_date = datetime.datetime.fromtimestamp(newest_time / 1000).strftime('%Y-%m-%d') if newest_time > 0 else 'unknown'
            raise XWordDLException(
                f"No puzzle found for date {dt.strftime('%Y-%m-%d')}. "
                f"Seattle Times Midi archive only contains puzzles from {oldest_date} to {newest_date}. "
                f"Historical puzzles beyond this range are not accessible via this API."
            )
        
        raise XWordDLException(f"No puzzle found for date {dt.strftime('%Y-%m-%d')}")

    def parse_xword(self, xw_data):
        # Date is already set in find_by_date
        return super().parse_xword(xw_data)
