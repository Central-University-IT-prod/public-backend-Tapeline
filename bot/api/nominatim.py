"""
NominatimAPI related stuff
"""

import requests


class City:
    """
    Adapter for Nominatim city
    """
    def __init__(self, osm_id: int, lat: float, lon: float,
                 name: str, full_name: str, type: str):
        self.id = osm_id
        self.lat = lat
        self.lon = lon
        self.name = name
        self.full_name = full_name
        self.type = type


class NominatimAPI:
    """
    Provides methods for accessing NominatimAPI
    """
    BASE_URL = "https://nominatim.openstreetmap.org"

    @classmethod
    def get_possible_cities_by_name(cls, name: str) -> list[City]:
        """
        Get list of cities that can be called with given name
        """
        answer = requests.get(f"{cls.BASE_URL}/search?q={name}&format=json")
        results = answer.json()
        return list(map(lambda x: City(x["osm_id"],
                                       x["lat"],
                                       x["lon"],
                                       x["name"],
                                       x["display_name"],
                                       x["osm_type"][0].upper()),
                        filter(lambda x: "type" in x and x["type"] in ("city", "town"),
                               results)))

    @classmethod
    def search(cls, query: str) -> list:
        """
        Perform a text search
        """
        answer = requests.get(f"{cls.BASE_URL}/search?q={query}&format=json")
        return answer.json()

    @classmethod
    def get_lat_lon_by_id(cls, osm_id: int, osm_type: str = "R") -> tuple[float, float]:
        """
        Get latitude and longitude of object with given OSM ID
        """
        answer = requests.get(f"{cls.BASE_URL}/lookup?osm_ids={osm_type}{osm_id}&format=json")
        results = answer.json()[0]
        if "lat" not in results:
            return (results["centroid"]["coordinates"][1],
                    results["centroid"]["coordinates"][0])
        return results["lat"], results["lon"]

    @classmethod
    def get_by_id(cls, osm_id: int, osm_type: str = "R") -> dict | None:
        """
        Get object with given OSM ID
        """
        answer = requests.get(f"{cls.BASE_URL}/lookup?osm_ids={osm_type}{osm_id}&format=json")
        if len(answer.json()) == 0:
            return None
        results = answer.json()[0]
        return results

    @classmethod
    def get_city_at_point(cls, lat: float, lon: float) -> dict | None:
        """
        Get city to which given point belongs
        """
        answer = requests.get(f"{cls.BASE_URL}/reverse?lat={lat}&lon={lon}&zoom=10&format=json")
        data = answer.json()
        if "error" in data:
            return None
        return data

    @classmethod
    def get_something_at_point(cls, lat: float, lon: float) -> dict | None:
        """
        Get object by its coordinates
        """
        answer = requests.get(f"{cls.BASE_URL}/reverse?lat={lat}&lon={lon}&format=json")
        data = answer.json()
        if "error" in data:
            return None
        return data

    @classmethod
    def get_something_at_point_with_zoom(cls, lat: float, lon: float, zoom: int) -> dict | None:
        """
        Get object by its coordinates (considering zoom)
        """
        answer = requests.get(f"{cls.BASE_URL}/reverse?lat={lat}&lon={lon}&zoom={zoom}&format=json")
        data = answer.json()
        if "error" in data:
            return None
        return data

    @classmethod
    def get_name_in_answer(cls, answer: dict) -> str:
        """
        Safely get name in OSM object given by Nominatim
        """
        if "name" in answer and len(answer["name"]) > 0:
            return answer["name"]
        if "localname" in answer and len(answer["localname"]) > 0:
            return answer["localname"]
        if "display_name" in answer and len(answer["display_name"]) > 0:
            return answer["display_name"]
        return "Unknown name"

    @classmethod
    def get_address(cls, answer: dict) -> str:
        addr = answer["address"]
        house_n = addr["house_number"] if "house_number" in addr else None
        road = addr["road"] if "road" in addr else None
        city = addr["city"] if "city" in addr else None
        components = list(filter(lambda x: x is not None, [city, road, house_n]))
        return ", ".join(components)
