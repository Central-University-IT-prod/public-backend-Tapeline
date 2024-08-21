import os

from pytest_image_snapshot import image_snapshot

from bot.utils import route
from PIL import Image


created_files = []


def test_route_creation(image_snapshot):
    file = route.create_route((54.72674, 55.94167), (54.73268, 55.93142))
    created_files.append(file)
    file_image = Image.open(file)
    image_snapshot(file_image, "bot/tests/map_test_1.png")


def test_poly_route_creation(image_snapshot):
    file = route.create_poly_route((
        (54.72674, 55.94167),
        (54.73268, 55.93142),
        (54.73317, 55.93937),
        (54.72808, 55.94940)
    ))
    created_files.append(file)
    file_image = Image.open(file)
    image_snapshot(file_image, "bot/tests/map_test_2.png")


def teardown():
    for file in created_files:
        os.remove(file)
