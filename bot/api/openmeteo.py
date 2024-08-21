"""
Provides methods to access Open-Meteo API
"""

import requests


class OpenMeteoAPI:
    """API Adapter"""
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    @classmethod
    def forecast_for_16_days(cls, lat: float, long: float) -> list | None:
        """
        Get forecast for next 16 days
        """
        response = requests.get(f"{cls.BASE_URL}?latitude={lat}&longitude={long}"
                                f"&forecast_days=16&daily=weather_code,temperature_2m_max,"
                                f"temperature_2m_min")
        data = response.json()
        if "error" in data and data["error"]:
            return None
        try:
            return zip(data["daily"]["time"], data["daily"]["weather_code"],
                       data["daily"]["temperature_2m_max"], data["daily"]["temperature_2m_min"])
        except KeyError:
            return None

    @classmethod
    def forecast_for_dates(cls, lat: float, long: float, dates: list) -> list | None:
        """
        Get maximum possible forecast for given range of dates
        """
        forecast = cls.forecast_for_16_days(lat, long)
        if forecast is None:
            return None
        return list(filter(lambda x: x[0] in dates, forecast))

    WEATHER_CODE_FORMAT = {
        0:  ("Clear sky", "☀️"),
        1:  ("Mainly clear", "🌤️"),
        2:  ("Partly cloudy", "⛅"),
        3:  ("Partly cloudy", "☁️"),
        45: ("Fog", "🌫️"),
        48: ("Rime fog", "🌫️"),
        51: ("Light drizzle", "🌦️"),
        53: ("Moderate drizzle", "🌦️"),
        55: ("Dense drizzle", "🌦️"),
        56: ("Light freezing drizzle", "🌦️"),
        57: ("Dense freezing drizzle", "🌦️"),
        61: ("Slight rain", "🌧️"),
        63: ("Moderate rain", "💧"),
        65: ("Heavy rain", "💧"),
        66: ("Light freezing rain", "🌧️"),
        67: ("Heavy freezing rain", "💧"),
        71: ("Slight snow fall", "🌨️"),
        73: ("Moderate snow fall", "❄️"),
        75: ("Heavy snow fall", "❄️"),
        77: ("Snow grains", "❄️"),
        80: ("Slight rain shower", "💧💧"),
        81: ("Moderate rain shower", "💧💧"),
        82: ("Violent rain shower", "💧💧"),
        85: ("Slight snow showers", "❄️❄️"),
        86: ("Heavy snow showers", "❄️❄️"),
        95: ("Thunderstorm", "🌪️"),
        96: ("Thunderstorm w/ slight hail", "🌪️❄️"),
        99: ("Thunderstorm w/ heavy hail", "🌪️❄️")
    }

    @classmethod
    def get_weather_code_format(cls, code: int) -> tuple[str, str]:
        """
        Transform integer weather code to icon w/ description
        """
        if code not in cls.WEATHER_CODE_FORMAT:
            return "Unknown", "❔"
        return cls.WEATHER_CODE_FORMAT[code]

    @classmethod
    def format_forecast(cls, forecast: list) -> list:
        """
        Format to human-readable format
        """
        return list(map(lambda x: (x[0].replace("-", "."),
                                   cls.get_weather_code_format(x[1]),
                                   f"{x[2]} °C",
                                   f"{x[3]} °C"),
                        forecast))
