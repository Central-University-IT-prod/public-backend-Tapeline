import uuid

import staticmaps
from polyline import polyline

from bot.api import openroute
from bot.api.openroute import RouteException


def create_poly_route(coords):
    if len(coords) == 2:
        return create_route(*coords)
    if len(coords) < 2:
        return None
    return create_route(coords[0], coords[-1], coords[1:-1])


def create_route(start_coords, end_coords, middle_points=None):
    if middle_points is None:
        middle_points = []
    try:
        a_lat, a_lon = map(float, start_coords)
        b_lat, b_lon = map(float, end_coords)
        line = openroute.api.route([[a_lon, a_lat],
                                    *list(map(lambda x: (x[1], x[0]), middle_points)),
                                    [b_lon, b_lat]])
        if line is None:
            return None
        decoded = polyline.decode(line)
        context = staticmaps.Context()
        context.set_tile_provider(staticmaps.tile_provider_OSM)
        if len(decoded) > 1:
            context.add_object(
                staticmaps.Line(
                    [staticmaps.create_latlng(lat, lng) for lat, lng in decoded],
                    width=3,
                    color=staticmaps.BLUE,
                )
            )
        for mp in middle_points:
            context.add_object(
                staticmaps.Marker(
                    staticmaps.create_latlng(*list(map(float, mp))),
                    color=staticmaps.GREEN
                )
            )
        context.add_object(
            staticmaps.ImageMarker(
                staticmaps.create_latlng(a_lat, a_lon),
                "bot/assets/icon_start.png",
                2,
                32
            )
        )
        context.add_object(
            staticmaps.ImageMarker(
                staticmaps.create_latlng(b_lat, b_lon),
                "bot/assets/icon_finish.png",
                10,
                32
            )
        )
        image = context.render_cairo(2000, 2000)
        file_uid = uuid.uuid4()
        image.write_to_png(f"{file_uid}.png")
    except RouteException as re:
        raise re
    except Exception as e:
        return None
    return f"{file_uid}.png"
