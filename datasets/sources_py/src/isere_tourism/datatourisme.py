# =====================================================================
# Import DATAtourisme data (v1 API) into Python
# Documentation: https://api.datatourisme.fr/v1/docs
# =====================================================================

import html
import time
import unicodedata
import warnings
from collections.abc import Sequence
from typing import Any, cast

import folium
import matplotlib.pyplot as plt
import pandas as pd
import requests
from folium.plugins import MarkerCluster
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -------------------------------------------------------------------------
# Configuration (✏️ = change according to your needs)
# -------------------------------------------------------------------------

# ✏️ [1] API KEY --------------------------------------------------------
# Get a key from https://www.datatourisme.fr/utiliser-les-donnees
# A key created for the hackathon is available in the Excel file.
API_KEY = "Ma clé"  # Hackathon key, available in the Excel file

BASE_URL = "https://api.datatourisme.fr/v1"

# ✏️ [2] DATA TYPE (endpoint) -------------------------------------------
#   "catalog"               : all POIs (places, events, routes, products)
#   "placeOfInterest"       : places of interest
#   "entertainmentAndEvent" : events
#   "tour"                  : routes
#   "product"               : products
ENDPOINT = "placeOfInterest"

# ✏️ [2bis] TERRITORY: ALWAYS ISÈRE ------------------------------------
# The filter on the Isère department (INSEE 38) is always applied.
DEPARTMENT_INSEE = "38"

# Optionally restrict the query to some municipalities and/or EPCIs
# (leave None to cover the whole department). Both lists are combined.
# Names are converted to INSEE codes through geo.api.gouv.fr.
MUNICIPALITIES: list[str] | None = None
INTERCOMMUNALITIES: list[str] | None = None
MUNICIPALITY_INSEE_CODES: list[str] | None = None

# ✏️ [3] OTHER FILTERS --------------------------------------------------
# All parameters below are optional: leave None to ignore them.
# Syntax: field[operator]=value, combinable with AND / OR / parentheses.
# Operators: eq, ne, gt, gte, lt, lte, in, nin, between, text, prefix, fuzzy, exists
FILTERS: str | None = "type=Restaurant"

# Full-text search on names and descriptions (only one at a time).
SEARCH: str | None = None

# Geographic search (usually only one of the two at a time).
GEO_DISTANCE: str | None = None  # "lat,lon,radius", e.g. "48.1173,-1.6778,10km"
GEO_BOUNDING: str | None = None  # "top_left_lat,top_left_lon,bottom_right_lat,bottom_right_lon"

# Sort order (e.g. "lastUpdate[desc]", "label", "_score[desc]").
SORT: str | None = None

# Language(s) for text fields: "fr", "fr,en" or "*" for all.
LANGUAGES = "fr"

# ✏️ [4] RETURNED FIELDS ------------------------------------------------
# None = the API default selection (name, type, location, address, contact,
# description, update dates...). If FIELDS is set, it replaces the default.
FIELDS: str | None = None

# ✏️ [5] FINAL TABLE COLUMNS --------------------------------------------
# column_name = "path.in.the.json" (same syntax as the API).
# Several possible paths can be given: the first non-empty one is kept.
COLUMNS: dict[str, str | list[str]] = {
    "uuid": "uuid",
    "name": "label",
    "type": "type",
    "municipality": [
        "isLocatedAt.address.hasAddressCity.label",
        "isLocatedAt.address.addressLocality",
    ],
    "postal_code": "isLocatedAt.address.postalCode",
    "address": "isLocatedAt.address.streetAddress",
    "latitude": "isLocatedAt.geo.latitude",
    "longitude": "isLocatedAt.geo.longitude",
    "updated_at": "lastUpdate",
    # For events (requires FIELDS with takesPlaceAt), uncomment:
    # "start_date": "takesPlaceAt.startDate",
    # "end_date": "takesPlaceAt.endDate",
}

# ✏️ [6] VOLUME AND QUOTA LIMITS ----------------------------------------
# API limits: 1000 requests/hour, ~10 requests/second, 100 results per page.
PAGE_SIZE = 100  # 1 to 100
MAX_PAGES = 5  # safety limit on the number of downloaded pages
PAUSE_SECONDS = 0.2  # delay between two requests

