from datetime import datetime


class DateFormatter:
    @classmethod
    def parse_date_pair(cls, dates_text) -> tuple[datetime, datetime]:
        dates = dates_text.strip().replace(" ", "").split("-")
        if len(dates) != 2:
            raise ValueError("Invalid date format")
        start_date, end_date = dates
        try:
            start_date = datetime.strptime(start_date, "%d.%m.%y")
            end_date = datetime.strptime(end_date, "%d.%m.%y")
            return start_date, end_date
        except ValueError as exc:
            raise ValueError("Invalid dates. Try again") from exc
