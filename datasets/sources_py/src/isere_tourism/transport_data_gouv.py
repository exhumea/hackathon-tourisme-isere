"""Fetch transport datasets covering the Isère department from the catalog."""

from typing import Any

import pandas as pd
import requests

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

COVERED_AREA: dict[str, str] = {
    "insee": "38",
    "nom": "Isère",
    "type": "departement",
}

DATASETS_API_URL = "https://transport.data.gouv.fr/api/datasets"
HTTP_OK = 200
OUTPUT_FILE = "catalogue_transports_isere.csv"

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------


def dataset_covers_isere(dataset: dict[str, Any]) -> bool:
    """Return True if the dataset covers the Isère department."""
    zones: list[dict[str, Any]] | None = dataset.get("covered_area")
    if not zones:
        return False

    for zone in zones:
        if (
            str(zone.get("insee")) == COVERED_AREA["insee"]
            and str(zone.get("nom")) == COVERED_AREA["nom"]
            and str(zone.get("type")) == COVERED_AREA["type"]
        ):
            return True

    return False


def build_catalog(datasets: list[dict[str, Any]]) -> pd.DataFrame:
    """Build a summary DataFrame of the datasets covering the Isère department."""
    datasets_isere = [dataset for dataset in datasets if dataset_covers_isere(dataset)]
    print(f"Datasets covering Isère: {len(datasets_isere)}")

    return pd.DataFrame(
        [
            {
                "id": str(dataset.get("id")),
                "title": dataset.get("title"),
                "type": dataset.get("type"),
                "url_page": dataset.get("page_url"),
                "number_of_resources": len(dataset.get("resources") or []),
            }
            for dataset in datasets_isere
        ]
    )


def main() -> None:
    response = requests.get(DATASETS_API_URL, timeout=120)
    response.raise_for_status()
    assert response.status_code == HTTP_OK

    datasets: list[dict[str, Any]] = response.json()
    print(f"Total number of datasets: {len(datasets)}")

    resultats = build_catalog(datasets)
    print(resultats)

    resultats.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
