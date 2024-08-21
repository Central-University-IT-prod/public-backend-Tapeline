"""
Provides methods to access OpenRouteService API
"""

import requests
from ratelimit import limits


class OpenRouteAPI:
    """API Adapter"""
    TOKEN = "5b3ce3597851110001cf6248ed30ed7e9f6646c4892b89a46bcecf9c"

    @limits(calls=30, period=60)
    @limits(calls=1500, period=60 * 60 * 24)
    def route(self, points: list) -> str | None:
        """
        Get route based on given point list
        """
        ans = requests.post("https://api.openrouteservice.org/v2/directions/driving-car/json", json={
            "coordinates": points
        }, headers={"Authorization": self.TOKEN})
        data = ans.json()
        if "error" in data:
            raise RouteException(data["error"]["message"])
        try:
            return ans.json()["routes"][0]["geometry"]
        except KeyError:
            return None


class RouteException(Exception):
    """Thrown when route generation fails"""
    pass


api = OpenRouteAPI()
