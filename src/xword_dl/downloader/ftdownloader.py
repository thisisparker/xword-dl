from datetime import datetime, timedelta, timezone
import base64
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from puz import Puzzle
import requests
from .basedownloader import BaseDownloader
from ..util import XWordDLException

class FTDownloader(BaseDownloader):
    command = "ft"
    outlet = "Financial Times"
    outlet_prefix = "FT"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # something like https://app.ft.com/crossword/04f9d247-99c8-58ac-9b03-e055e1f54ef8
    # will return the url plus the iso date, like:
    # https://app.ft.com/crossword/04f9d247-99c8-58ac-9b03-e055e1f54ef8#2025-11-28T00:00:00.000Z
    # eh.... doesn't seem easily parsable from the original url, skipping this
    def find_solver(self, url: str) -> str:
        """Gets the solver_url"""
        id_timestamp = url.split("/")[-1]
        assert len(id_timestamp.split("#")) == 2, \
            "Unable to download by url, should be in the form: https://app.ft.com/crossword/04f9d247-99c8-58ac-9b03-e055e1f54ef8#2025-11-28T00:00:00.000Z"
        return url
    
    @classmethod
    def to_base(cls, i: int, b: int) -> str:
        """Converts integer to base <=36"""
        alpha = "0123456789abcdefghijklmnopqrstuvwxyz"
        ret = ""
    
        while i > 0:
            ret += alpha[i % b]
            i //= b 

        return ret[::-1]

    @classmethod
    def get_key_from_last_modified(cls, last_modified: int) -> str:
        dt = datetime.utcfromtimestamp(last_modified/1000)

        rev_day = str(dt.day)[::-1]
        if dt.day < 10:
            rev_day += '0'
        rev_year = str(dt.year)[::-1]
        
        part1 = cls.to_base(int(str(last_modified), 16), 36)
        part2 = cls.to_base((int(rev_day) + dt.day) * (int(rev_year) + dt.year), 24)

        return "#" + (part1 + part2)[:14] + "$"
     
    @classmethod
    def get_recent_puzzles(cls, from_date: datetime, to_date: datetime) -> dict:
        
        api_url = f"https://d3qii0ai0bvcck.cloudfront.net/prod/fetchlatestpuzzles?left_window={from_date.isoformat()}&right_window={to_date.isoformat()}"
        response = requests.get(api_url,
                                headers={
                                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                                    'Accept-Encoding': 'gzip' 
                                })
        json_response = response.json()
        if json_response.get("lastModified") is None or json_response.get("response") is None:
            raise XWordDLException(
                "Unable to extract lastModified and response from json response"
                )
        last_modified = json_response["lastModified"]
        response_bytes = base64.b64decode(json_response["response"])

        key = cls.get_key_from_last_modified(last_modified)
        cipher = AES.new(key.encode(), AES.MODE_CBC, iv=key.upper().encode())

        decrypted = unpad(cipher.decrypt(response_bytes), 16, style="pkcs7").decode()

        recent_puzzles_dict = json.loads(decrypted)

        # print("got recent_puzzles:")
        # print(json.dumps(recent_puzzles_dict, indent=4))
        
        recent_puzzles = recent_puzzles_dict.get("Items")
        if recent_puzzles is None:
            raise XWordDLException(
                "Malformed data from /fetchlatestpuzzles endpoint: Cannot get 'Items'"
            )

        return recent_puzzles
        
    def fetch_data(self, solver_url: str):
        id_timestamp = solver_url.split("/")[-1]
        dt = datetime.fromisoformat(id_timestamp.split('#')[1])
        
        recent_puzzles = self.get_recent_puzzles(dt + timedelta(days=-2),
                                                 dt + timedelta(days=2))
        
        for puzzle in recent_puzzles:
            if puzzle["id#crossword_timestamp"] == id_timestamp:
                return puzzle

        raise XWordDLException(
            f"Cannot get crossword from '{solver_url}'"
        )
                    
    def parse_xword(self, xw_data) -> Puzzle:
        puzzle = Puzzle()

        puzzle.author = xw_data["author"]
        puzzle.width, puzzle.height = [int(i) for i in xw_data["dimensions"].split("x")]
        puzzle.notes = xw_data["author_message"]
        puzzle.title = f"Cryptic No. {xw_data['crossword_id']}"

        crossword_json : dict = json.loads(xw_data["crossword"])
        across, down = crossword_json["across"], crossword_json["down"]

        solution = ["."] * (puzzle.width * puzzle.height)
        fill = ["."] * (puzzle.width * puzzle.height)

        for clue_obj in across.values():
            col, row = clue_obj["col"], clue_obj["row"]
            answer = clue_obj["answer"]
            for i in range(len(answer)):
                idx = row * puzzle.width + col + i
                solution[idx] = answer[i]
                fill[idx] = "-"

        for clue_obj in down.values():
            col, row = clue_obj["col"], clue_obj["row"]
            answer = clue_obj["answer"]
            for i in range(len(answer)):
                idx = (row + i) * puzzle.width + col
                solution[idx] = answer[i]
                fill[idx] = "-"
            
        puzzle.solution = "".join(solution)
        puzzle.fill = "".join(fill)
        
        clues = []
        max_clue_num = max(max(map(int, across.keys())),
                           max(map(int, down.keys())))

        for clue_num in range(1, max_clue_num+1):
            if across.get(str(clue_num)):
                clue_obj = across[str(clue_num)]
                clue = clue_obj["clue"]
                if clue_obj.get("format"):
                    clue += f" ({clue_obj['format']})"
                clues.append(clue)

            if down.get(str(clue_num)):
                clue_obj = down[str(clue_num)]
                clue = clue_obj["clue"]
                if clue_obj.get("format"):
                    clue += f" ({clue_obj['format']})"
                clues.append(clue)
            
        puzzle.clues = clues
        
        return puzzle

    @classmethod
    def find_latest_by_type(cls, crossword_type: str) -> str:
        recent_puzzles = cls.get_recent_puzzles(datetime.today() + timedelta(days=-30), datetime.today() + timedelta(days=1))
        latest = None

        for puzzle in recent_puzzles:
            if puzzle['crossword_status'] == 'PUBLISHED' and \
               puzzle['crossword_type'] == crossword_type:
                if latest is None or \
                   datetime.fromisoformat(latest['crossword_timestamp']) < \
                   datetime.fromisoformat(puzzle['crossword_timestamp']):
                   latest = puzzle

        if latest is None:
            raise XWordDLException(
                f"Cannot find latest puzzle of type {crossword_type}"
            )
        else:
            return f"https://app.ft.com/crossword/{latest['id#crossword_timestamp']}"

    def find_latest(self) -> str:
        return self.find_latest_by_type("CRYPTIC")

    @classmethod
    def find_by_date_by_type(cls, dt: datetime, crossword_type: str) -> str:
        if dt.hour != 0 or dt.minute != 0 or dt.second != 0 or (dt.tzname() != "UTC" and dt.tzinfo is not None):
            raise XWordDLException(
                f"Datetime must be exactly midnight UTC, got {dt.isoformat()}"
            )

        dt_timestamp = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        recent_puzzles = cls.get_recent_puzzles(dt + timedelta(days=-2), dt + timedelta(days=2))

        for puzzle in recent_puzzles:
            if puzzle['crossword_type'] == crossword_type and \
               puzzle['crossword_timestamp'] == dt_timestamp:
                return f"https://app.ft.com/crossword/{puzzle['id#crossword_timestamp']}"

        raise XWordDLException(
            f"Cannot find puzzle type {crossword_type} on {dt_timestamp}"
        )
        

    def find_by_date(self, dt: datetime) -> str:
        return self.find_by_date_by_type(dt, "CRYPTIC")
        
