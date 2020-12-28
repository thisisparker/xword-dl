import xword_dl


class TestWsjDownloader:
    def test_find_solver_simple(self):
        # Arrange
        downloader = xword_dl.WSJDownloader()
        url = "https://example.com/puzzles/crossword/123"

        # Act
        url = downloader.find_solver(url)

        # Assert
        assert url == "https://example.com/puzzles/crossword/123"
