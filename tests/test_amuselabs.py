import datetime as dt

import puz

import xword_dl


class TestWaPoDownloader:
    def test_find_puzzle_url_from_id(self):
        # Arrange
        downloader = xword_dl.WaPoDownloader()
        puzzle_id = "ebirnholz_201227"

        # Act
        url = downloader.find_puzzle_url_from_id(puzzle_id)

        # Assert
        assert (
            url == "https://cdn1.amuselabs.com/wapo/crossword"
            "?id=ebirnholz_201227&set=wapo-eb"
        )

    def test_parse_xword(self):
        # Arrange
        downloader = xword_dl.WaPoDownloader()
        xword_data = {
            "title": " my crossword ",
            "box": [["B", "I", "G"], ["P", "I", "G"]],
            "w": 2,
            "h": 2,
            "placedWords": [
                {
                    "word": "ROCK",
                    "x": 0,
                    "y": 0,
                    "acrossNotDown": True,
                    "clue": {"clue": " 'n' roll"},
                }
            ],
        }

        # Act
        puzzle = downloader.parse_xword(xword_data)

        # Assert
        assert puzzle.title == "my crossword"
        assert puzzle.width == 2
        assert puzzle.height == 2

    def test_pick_filename(self):
        # Arrange
        downloader = xword_dl.WaPoDownloader()
        puzzle = puz.Puzzle()
        puzzle.id = "ebirnholz_201227"

        # Act
        filename = downloader.pick_filename(puzzle)

        # Assert
        assert filename == "WaPo.puz"

    def test_guess_date_from_id(self):
        # Arrange
        downloader = xword_dl.WaPoDownloader()
        puzzle_id = "ebirnholz_201227"

        # Act
        downloader.guess_date_from_id(puzzle_id)

        # Assert
        assert downloader.date == dt.datetime(2020, 12, 27, 0, 0)

    def test_find_by_date(self):
        # Arrange
        downloader = xword_dl.WaPoDownloader()
        today = dt.datetime(2020, 12, 28, 19, 34, 14, 943230)

        # Act
        url = downloader.find_by_date(today)

        # Assert
        assert (
            url == "https://cdn1.amuselabs.com/wapo/crossword"
            "?id=ebirnholz_201228&set=wapo-eb"
        )


class TestAtlanticDownloader:
    def test_find_by_date(self):
        # Arrange
        downloader = xword_dl.AtlanticDownloader()
        today = dt.datetime(2020, 12, 28, 19, 34, 14, 943230)

        # Act
        url = downloader.find_by_date(today)

        # Assert
        assert (
            url == "https://cdn3.amuselabs.com/atlantic/crossword"
            "?id=atlantic_20201228&set=atlantic"
        )
