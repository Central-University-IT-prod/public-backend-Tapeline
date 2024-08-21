"""
Provides methods for OpenTripMap API
"""

import requests

from bot.utils.listutils import lists_intersect


class Feature:
    """
    Adapter for OpenTripMap feature object
    """
    def __init__(self, name, dist, rate, osm_link, kinds, xid):
        self.name = name
        self.dist = dist
        self.rate = int(str(rate).replace("h", ""))
        self.osm_link = osm_link
        self.kinds = kinds.split(",")
        self.xid = xid


class OpenTripMapAPI:
    """API Adapter"""
    API_KEY = "5ae2e3f221c38a28845f05b63a52b9d00a39d11ebcce4b01b1dfaa5a"
    BASE_URL = "https://api.opentripmap.com/0.1/en"

    @classmethod
    def get_places_around(cls, lat: float, lon: float, radius: int = 3000) -> list[Feature]:
        """
        Gets all features in certain radius
        """
        response = requests.get(f"{cls.BASE_URL}/places/radius?lat={lat}&lon={lon}&radius={radius}"
                                f"&apikey={cls.API_KEY}")
        try:
            features = response.json()["features"]
            return list(map(lambda x: Feature(x["properties"]["name"],
                                              x["properties"]["dist"] if "dist" in x["properties"] else 0,
                                              x["properties"]["rate"] if "rate" in x["properties"] else 0,
                                              x["properties"]["osm"] if "osm" in x["properties"] else None,
                                              x["properties"]["kinds"],
                                              x["properties"]["xid"]),
                            features))
        except KeyError:
            return []

    @classmethod
    def get_foods_around(cls, lat: float, lon: float, radius: int = 3000) -> list[Feature]:
        response = requests.get(f"{cls.BASE_URL}/places/radius?lat={lat}&lon={lon}&radius={radius}"
                                f"&apikey={cls.API_KEY}&kinds=foods")
        try:
            features = response.json()["features"]
            return list(map(lambda x: Feature(x["properties"]["name"],
                                              x["properties"]["dist"] if "dist" in x["properties"] else 0,
                                              x["properties"]["rate"] if "rate" in x["properties"] else 0,
                                              x["properties"]["osm"] if "osm" in x["properties"] else None,
                                              x["properties"]["kinds"],
                                              x["properties"]["xid"]),
                            features))
        except KeyError:
            return []

    @classmethod
    def get_accommodations_around(cls, lat: float, lon: float, radius: int = 3000) -> list[Feature]:
        response = requests.get(f"{cls.BASE_URL}/places/radius?lat={lat}&lon={lon}&radius={radius}"
                                f"&apikey={cls.API_KEY}&kinds=accomodations")
        try:
            features = response.json()["features"]
            return list(map(lambda x: Feature(x["properties"]["name"],
                                              x["properties"]["dist"] if "dist" in x["properties"] else 0,
                                              x["properties"]["rate"] if "rate" in x["properties"] else 0,
                                              x["properties"]["osm"] if "osm" in x["properties"] else None,
                                              x["properties"]["kinds"],
                                              x["properties"]["xid"]),
                            features))
        except KeyError:
            return []

    KIND_TO_ICON = {
        "natural": "🏔️",
        "cultural": "🎭",
        "historic": "🏛️",
        "religion": "🛐",
        "architecture": "🏰",
        "amusements": "🎡",
    }
    ALLOWED_FEATURES = KIND_TO_ICON.keys()

    @classmethod
    def filter_suitable(cls, features: list[Feature]) -> list[Feature]:
        """
        Filters all unsuitable places
        """
        return list(filter(lambda x: lists_intersect(cls.ALLOWED_FEATURES, x.kinds) and
                           len(x.name) > 0, features))

    @classmethod
    def get_icons_for_feature(cls, feature: Feature) -> str:
        """Transform kind-IDs to icons"""
        return "".join(map(lambda x: cls.KIND_TO_ICON[x],
                           filter(lambda x: x in cls.KIND_TO_ICON, feature.kinds)))

    @classmethod
    def _get_score_for_feature(cls, feature: Feature, radius=3000) -> float:
        """Utility function"""
        rate_score = (feature.rate + 1) * 0.2
        dist_score = (radius - feature.dist) / radius
        return (rate_score + dist_score) / 2

    @classmethod
    def sort_by_relevancy(cls, features: list[Feature], radius: int = 3000) -> list[Feature]:
        """Sort features by their distance and rate"""
        return sorted(features, key=lambda x: cls._get_score_for_feature(x, radius), reverse=True)
