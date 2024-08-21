from datetime import timedelta


def datetime_range(start, end):
    span = end - start
    for i in range(span.days + 1):
        yield start + timedelta(days=i)
