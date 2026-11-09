# The first part retrieves the weather file from the Insee SSP Cloud
# (Onyxia). Update the access keys according to the file location settings.
#
# The script filters Météo-France daily data for Isère over two periods:
# 1986-2024 and 1950-1985.

import os
from typing import Any, Final, cast

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.fs as pafs
from pyarrow import csv

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

AWS_PROFILE = "default"
S3_REGION = "us-east-1"
S3_ENDPOINT = "minio.lab.sspcloud.fr"
S3_SCHEME: Final = "https"
WEATHER_S3_PATH = "maximehautin/Q_38_previous-1950-2024_RR-T-Vent.csv.gz"

COLUMNS: list[str] = [
    "NUM_POSTE",
    "NOM_USUEL",
    "LAT",
    "LON",
    "ALTI",
    "AAAAMMJJ",
    "RR",
    "TN",
    "TX",
    "TM",
]

SCHEMA_FIELDS: list[tuple[str, pa.DataType]] = [
    ("NUM_POSTE", pa.string()),
    ("NOM_USUEL", pa.string()),
    ("LAT", pa.float64()),
    ("LON", pa.float64()),
    ("ALTI", pa.float64()),
    ("AAAAMMJJ", pa.int64()),
    ("RR", pa.float64()),
    ("QRR", pa.string()),
    ("TN", pa.float64()),
    ("QTN", pa.string()),
    ("HTN", pa.string()),
    ("QHTN", pa.string()),
    ("TX", pa.float64()),
    ("QTX", pa.string()),
    ("HTX", pa.string()),
    ("QHTX", pa.string()),
    ("TM", pa.float64()),
    ("QTM", pa.string()),
    ("TNTXM", pa.string()),
    ("QTNTXM", pa.string()),
    ("TAMPLI", pa.string()),
    ("QTAMPLI", pa.string()),
    ("TNSOL", pa.string()),
    ("QTNSOL", pa.string()),
    ("TN50", pa.string()),
    ("QTN50", pa.string()),
    ("DG", pa.string()),
    ("QDG", pa.string()),
    ("FFM", pa.string()),
    ("QFFM", pa.string()),
    ("FF2M", pa.string()),
    ("QFF2M", pa.string()),
    ("FXY", pa.string()),
    ("QFXY", pa.string()),
    ("DXY", pa.string()),
    ("QDXY", pa.string()),
    ("HXY", pa.string()),
    ("QHXY", pa.string()),
    ("FXI", pa.string()),
    ("QFXI", pa.string()),
    ("DXI", pa.string()),
    ("QDXI", pa.string()),
    ("HXI", pa.string()),
    ("QHXI", pa.string()),
    ("FXI2", pa.string()),
    ("QFXI2", pa.string()),
    ("DXI2", pa.string()),
    ("QDXI2", pa.string()),
    ("HXI2", pa.string()),
    ("QHXI2", pa.string()),
    ("FXI3S", pa.string()),
    ("QFXI3S", pa.string()),
    ("DXI3S", pa.string()),
    ("QDXI3S", pa.string()),
    ("HXI3S", pa.string()),
    ("QHXI3S", pa.string()),
    ("DRR", pa.string()),
    ("QDRR", pa.string()),
    ("STATUS_FXI3S", pa.string()),
    ("STATUS_DXI3S", pa.string()),
]

SCHEMA: pa.Schema = pa.schema(SCHEMA_FIELDS)

PERIODS: list[tuple[int, int, str]] = [
    (1986, 2024, "weather_1986_2024.csv"),
    (1950, 1985, "weather_1950_1985.csv"),
]

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


def schema_column_types(schema: pa.Schema) -> dict[str, pa.DataType]:
    """Return the column types declared in a PyArrow schema."""
    return {field.name: cast("pa.DataType", field.type) for field in cast("list[pa.Field[Any]]", list(schema))}


def load_dataset(filesystem: pafs.S3FileSystem) -> ds.Dataset:
    """Load the compressed Météo-France CSV file as a PyArrow dataset."""
    return ds.dataset(
        WEATHER_S3_PATH,
        filesystem=filesystem,
        format=ds.CsvFileFormat(
            read_options=csv.ReadOptions(
                skip_rows=1,
                column_names=SCHEMA.names,
            ),
            parse_options=csv.ParseOptions(
                delimiter=";",
            ),
            convert_options=csv.ConvertOptions(
                column_types=schema_column_types(SCHEMA),
            ),
        ),
    )


def filter_dataset(
    dataset: ds.Dataset,
    start_date: int,
    end_date: int,
) -> ds.Dataset:
    """Filter the dataset on a YYYYMMDD date range."""
    return dataset.filter((ds.field("AAAAMMJJ") >= start_date) & (ds.field("AAAAMMJJ") <= end_date))


def export_period(
    dataset: ds.Dataset,
    start_date: int,
    end_date: int,
    output_path: str,
) -> pd.DataFrame:
    """Filter one period, print a preview, and export it to CSV."""
    filtered_dataset = filter_dataset(dataset, start_date, end_date)
    print(filtered_dataset.to_table(columns=COLUMNS).slice(0, 5).to_pandas())

    weather_dataframe: pd.DataFrame = filtered_dataset.to_table(columns=COLUMNS).to_pandas()
    weather_dataframe.to_csv(output_path, index=False)
    return weather_dataframe


def main() -> None:
    filesystem = build_s3_filesystem()
    dataset = load_dataset(filesystem)

    print(dataset.schema)

    for start_date, end_date, output_path in PERIODS:
        export_period(dataset, start_date, end_date, output_path)


if __name__ == "__main__":
    main()
