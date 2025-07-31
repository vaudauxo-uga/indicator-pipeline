from functools import partial
from pathlib import Path
from typing import Any, Optional, Dict, List

import numpy as np
import pyedflib
from mne.io import read_raw_edf


def read_header_flexible(edf_filepath):
    header = {}
    with open(edf_filepath, mode="rb", buffering=0) as f:
        header["ver"] = int(f.read(8).decode("latin-1"))
        header["patientID"] = f.read(80).decode("latin-1")
        header["recordID"] = f.read(80).decode("latin-1")
        header["startdate"] = f.read(8).decode("latin-1")
        header["starttime"] = f.read(8).decode("latin-1")
        header["bytes"] = int(f.read(8).decode("latin-1"))
        header["reserved"] = f.read(44).decode("latin-1")
        header["records"] = int(f.read(8).decode("latin-1"))
        header["duration"] = float(f.read(8).decode("latin-1"))
        header["ns"] = int(f.read(4).decode("latin-1"))
        header["label"] = [
            f.read(16).decode("latin-1").strip() for _ in range(header["ns"])
        ]
        # header['labels'] = [re.sub('\W', '', label) for label in header['labels']]

        header["transducer"] = [
            f.read(80).decode("latin-1") for _ in range(header["ns"])
        ]
        header["units"] = [f.read(8).decode("latin-1") for _ in range(header["ns"])]
        header["physical_min"] = np.array(
            [float(f.read(8).decode("latin-1")) for _ in range(header["ns"])]
        )
        header["physical_max"] = np.array(
            [float(f.read(8).decode("latin-1")) for _ in range(header["ns"])]
        )
        header["digital_min"] = np.array(
            [int(f.read(8).decode("latin-1")) for _ in range(header["ns"])]
        )
        header["digital_max"] = np.array(
            [int(f.read(8).decode("latin-1")) for _ in range(header["ns"])]
        )
        header["prefilter"] = [
            f.read(80).decode("latin-1") for _ in range(header["ns"])
        ]
        header["samples"] = np.array(
            [int(f.read(8).decode("latin-1")) for _ in range(header["ns"])]
        )
        header["reserved2"] = [
            f.read(32).decode("latin-1") for _ in range(header["ns"])
        ]
    return header


def read_signal_from_path(
    edf_path: str, idx: int, digital: bool = False, dtype: np.dtype = np.float32
) -> np.array:
    with pyedflib.EdfReader(edf_path, annotations_mode=0) as hdl:
        # Read as digital if need to rewrite EDF
        # since otherwise will crash due to shifted values
        # https://github.com/holgern/pyedflib/issues/46
        s = hdl.readSignal(idx, digital=digital)

    return np.array(s).astype(dtype)


def read_edf_export(
    edf_path: Path,
    digital: bool = False,
    ch_names: Optional[list[str]] = None,
    annotations: bool = False,
    dtype: np.dtype = np.float32,
) -> tuple[list[np.array], list[dict[str, Any]], dict[str, Any]]:
    """Reads an EDF file and returns lazy signal loaders, signal headers, and metadata."""

    edf_path_str: str = str(edf_path.resolve())

    # Tell EdfReader not to validate annotations if they will not be used
    if annotations is False:
        annotations_mode = 0
    else:
        annotations_mode = 2

    with pyedflib.EdfReader(edf_path_str, annotations_mode=annotations_mode) as hdl:
        n_chs: int = hdl.signals_in_file

        # Resolve the channel indices if channel names are given
        if ch_names is None:
            # Defaults to all channels
            ch_idx = range(n_chs)
        else:
            # Create a mapping from channel name to channel index
            ch_name_idx_map = {}
            for i in range(n_chs):
                ch_name_idx_map[hdl.getLabel(i).strip()] = i
            ch_idx = [ch_name_idx_map[ch_name] for ch_name in ch_names]

        header: Dict[str, Any] = hdl.getHeader()

        # add annotations to header
        if annotations:
            annotations = hdl.readAnnotations()
            annotations = [[s, d, a] for s, d, a in zip(*annotations)]
            header["annotations"] = annotations

        signal_headers: List[Dict[str, Any]] = []
        s_load_funcs: List = []
        for i in ch_idx:
            s_header: Dict[str, Any] = hdl.getSignalHeader(i)
            fs: float = hdl.samples_in_datarecord(i) / hdl.datarecord_duration
            # Patch the wrongly calculated fs
            s_header["sample_frequency"] = fs
            signal_headers.append(s_header)

            s_func = partial(
                read_signal_from_path,
                edf_path=edf_path_str,
                idx=i,
                digital=digital,
                dtype=dtype,
            )
            s_load_funcs.append(s_func)

    return s_load_funcs, signal_headers, header


## Reading using MNE library


def read_signal_from_path_mne(
    edf_path: str, ch_name: str, dtype: np.dtype = np.float32
) -> np.array:
    signal_raw = read_raw_edf(edf_path, include=ch_name, preload=True, verbose="error")
    s = signal_raw.get_data()
    return np.array(s[0]).astype(dtype)


def read_edf_export_mne(
    edf_path: str,
    ch_names: Optional[list[str]] = None,
    annotations: bool = False,
    dtype: np.dtype = np.float32,
) -> tuple[list[np.array], list[dict[str, Any]], dict[str, Any]]:
    """Read the EDF file and return signals and headers separately.

    Instead of the actual signal, return a function which reads the signal
    when evaluated. This way, all data need not fit into memory.
    """

    header = read_header_flexible(edf_path)
    n_chs = header["ns"]

    if ch_names is None:
        # Defaults to all channels
        ch_idx = range(n_chs)
    else:
        # Create a mapping from channel name to channel index
        ch_name_idx_map = {}
        for i in range(n_chs):
            ch_name_idx_map[header["label"][i]] = i
        ch_idx = [ch_name_idx_map[ch_name] for ch_name in ch_names]

    signal_headers = []
    s_load_funcs = []
    for i in ch_idx:
        if header["label"][i] == "EDF Annotations" and annotations:
            s_header = {}
            fs = header["samples"][i] / header["duration"]
            s_header["sample_frequency"] = fs
            s_header["label"] = header["label"][i]
            s_header["dimension"] = header["units"][i]
            s_header["prefilter"] = header["prefilter"][i]
            s_header["transducer"] = header["transducer"][i]
            signal_headers.append(s_header)

            s_func = partial(
                read_signal_from_path_mne,
                edf_path=edf_path,
                ch_name=header["label"][i],
                dtype=dtype,
            )
            s_load_funcs.append(s_func)

        elif header["label"][i] != "EDF Annotations":
            s_header = {}
            fs = header["samples"][i] / header["duration"]
            s_header["sample_frequency"] = fs
            s_header["label"] = header["label"][i]
            s_header["dimension"] = header["units"][i]
            s_header["prefilter"] = header["prefilter"][i]
            s_header["transducer"] = header["transducer"][i]
            signal_headers.append(s_header)

            s_func = partial(
                read_signal_from_path_mne,
                edf_path=edf_path,
                ch_name=header["label"][i],
                dtype=dtype,
            )
            s_load_funcs.append(s_func)

    return s_load_funcs, signal_headers, header
