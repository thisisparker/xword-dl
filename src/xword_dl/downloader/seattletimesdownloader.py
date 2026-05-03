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
        rather than date-based IDs. We fetch the picker page first to check recent
        puzzles in streakInfo, then fall back to ID enumeration for older puzzles.
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
        
        # First, try to find puzzle in streakInfo (fast path for recent puzzles)
        for puzzle_entry in streak_info:
            puzzle_details = puzzle_entry.get('puzzleDetails', {})
            pub_time = puzzle_details.get('publicationTime', 0)
            puzzle_id = puzzle_details.get('puzzleId')
            
            # Check if publication date matches (within same day)
            if abs(pub_time - requested_timestamp) < 86400000:  # 24 hours in milliseconds
                self.id = puzzle_id
                self.get_and_add_picker_token(picker_source=res.text)
                return self.find_puzzle_url_from_id(self.id)
        
        # Not in streakInfo - fall back to ID enumeration for historical puzzles
        # Seattle Times Midi publishes daily, so estimate the ID based on days difference
        # Use known reference point: Feb 4, 2026 = puzzle ID 1 (first puzzle)
        from datetime import datetime as dt_class
        reference_date = dt_class(2026, 2, 4, 0, 0, 0)
        reference_id = 1
        reference_timestamp = int(reference_date.timestamp() * 1000)
        
        # Calculate days between reference date and requested date
        days_diff = (requested_timestamp - reference_timestamp) / 86400000  # milliseconds to days
        
        # Estimate the target ID (assuming ~1 puzzle per day)
        estimated_id = int(reference_id + days_diff)
        
        # Search in a range around the estimate (±60 puzzles - IDs are not strictly chronological)
        search_start = max(1, estimated_id - 60)
        search_end = estimated_id + 60
        
        # Search for the puzzle, trying IDs closest to estimate first
        search_order = []
        for offset in range(61):
            if estimated_id - offset >= search_start:
                search_order.append(estimated_id - offset)
            if estimated_id + offset <= search_end and offset > 0:
                search_order.append(estimated_id + offset)
        
        for id_num in search_order:
            if id_num < 1:
                continue
                
            puzzle_id = f"midi-crossword-{id_num}"
            
            # Set the ID first, then get the token for THIS specific puzzle
            self.id = puzzle_id
            self.get_and_add_picker_token(picker_source=res.text)
            
            # Build puzzle URL with the correct tokens
            puzzle_url = self.find_puzzle_url_from_id(puzzle_id)
            
            try:
                # Use the parent class's fetch_data method to get decoded puzzle data
                xword_data = self.fetch_data(puzzle_url)
                
                # Extract publishTime from puzzle data (in milliseconds)
                pub_time = int(xword_data.get('publishTime', 0))
                
                if not pub_time:
                    continue
                
                # Compare dates, not timestamps, to avoid timezone issues
                pub_date = datetime.date.fromtimestamp(pub_time / 1000)
                target_date = dt.date()
                
                if pub_date == target_date:
                    # Found it! puzzle_url is already correct
                    return puzzle_url
                    
            except Exception as e:
                # Failed to fetch/parse this ID, try next
                continue
            finally:
                # Reset url_from_id for next iteration
                self.url_from_id = "https://seattletimes.amuselabs.com/puzzleme/crossword?id={puzzle_id}&set=seattletimes-crossword-midi"
        
        raise XWordDLException(
            f"No puzzle found for date {dt.strftime('%Y-%m-%d')}. "
            f"Searched puzzle IDs {search_start} to {search_end} based on publication schedule."
        )

    def parse_xword(self, xw_data):
        # Date is already set in find_by_date
        return super().parse_xword(xw_data)
