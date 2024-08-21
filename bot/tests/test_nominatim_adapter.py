from bot.api.nominatim import NominatimAPI


def test_search_relation_by_id():
    place = NominatimAPI.get_by_id(1549169)
    assert NominatimAPI.get_name_in_answer(place) == "Уфа"


def test_search_way_by_id():
    place = NominatimAPI.get_by_id(31001677, "W")
    assert NominatimAPI.get_name_in_answer(place) == "Благовещенск"


def test_search_node_by_id():
    place = NominatimAPI.get_by_id(5373733677, "N")
    assert NominatimAPI.get_name_in_answer(place) == "Башкирская государственная филармония имени Хусаина Ахметова"


def test_get_city_at_point():
    city = NominatimAPI.get_city_at_point(54.728293900000004, 55.9396757)
    assert NominatimAPI.get_name_in_answer(city) == "Уфа"


def test_get_country_at_city():
    city = NominatimAPI.get_city_at_point(54.728293900000004, 55.9396757)
    obj = NominatimAPI.get_by_id(city["osm_id"])
    assert obj["address"]["country"] == "Россия"
