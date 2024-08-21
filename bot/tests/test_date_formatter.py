import pytest

from bot.data.formatter import DateFormatter


def test_date_formatter_valid_date():
    a, b = DateFormatter.parse_date_pair("02.04.24 - 07.04.24")
    assert a.strftime("%Y%m%d") == "20240402" and b.strftime("%Y%m%d") == "20240407"


def test_date_formatter_valid_date_no_space():
    a, b = DateFormatter.parse_date_pair("02.04.24-07.04.24")
    assert a.strftime("%Y%m%d") == "20240402" and b.strftime("%Y%m%d") == "20240407"


def test_date_formatter_invalid_date():
    with pytest.raises(ValueError):
        DateFormatter.parse_date_pair("02.04.24 07.04.24")
