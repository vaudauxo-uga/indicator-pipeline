from typing import Dict

DESATURATION_MAP: Dict[str, str] = {
    "DesSev": "des_severity",
    "DesSev100": "des_severity_100",
    "DesDur": "des_duration",
    "avg_des_dur": "avg_des_dur",
    "avg_des_area": "avg_des_area",
    "avg_des_area100": "avg_des_area_100",
    "avg_des_slope": "avg_des_slope",
    "avg_des_depth": "avg_des_depth",
    "avg_des_max": "avg_des_max",
    "avg_des_nadir": "avg_des_nadir",
    "med_des_dur": "med_des_dur",
    "med_des_area": "med_des_area",
    "med_des_area100": "med_des_area_100",
    "med_des_slope": "med_des_slope",
    "med_des_depth": "med_des_depth",
    "med_des_max": "med_des_max",
    "med_des_nadir": "med_des_nadir",
}

RECOVERY_MAP: Dict[str, str] = {
    "RI": "rec_index",
    "RecSev": "rec_severity",
    "RecSev100": "rec_severity_100",
    "RecDur": "rec_duration",
    "avg_reco_dur": "avg_reco_dur",
    "avg_reco_area": "avg_reco_area",
    "avg_reco_area100": "avg_reco_area_100",
    "avg_reco_slope": "avg_reco_slope",
    "avg_reco_depth": "avg_reco_depth",
    "avg_reco_max": "avg_reco_max",
    "avg_reco_nadir": "avg_reco_nadir",
    "med_reco_dur": "med_reco_dur",
    "med_reco_area": "med_reco_area",
    "med_reco_area100": "med_reco_area_100",
    "med_reco_slope": "med_reco_slope",
    "med_reco_depth": "med_reco_depth",
    "med_reco_max": "med_reco_max",
    "med_reco_nadir": "med_reco_nadir",
}

RATIOS_MAP: Dict[str, str] = {
    "avg_duration_ratio": "avg_duration_ratio",
    "avg_depth_ratio": "avg_depth_ratio",
    "avg_area_ratio": "avg_area_ratio",
    "avg_area100_ratio": "avg_area_100_ratio",
    "avg_slope_ratio": "avg_slope_ratio",
    "med_duration_ratio": "med_duration_ratio",
    "med_depth_ratio": "med_depth_ratio",
    "med_area_ratio": "med_area_ratio",
    "med_area100_ratio": "med_area_100_ratio",
    "med_slope_ratio": "med_slope_ratio",
}

SEVERITY_MAP: Dict[str, str] = {
    "TotalSev_integrated": "total_severity_integrated",
    "TotalSev_block": "total_severity_block",
    "TotalSev100": "total_severity_100",
    "TotalDur": "total_duration",
    "total_area_below100": "total_area_below_100",
}

SPO2_MAP: Dict[str, str] = {
    "avg_spO2": "avg_spo2",
    "med_spO2": "med_spo2",
    "max_spO2": "max_spo2",
    "nadir_spO2": "nadir_spo2",
    "variance_spO2": "variance_spo2",
}

TIME_BELOW_THRESHOLDS_MAP: Dict[str, str] = {
    "t100": "t_100",
    "t98": "t_98",
    "t95": "t_95",
    "t92": "t_92",
    "t90": "t_90",
    "t88": "t_88",
    "t85": "t_85",
    "t80": "t_80",
    "t75": "t_75",
    "t70": "t_70",
    "t65": "t_65",
    "t60": "t_60",
    "t55": "t_55",
    "t50": "t_50",
}
