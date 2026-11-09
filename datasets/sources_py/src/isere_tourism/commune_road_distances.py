# The first part retrieves the communes file from the Insee SSP Cloud
# (Onyxia). Update the access keys according to the file location settings.
#
# The script then fetches the geographic center of each Isère commune and
# builds a road-distance matrix with the OSRM API.

import os
import time
from typing import Any, Final, cast

import numpy as np
import pandas as pd
import pyarrow.fs as pafs
import requests

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

AWS_PROFILE = "default"
S3_REGION = "us-east-1"
S3_ENDPOINT = "minio.lab.sspcloud.fr"
S3_SCHEME: Final = "https"
COMMUNES_S3_PATH = "maximehautin/Communes-d_Isere.csv"

GEO_API_URL = "https://geo.api.gouv.fr"
OSRM_SERVER = "https://router.project-osrm.org"
OSRM_PROFILE = "car"
BLOCK_SIZE = 50

OUTPUT_FILE = "isere_road_distances.xlsx"

# -------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------


def build_s3_filesystem() -> pafs.S3FileSystem:
    """Build the S3 filesystem used to read the SSP Cloud data."""
    os.environ["AWS_PROFILE"] = AWS_PROFILE
    return pafs.S3FileSystem(
        region=S3_REGION,
        endpoint_override=S3_ENDPOINT,
        scheme=S3_SCHEME,
    )


def load_communes(filesystem: pafs.S3FileSystem) -> pd.DataFrame:
    """Load the Isère communes and keep their INSEE code and name."""
    with filesystem.open_input_stream(COMMUNES_S3_PATH) as file:
        dataset = pd.read_csv(file)

    communes = dataset.copy()
    communes.columns = ["insee_code", "municipality"]
    return communes


def fetch_commune_center(code: str) -> dict[str, float]:
    """Fetch the geographic center of a commune from geo.api.gouv.fr."""
    url = f"{GEO_API_URL}/communes/{code}?fields=centre"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    result: dict[str, Any] = response.json()
    return {
        "lon": float(result["centre"]["coordinates"][0]),
        "lat": float(result["centre"]["coordinates"][1]),
    }


def add_commune_centers(communes: pd.DataFrame) -> pd.DataFrame:
    """Add longitude and latitude columns for each commune center."""
    centers: list[dict[str, float]] = []
    for code in communes["insee_code"]:
        time.sleep(0.1)
        centers.append(fetch_commune_center(str(code)))

    centers_dataframe: pd.DataFrame = pd.DataFrame(centers)
    return pd.concat([communes.reset_index(drop=True), centers_dataframe], axis=1)


def fetch_osrm_table(source: pd.DataFrame, destination: pd.DataFrame) -> list[list[float]]:
    """Fetch a distance sub-matrix from the OSRM table service."""
    coordinates = pd.concat(
        [source[["lon", "lat"]], destination[["lon", "lat"]]],
        ignore_index=True,
    )
    coordinate_string = ";".join(
        f"{lon},{lat}" for lon, lat in coordinates[["lon", "lat"]].itertuples(index=False, name=None)
    )
    sources = ";".join(str(index) for index in range(len(source)))
    destinations = ";".join(str(len(source) + index) for index in range(len(destination)))

    url = f"{OSRM_SERVER}/table/v1/{OSRM_PROFILE}/{coordinate_string}"
    response = requests.get(
        url,
        params={
            "sources": sources,
            "destinations": destinations,
            "annotations": "distance",
        },
        timeout=120,
    )
    response.raise_for_status()

    return cast("list[list[float]]", response.json()["distances"])


def build_distance_matrix(communes: pd.DataFrame) -> pd.DataFrame:
    """Build the full road-distance matrix between communes."""
    points = pd.DataFrame(
        {
            "id": communes["municipality"],
            "lon": communes["lon"],
            "lat": communes["lat"],
        }
    )

    count = len(points)
    matrix = pd.DataFrame(
        np.nan,
        index=points["id"],
        columns=points["id"],
    )

    for row_start in range(0, count, BLOCK_SIZE):
        row_end = min(row_start + BLOCK_SIZE, count)
        print("Rows", row_start + 1, "to", row_end)

        for column_start in range(0, count, BLOCK_SIZE):
            column_end = min(column_start + BLOCK_SIZE, count)
            print("Columns", column_start + 1, "to", column_end)

            result = fetch_osrm_table(
                points.iloc[row_start:row_end],
                points.iloc[column_start:column_end],
            )
            matrix.iloc[row_start:row_end, column_start:column_end] = np.array(result)

    return matrix


def export_distance_matrix(matrix: pd.DataFrame, path: str) -> None:
    """Export the distance matrix to an Excel file."""
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        matrix.to_excel(writer, sheet_name="Distances")


def main() -> None:
    filesystem = build_s3_filesystem()
    communes = load_communes(filesystem)
    print(communes.head())

    communes = add_commune_centers(communes)
    distance_matrix = build_distance_matrix(communes)
    export_distance_matrix(distance_matrix, OUTPUT_FILE)


if __name__ == "__main__":
    main()
