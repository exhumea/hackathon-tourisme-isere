# -----------------------------------------------------------------------------
# Download the Loopi GTFS data and compute a sample bike route
# -----------------------------------------------------------------------------

import json
import zipfile
from pathlib import Path
from typing import Any, cast

import pandas as pd
import requests

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

GTFS_URL = "https://transport.loopi.fr/api/v1/datas/loopi/gtfs.zip"
GTFS_TOKEN = "m3B0vQvpxi-L1TjwKRaeOQ"  # Hackathon token, available in the Excel file
GTFS_ZIP_PATH = "loopi.zip"
GTFS_EXTRACT_DIR = "loopi_gtfs"

LOOPI_API_URL = "https://api.loopi.fr/1.0"
LOOPI_EMAIL = "hackathon@loopi.fr"
LOOPI_PASSWORD = "Mot de passe"  # Hackathon password, available in the Excel file
START_COORDINATES = [5.72921, 45.164059]  # Cite of l'Arlequin, Grenoble
END_COORDINATES = [5.327656375375591, 45.83711769976123]  # Château d'Amblérieu

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------


def download_gtfs(url: str, token: str) -> None:
    """Download and extract the Loopi GTFS archive."""
    response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=120)
    response.raise_for_status()

    with Path(GTFS_ZIP_PATH).open("wb") as file:
        file.write(response.content)

    with zipfile.ZipFile(GTFS_ZIP_PATH) as archive:
        archive.extractall(GTFS_EXTRACT_DIR)


def load_stops() -> pd.DataFrame:
    """Load the Loopi GTFS stops."""
    return pd.read_csv(f"{GTFS_EXTRACT_DIR}/stops.txt")


def login(base_url: str, email: str, password: str) -> str:
    """Log in to the Loopi API and return the access token."""
    response = requests.post(
        f"{base_url}/user/login",
        json={
            "email": email,
            "password": password,
        },
        timeout=60,
    )
    response.raise_for_status()
    return str(response.json()["accessToken"])


def compute_recommended_route(
    base_url: str,
    token: str,
    coordinates: list[list[float]],
) -> requests.Response:
    """Compute the recommended bike route with the Loopi API."""
    body: dict[str, Any] = {
        "coordinates": coordinates,
        "langue": "fr",
        "type": "velo",
        "steps": True,
        "debug": True,
    }

    response = requests.post(
        f"{base_url}/route/recommande",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=120,
    )
    response.raise_for_status()
    return response


def save_itinerary(itinerary: Any, path: str) -> None:
    """Save the computed itinerary as a JSON file."""
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(itinerary, file, ensure_ascii=False, indent=2)


def main() -> None:
    download_gtfs(GTFS_URL, GTFS_TOKEN)
    stops = load_stops()
    print(f"Number of Loopi stops loaded: {len(stops)}")

    response = compute_recommended_route(
        LOOPI_API_URL,
        login(LOOPI_API_URL, LOOPI_EMAIL, LOOPI_PASSWORD),
        [START_COORDINATES, END_COORDINATES],
    )
    itinerary: Any = response.json()
    save_itinerary(itinerary, "itineraire.json")

    print("HTTP status:", response.status_code)
    if isinstance(itinerary, dict):
        print(cast("dict[str, Any]", itinerary).keys())
    print(json.dumps(itinerary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
