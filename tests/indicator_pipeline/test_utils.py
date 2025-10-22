from pathlib import Path

import pytest

from indicator_pipeline.utils import (
    parse_patient_visit_recording,
    extract_subject_id_from_filename, try_parse_number, parse_recording_number,
)


@pytest.mark.parametrize("filename, expected", [
    ("PA123_V1_FE0001", ("123", "1", "0001")),
    ("PA001_V02_FE34", ("001", "02", "34")),
    ("PA999V3_FE3456", ("999", "3", "3456")),
    ("PA7864_V12FE1734", ("7864", "12", "1734")),
    ("PA_V_FE", ("", "", "")),
    ("PA22875", ("22875", "", "")),
    ("invalid_filename", ("", "", "")),
])
def test_parse_patient_visit_recording(filename, expected):
    assert parse_patient_visit_recording(filename) == expected


@pytest.mark.parametrize("filename, expected", [
    ("FE1234T1-PA123_V1", "1234"),
    ("FE6547-PA001_V02", "6547"),
    ("invalid_filename", ""),
    ("FE1T1-PA657_V1", "1"),
    ("PA3456_V2_FE0001", "0001"),
])
def test_parse_recording_number(filename, expected):
    assert parse_recording_number(filename) == expected


@pytest.mark.parametrize("filename, expected", [
    (Path("FE3520T1-PA123_V1.edf"), "PA123_V1_FE3520"),
    (Path("FE457T1_PA123V2.edf"), "PA123_V2_FE457"),
    (Path("PA3643V3C1.edf"), "PA3643_V3"),
    (Path("FE3456T12-PA6578.edf"), "PA6578_FE3456"),
    (Path("PA045.edf"), "PA045"),
    (Path("junk.edf"), "PA"),
])
def test_extract_subject_id_from_filename(filename, expected):
    assert extract_subject_id_from_filename(filename) == expected


@pytest.mark.parametrize("value,as_int,expected", [
    ("42", True, 42),
    ("3.14", False, 3.14),
    ("3,14", False, 3.14),
    (None, False, None),
    ("abc", True, None)
])
def test_try_parse_number(value, as_int, expected):
    assert try_parse_number(value, as_int) == expected