DISPLAY_LANGUAGE = "fr"  # language kept when a field is multilingual

# ✏️ [7] VISUALIZATION ---------------------------------------------------
#   "map"       : interactive map of POIs
#   "bar_chart" : number of POIs per value of a variable
#   "timeline"  : number of events per month (with start_date enabled above)
#   "none"      : no chart
VISUALIZATION = "map"
BAR_CHART_VARIABLE = "municipality"
TOP_N = 15

# ✏️ [8] EXPORT ----------------------------------------------------------
EXPORT_CSV: str | None = None  # e.g. "datatourisme_pois.csv"

GEO_API_URL = "https://geo.api.gouv.fr"

# -------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------


def normalize(text: object) -> str:
    """Return a lowercase, accent-free version of a string."""
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii").lower()


def call_geo_api(path: str, **params: Any) -> Any:
    """Call the geo.api.gouv.fr API and return the decoded JSON response."""
    response = requests.get(
        f"{GEO_API_URL}{path}",
        params={key: value for key, value in params.items() if value is not None},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def municipality_insee_codes(names: Sequence[str]) -> list[str]:
    """Convert municipality names to INSEE codes within the department."""
    codes: list[str] = []
    for name in names:
        response: list[dict[str, Any]] = call_geo_api(
            "/communes",
            nom=name,
            codeDepartement=DEPARTMENT_INSEE,
            fields="nom,code",
            limit=5,
        )
        if not response:
            warnings.warn(
                f"Municipality not found in department {DEPARTMENT_INSEE}: {name}",
                stacklevel=2,
            )
            continue

        exact_matches = [
            index for index, municipality in enumerate(response) if normalize(municipality["nom"]) == normalize(name)
        ]
        choice = exact_matches[0] if exact_matches else 0
        print(f"Municipality '{name}' -> {response[choice]['nom']} ({response[choice]['code']})")
        codes.append(str(response[choice]["code"]))
    return codes


def epci_insee_codes(names: Sequence[str]) -> list[str]:
    """Convert EPCI names to the INSEE codes of their municipalities in Isère."""
    codes: list[str] = []
    for name in names:
        response: list[dict[str, Any]] = call_geo_api(
            "/epcis",
            nom=name,
            codeDepartement=DEPARTMENT_INSEE,
            fields="nom,code",
            limit=5,
        )
        if not response:
            warnings.warn(
                f"Intercommunality not found in department {DEPARTMENT_INSEE}: {name}",
                stacklevel=2,
            )
            continue

        partial_matches = [index for index, epci in enumerate(response) if normalize(name) in normalize(epci["nom"])]
        choice = partial_matches[0] if partial_matches else 0

        other_candidates = ""
        if len(response) > 1:
            other_candidates = " ; other candidates: " + ", ".join(
                epci["nom"] for index, epci in enumerate(response) if index != choice
            )
        print(
            f"Intercommunality '{name}' -> {response[choice]['nom']} "
            f"(SIREN {response[choice]['code']}){other_candidates}"
        )

        municipalities: list[dict[str, Any]] = call_geo_api(
            f"/epcis/{response[choice]['code']}/communes",
            fields="nom,code",
        )
        epci_codes = [
            str(municipality["code"])
            for municipality in municipalities
            if str(municipality["code"]).startswith(DEPARTMENT_INSEE)
        ]
        print(f"  {len(epci_codes)} municipality(ies) kept in Isère")
        codes.extend(epci_codes)
    return codes


def build_final_filter() -> str:
    """Build the final filter: Isère (always) + municipalities + other filters."""
    department_field = "isLocatedAt.address.hasAddressCity.isPartOfDepartment.insee"
    municipality_field = "isLocatedAt.address.hasAddressCity.insee"

    filters = [f"{department_field}[eq]={DEPARTMENT_INSEE}"]

    codes: list[str] = []
    if MUNICIPALITIES is not None:
        codes.extend(municipality_insee_codes(MUNICIPALITIES))
    if INTERCOMMUNALITIES is not None:
        codes.extend(epci_insee_codes(INTERCOMMUNALITIES))
    if MUNICIPALITY_INSEE_CODES is not None:
        codes.extend(MUNICIPALITY_INSEE_CODES)

    codes = list(dict.fromkeys(codes))
    if MUNICIPALITIES is not None or INTERCOMMUNALITIES is not None or MUNICIPALITY_INSEE_CODES is not None:
        if not codes:
            raise ValueError("No municipality found for the requested names: import cancelled.")
        filters.append(f"{municipality_field}[in]={','.join(map(str, codes))}")

    if FILTERS is not None:
        filters.append(f"({FILTERS})")

    return " AND ".join(filters)


def build_request(url: str | None, final_filter: str) -> dict[str, Any]:
    """Build the HTTP request for the first page or the next page."""
    params: dict[str, Any]
    if url is None:
        params = {
            "page_size": PAGE_SIZE,
            "lang": LANGUAGES,
            "filters": final_filter,
            "search": SEARCH,
            "fields": FIELDS,
            "sort": SORT,
            "geo_distance": GEO_DISTANCE,
            "geo_bounding": GEO_BOUNDING,
        }
        params = {key: value for key, value in params.items() if value is not None}
        url = f"{BASE_URL}/{ENDPOINT}"
    else:
        params = {}
        url = url.replace("http://", "https://", 1)

    return {
        "url": url,
        "params": params,
        "headers": {
            "X-API-Key": API_KEY,
            "User-Agent": "Python - DATAtourisme import",
        },
    }


def build_session() -> requests.Session:
    """Build an HTTP session with retries on transient errors."""
    session = requests.Session()
    retry_strategy = Retry(
        total=4,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=0.2,
        allowed_methods=["GET", "POST"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
    return session


def check_response(response: requests.Response) -> None:
    """Raise an HTTPError with the API detail when the response is an error."""
    if response.status_code >= 400:
        try:
            body: Any = response.json()
            if isinstance(body, dict):
                detail = " | ".join(str(value) for value in cast("dict[str, Any]", body).values())
            elif isinstance(body, list):
                detail = " | ".join(str(value) for value in body)
            else:
                detail = str(body)
        except Exception:
            detail = "(no detail returned by the API)"
        raise requests.HTTPError(
            f"{response.status_code} - {detail}",
            response=response,
        )


def fetch_pois(
    session: requests.Session,
    final_filter: str,
) -> list[dict[str, Any]]:
    """Download successive pages by following the API's next link."""
    objects: list[dict[str, Any]] = []
    next_url: str | None = None
    page = 0

    while True:
        page += 1
        response = session.get(**build_request(next_url, final_filter), timeout=60)
        check_response(response)
        body: dict[str, Any] = response.json()

        if page == 1:
            metadata: dict[str, Any] = body.get("meta", {})
            print(f"{metadata.get('total')} results in total, i.e. {metadata.get('total_pages')} pages of {PAGE_SIZE}.")
            if metadata.get("total_pages") is not None and metadata["total_pages"] > MAX_PAGES:
                print(f"Only the first {MAX_PAGES} pages will be downloaded (MAX_PAGES).")

        objects.extend(body.get("objects", []))
        print(f"Page {page}: {len(objects)} POIs accumulated")

        next_url = body.get("meta", {}).get("next")
        if next_url is None or page >= MAX_PAGES:
            break
        time.sleep(PAUSE_SECONDS)

    return objects


def fetch_thesaurus(session: requests.Session, code: str) -> Any:
    """Fetch the values of a thesaurus (useful to build filters)."""
    response = session.get(
        f"{BASE_URL}/thesaurus/{code}",
        headers={"X-API-Key": API_KEY},
        timeout=60,
    )
    check_response(response)
    return response.json()


def flatten_value(value: Any) -> str | None:
    """Turn a JSON value (text, list, multilingual object) into a string."""
    if value is None:
        return None
    if isinstance(value, dict):
        mapping = cast("dict[str, Any]", value)
        if not mapping:
            return None
        key = DISPLAY_LANGUAGE if DISPLAY_LANGUAGE in mapping else next(iter(mapping))
        return flatten_value(mapping[key])
    if isinstance(value, list):
        items = value
        if len(items) == 0:
            return None
        if all(not isinstance(item, (list, dict)) for item in items):
            return " | ".join(str(item) for item in items)
        return flatten_value(items[0])
    return str(value)


def extract_value(poi: dict[str, Any], paths: str | Sequence[str]) -> str | None:
    """Look up 'a.b.c' in a POI, trying several paths when provided."""
    path_list = [paths] if isinstance(paths, str) else paths
    for path in path_list:
        value: Any = poi
        for key in path.split("."):
            if isinstance(value, list):
                items = value
                value = items[0] if items else None
            value = cast("dict[str, Any]", value).get(key) if isinstance(value, dict) else None
            if value is None:
                break
        result = flatten_value(value)
        if result is not None:
            return result
    return None


def to_dataframe(objects: Sequence[dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of POIs to a DataFrame."""
    rows: list[dict[str, str | None]] = [
        {column: extract_value(obj, paths) for column, paths in COLUMNS.items()} for obj in objects
    ]
    dataframe: pd.DataFrame = pd.DataFrame(rows, columns=list(COLUMNS.keys()))
    for column in ["latitude", "longitude"]:
        if column in dataframe.columns:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")
    return dataframe


def plot_map(dataframe: pd.DataFrame) -> None:
    """Display the POIs on an interactive Folium map."""
    geo_dataframe = dataframe.dropna(subset=["latitude", "longitude"])
    if len(geo_dataframe) > 0:
        center = [
            float(geo_dataframe["latitude"].mean()),
            float(geo_dataframe["longitude"].mean()),
        ]
    else:
        center = [46.5, 2.5]

    map_ = folium.Map(location=center, zoom_start=8)
    cluster = MarkerCluster().add_to(map_)

    for _, row in geo_dataframe.iterrows():
        name = html.escape(str(row.get("name", "")))
        municipality = html.escape(str(row.get("municipality", "")))
        folium.CircleMarker(
            location=[float(row["latitude"]), float(row["longitude"])],
            radius=4,
            popup=f"<b>{name}</b><br>{municipality}",
        ).add_to(cluster)

    map_.save("poi_map.html")
    print("Map saved to poi_map.html")


def plot_bar_chart(dataframe: pd.DataFrame) -> None:
    """Display the number of POIs per value of a variable."""
    series = dataframe[BAR_CHART_VARIABLE].dropna().value_counts().head(TOP_N)

    _, ax = plt.subplots()
    series.sort_values().plot.barh(ax=ax, color="steelblue")
    ax.set_xlabel("Number of POIs")
    ax.set_ylabel("")
    ax.set_title(f"POIs by {BAR_CHART_VARIABLE}")
    plt.tight_layout()
    plt.show()


def plot_timeline(dataframe: pd.DataFrame) -> None:
    """Display the number of events per start month."""
    if "start_date" not in dataframe.columns:
        raise ValueError("Enable the start_date column in COLUMNS (and FIELDS with takesPlaceAt).")

    months = pd.to_datetime(
        dataframe["start_date"].astype(str).str[:7] + "-01",
        errors="coerce",
    )
    series = months.dropna().dt.to_period("M").value_counts().sort_index()

    _, ax = plt.subplots()
    series.plot.bar(ax=ax, color="steelblue")
    ax.set_xlabel("")
    ax.set_ylabel("Number of events")
    ax.set_title("Events by start month")
    plt.tight_layout()
    plt.show()


def main() -> None:
    final_filter = build_final_filter()
    print("Filter sent to the API:", final_filter)

    session = build_session()
    raw_pois = fetch_pois(session, final_filter)
    dataframe = to_dataframe(raw_pois)

    print(dataframe)

    if VISUALIZATION == "map":
        plot_map(dataframe)
    elif VISUALIZATION == "bar_chart":
        plot_bar_chart(dataframe)
    elif VISUALIZATION == "timeline":
        plot_timeline(dataframe)

    if EXPORT_CSV is not None:
        dataframe.to_csv(EXPORT_CSV, index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
