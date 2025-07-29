from pathlib import Path

import pytest

from indicator_pipeline.utils import (
    parse_patient_and_visit,
    extract_subject_id_from_filename,
)


@pytest.mark.parametrize("filename, expected", [
    ("PA123_V1", ("123", "1")),
    ("PA001_V02", ("001", "02")),
    ("PA999V3", ("999", "3")),
    ("invalid_filename", ("", "")),
    ("PA_V", ("", "")),
    ("PA22875", ("22875", "")),
])
def test_parse_patient_and_visit(filename, expected):
    assert parse_patient_and_visit(filename) == expected

@pytest.mark.parametrize("filename, expected", [
    (Path("PA123_V1.edf"), "PA123_V1"),
    (Path("PA123V2.edf"), "PA123_V2"),
    (Path("PA3643V3C1.edf"), "PA3643_V3"),
    (Path("PA045.edf"), "PA045"),
    (Path("junk.edf"), "PA"),
])
def test_extract_subject_id_from_filename(filename, expected):
    assert extract_subject_id_from_filename(filename) == expected
