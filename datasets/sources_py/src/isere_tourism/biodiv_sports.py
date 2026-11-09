# ----------------------------------------------------------------------
# Example use of the Biodiv'Sports API for sensitive areas
# See all available operations: https://biodiv-sports.fr/api/v2/#operations-tag-sensitivearea
# ----------------------------------------------------------------------

import os
import tempfile

import geopandas as gpd
import matplotlib.pyplot as plt
import requests

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

SENSITIVE_AREAS_URL = "https://biodiv-sports.fr/api/v2/sensitivearea/"
DEPARTMENTS_URL = (
    "https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2025/geojson/departements-100m.geojson"
)
DEPARTMENT_CODE = "38"  # Isère

# -------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------


def download_sensitive_areas(url: str) -> gpd.GeoDataFrame:
    """Download the Biodiv'Sports sensitive areas as a GeoDataFrame."""
    response = requests.get(
        url,
        params={
            "format": "geojson",
            "language": "fr",
        },
        timeout=120,
    )
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(
        suffix=".geojson",
        delete=False,
        mode="w",
        encoding="utf-8",
    ) as temp_file:
        temp_file.write(response.text)
        temp_path = temp_file.name

    try:
        areas: gpd.GeoDataFrame = gpd.read_file(temp_path)
    finally:
        os.unlink(temp_path)
    return areas


def load_departments(url: str) -> gpd.GeoDataFrame:
    """Load the French administrative department boundaries."""
    departments: gpd.GeoDataFrame = gpd.read_file(url)
    return departments


def filter_areas_for_department(
    areas: gpd.GeoDataFrame,
    departments: gpd.GeoDataFrame,
    department_code: str,
) -> gpd.GeoDataFrame:
    """Keep the sensitive areas that intersect the requested department."""
    department: gpd.GeoDataFrame = departments[departments["code"] == department_code].copy()

    if areas.crs is None:
        raise ValueError("The sensitive-area GeoJSON has no coordinate reference system.")
    department = department.to_crs(areas.crs)

    areas = areas.copy()
    areas.geometry = areas.geometry.make_valid()
    department.geometry = department.geometry.make_valid()

    department_geometry = department.geometry.union_all()
    return areas[areas.geometry.intersects(department_geometry)]


def plot_areas(
    areas: gpd.GeoDataFrame,
    department: gpd.GeoDataFrame,
) -> None:
    """Plot the sensitive areas inside the department."""
    _, ax = plt.subplots()
    department.plot(
        ax=ax,
        color="#F2F2F2",
        edgecolor="black",
    )
    areas.plot(
        ax=ax,
        color="lightblue",
        edgecolor="blue",
    )
    ax.set_title("Biodiv'Sports sensitive areas in Isère")
    plt.show()


def main() -> None:
    sensitive_areas = download_sensitive_areas(SENSITIVE_AREAS_URL)
    departments = load_departments(DEPARTMENTS_URL)
    isere_areas = filter_areas_for_department(sensitive_areas, departments, DEPARTMENT_CODE)

    print("Number of areas intersecting Isère:", len(isere_areas))

    isere: gpd.GeoDataFrame = departments[departments["code"] == DEPARTMENT_CODE]
    plot_areas(isere_areas, isere)


if __name__ == "__main__":
    main()
