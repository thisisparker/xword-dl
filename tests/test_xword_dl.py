import pytest

import xword_dl


def test_remove_invalid_chars_from_filename():
    # Arrange
    invalid_filename = r'<my> filename:"/\|?*'

    # Act
    filename = xword_dl.remove_invalid_chars_from_filename(invalid_filename)

    # Assert
    assert filename == "my filename"


class TestBaseDownloader:
    def test_find_solver(self):
        # Arrange
        downloader = xword_dl.BaseDownloader()
        url = "https://example.com"

        # Act / Assert
        with pytest.raises(NotImplementedError):
            downloader.find_solver(url)
