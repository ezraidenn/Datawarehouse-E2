"""The crime extract must keep its output layout regardless of the source."""

from pathlib import Path

import pandas as pd
import pytest

from src import extract_crime

FIXTURE = Path(__file__).parent / "fixtures" / "crime_sample.csv"


@pytest.fixture()
def extracted() -> pd.DataFrame:
    source = dict(extract_crime.CRIME_SOURCE, path=FIXTURE, source_name="fixture")
    return extract_crime.extract(source)


def test_columns_and_order(extracted):
    assert list(extracted.columns) == extract_crime.OUTPUT_COLUMNS


def test_one_row_per_incident_and_unique_id(extracted):
    assert len(extracted) == len(pd.read_csv(FIXTURE))
    assert extracted["source_incident_id"].is_unique


def test_coordinates_are_numeric(extracted):
    assert pd.api.types.is_float_dtype(extracted["latitude"])
    assert pd.api.types.is_float_dtype(extracted["longitude"])
    # the fixture contains one unparseable latitude, kept as missing for the cleaning step
    assert extracted["latitude"].isna().sum() == 1


def test_crime_type_is_normalised(extracted):
    assert (extracted["crime_type"] == extracted["crime_type"].str.strip().str.upper()).all()


def test_hour_range(extracted):
    hours = extracted["incident_hour"].dropna()
    assert hours.between(0, 23).all()
    # '25:00' is out of range and an empty value is missing
    assert extracted["incident_hour"].isna().sum() == 2


def test_no_rows_are_dropped_or_filtered(extracted):
    # the extract does not filter by geography: the point outside Mérida is still present
    assert (extracted["latitude"] > 21.2).any()


def test_missing_source_raises(tmp_path):
    source = dict(extract_crime.CRIME_SOURCE, path=tmp_path / "absent.csv")
    with pytest.raises(FileNotFoundError):
        extract_crime.extract(source)
