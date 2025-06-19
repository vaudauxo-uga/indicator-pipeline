"""Plot signals and annotations."""

import argparse
import logging

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal
import sleeplab_format as slf

from datetime import timedelta
from pathlib import Path


logger = logging.getLogger(__name__)


HYPNOGRAM_CMAP = {
    "W": "tab:olive",
    "N1": "tab:cyan",
    "N2": "tab:pink",
    "N3": "tab:purple",
    "R": "tab:brown",
    "UNSURE": "tab:gray",
    "UNSCORED": "tab:gray",
    "ARTIFACT": "tab:gray",
}

EVENT_CMAP = {
    # ARTIFACT = 'ARTIFACT'
    # # A generic class for unsure
    # UNSURE = 'UNSURE'
    # # Arousal events
    # AROUSAL = 'AROUSAL'
    # AROUSAL_RES = 'AROUSAL_RES'
    # AROUSAL_SPONT = 'AROUSAL_SPONT'
    # AROUSAL_LM = 'AROUSAL_LM'
    # AROUSAL_PLM = 'AROUSAL_PLM'
    # RERA = 'RERA'
    # # Cardiac events
    # # TODO: Add these if a use case ever pops up
    # # Movement events
    # BRUXISM = 'BRUXISM'
    # LM = 'LM'  # Leg movement
    # LM_LEFT = 'LM_LEFT',
    # LM_RIGHT = 'LM_RIGHT',
    # PLM = 'PLM'  # Periodic leg movement
    # PLM_LEFT = 'PLM_LEFT'
    # PLM_RIGHT = 'PLM_RIGHT'
    # Respiratory events
    "APNEA": "tab:red",
    "APNEA_CENTRAL": "tab:red",
    "APNEA_OBSTRUCTIVE": "tab:red",
    "APNEA_MIXED": "tab:red",
    "HYPOPNEA": "tab:blue",
    "HYPOPNEA_CENTRAL": "tab:blue",
    "HYPOPNEA_OBSTRUCTIVE": "tab:blue",
    # 'SPO2_DESAT': 'tab:orange'
    # SNORE = 'SNORE'
}


def scale_y(ax):
    """Scale y-axis when xlim has been"""
    xmin, xmax = ax.get_xlim()
    x, y = ax.lines[0].get_data()
    cond = (x >= xmin) & (x <= xmax)
    y_zoom = y[cond]
    new_ylim = [y_zoom.min(), y_zoom.max()]
    ax.set_ylim(new_ylim)


def resample_polyphase(
    s: np.array, fs: float, fs_new: float, dtype: np.dtype = np.float32
) -> np.array:
    """Resample the signal using scipy.signal.resample_polyphase."""
    # Cast to float64 before filtering
    s = s.astype(np.float64)

    up = int(fs_new)
    down = int(fs)

    resampled = scipy.signal.resample_poly(s, up, down)
    return resampled.astype(dtype)


def plot_subject(
    subject_dir: str,
    start_sec: float = 0.0,
    end_sec: float = -1.0,
    channels: list[str] | None = None,
    annotations: list[str] | None = None,
    interactive: bool = False,
    save_path: str = None,
    resample_fs: float | None = None,
    extra_axes: int = 0,
) -> None:
    """Plot SLF subject."""
    subj = slf.reader.read_subject(Path(subject_dir))
    all_channels = set(list(subj.sample_arrays.keys()))
    if channels is None:
        channels = all_channels
    else:
        channels = set(channels)
        assert set(channels).issubset(
            set(all_channels)
        ), f"{channels - all_channels} not found in {subject_dir}"

    all_annotations = set(list(subj.annotations.keys()))
    if annotations is None:
        annotations = all_annotations
    else:
        annotations = set(annotations)
        assert set(annotations).issubset(
            set(all_annotations)
        ), f"{annotations - all_annotations} not found in {subject_dir}"

    fig, axs = plt.subplots(len(channels) + extra_axes, 1, sharex=True)

    for i, ch in enumerate(sorted(channels)):
        sarr = subj.sample_arrays[ch]
        start_ts = sarr.attributes.start_ts
        fs = sarr.attributes.sampling_rate

        if len(channels) + extra_axes == 1:
            ax = axs
        else:
            ax = axs[i]

        s = np.array(sarr.values)
        if resample_fs is not None:
            logger.info(
                f"Resampling {sarr.attributes.name} from {fs} Hz to {resample_fs} Hz"
            )
            s = resample_polyphase(s, fs, resample_fs)
            fs = resample_fs

        ax.plot(s)
        ax.set_title(ch)
        ax.xaxis.set_major_formatter(
            lambda x, pos: (start_ts + timedelta(seconds=x / fs)).strftime("%H:%M:%S")
        )
        ax.callbacks.connect("xlim_changed", scale_y)

    for ax in axs:
        used_a_names = set()
        for a_key in annotations:

            if "hypnogram" in a_key:
                ymin = 0.95
                ymax = 1.0
                alpha = 0.5
                cmap = HYPNOGRAM_CMAP
            elif "events" in a_key:
                ymin = 0.0
                ymax = 0.95
                alpha = 0.2
                cmap = EVENT_CMAP
            else:
                logger.info(f"Skip unsupported annotation type: {a_key}")
                continue

            a_list = subj.annotations[a_key].annotations
            logger.info(f"Plotting annotations for {a_key}")
            for a in a_list:
                if a.name in cmap.keys():
                    used_a_names.add(a.name)
                    start_idx = fs * a.start_sec
                    end_idx = start_idx + fs * a.duration
                    ax.axvspan(
                        start_idx,
                        end_idx,
                        ymin=ymin,
                        ymax=ymax,
                        facecolor=cmap[a.name],
                        alpha=alpha,
                    )

    hg_patches = [
        matplotlib.patches.Patch(color=v, label=k, alpha=0.5)
        for k, v in HYPNOGRAM_CMAP.items()
        if k in used_a_names
    ]
    axs[0].legend(handles=hg_patches, bbox_to_anchor=(1, 1), loc="upper left")

    event_patches = [
        matplotlib.patches.Patch(color=v, label=k, alpha=0.2)
        for k, v in EVENT_CMAP.items()
        if k in used_a_names
    ]
    axs[1].legend(handles=event_patches, bbox_to_anchor=(1, 1), loc="upper left")

    return fig, axs


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-s", "--subject-dir", required=True, help="Path to the SLF subject"
    )
    parser.add_argument(
        "--start-sec", type=float, default=0.0, help="Start second for the plot"
    )
    parser.add_argument(
        "--end-sec",
        type=float,
        default=-1.0,
        help="End second for the plot. -1.0 signifies end of signal.",
    )
    parser.add_argument(
        "-f",
        "--resample-fs",
        type=float,
        default=None,
        help="Sampling frequency to which all signals are resampled before plotting",
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Plot in interactive mode"
    )
    parser.add_argument("--save-path", nargs="?", help="Optional save path")
    parser.add_argument(
        "-c",
        "--channels",
        nargs="*",
        default=None,
        help="Sample array names to be displayed",
    )
    parser.add_argument(
        "-a",
        "--annotations",
        nargs="*",
        default=None,
        help="Annotation names to be displayed",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    fig, axs = plot_subject(**vars(args))
    plt.show(block=True)
