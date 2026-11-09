"""Unit tests for the OpenStreetMap retrieval helpers.

These tests do not perform any network request.
"""

import geopandas as gpd
import shapely.geometry as sg
from isere_tourism.osm import get_layer


def test_get_layer_filters_by_geometry_type() -> None:
    data: gpd.GeoDataFrame = gpd.GeoDataFrame(
        {"name": ["restaurant_a", "restaurant_b"]},
        geometry=[sg.Point(0, 0), sg.Point(1, 1)],
        crs="EPSG:4326",
    )

    points = get_layer(data, "Point")

    assert len(points) == 2


def test_get_layer_returns_no_line_for_point_data() -> None:
    data: gpd.GeoDataFrame = gpd.GeoDataFrame(
        {"name": ["restaurant_a"]},
        geometry=[sg.Point(0, 0)],
        crs="EPSG:4326",
    )

    lines = get_layer(data, "LineString")

    assert len(lines) == 0
