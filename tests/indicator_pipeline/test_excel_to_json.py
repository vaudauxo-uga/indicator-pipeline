import pandas as pd
from indicator_pipeline.excel_to_json import df_to_json_payloads


def test_df_to_json_payloads_basic(monkeypatch):
    monkeypatch.setattr(
        "indicator_pipeline.excel_to_json.parse_patient_and_visit",
        lambda filename: ("1234", "2")
    )

    df = pd.DataFrame([{
        "Filename": "P1234V2",
        "TST": "3,14",
        "n_desat": "42",
        "n_reco": None,
        "ODI": "abc",
        "DesSev": "5.5"
    }])

    payloads = df_to_json_payloads(df)

    assert len(payloads) == 1
    p = payloads[0]

    assert p["patient_id"] == 1234
    assert p["numero_visite"] == 2
    assert p["TST"] == 3.14
    assert p["n_desat"] == 42
    assert p["n_reco"] is None
    assert p["ODI"] is None

    assert isinstance(p["desaturation"], dict)
    assert p["desaturation"]["DesSev"] == 5.5