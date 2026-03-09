#!/usr/bin/env python
"""
Extract monitor and detector spectra from EQSANS NeXus files.

Usage:
    python extract_monitor.py <run_number> [--ipts IPTS] [--bins NBINS] [--output OUTPUT]
    
Examples:
    python extract_monitor.py 176475
    python extract_monitor.py 176475 --ipts 37424
    python extract_monitor.py 176475 --bins 2000 --output my_monitor.dat
    python extract_monitor.py 176475 --plot  # Combined monitor + detector plot
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import h5py
import numpy as np


# Chopper configuration from onechopper_diagram.py
CHOPPER_CONFIG = {
    "1a": {"distance": 5.6978, "opening_deg": 129.600},
    "1b": {"distance": 5.7078, "opening_deg": 129.600},
    "2a": {"distance": 7.7978, "opening_deg": 180.000},
    "2b": {"distance": 7.8078, "opening_deg": 180.000},
    "3a": {"distance": 9.4978, "opening_deg": 230.010},
    "3b": {"distance": 9.5078, "opening_deg": 230.007},
}


def parse_chopper_name(title: str) -> Optional[str]:
    """
    Extract chopper name (1a, 1b, 2a, 2b, 3a, 3b) from run title.
    
    Examples:
        "Chopper 1a calibration" -> "1a"
        "Test run 3B" -> "3b"
        "1A chopper scan" -> "1a"
    
    Returns None if no chopper name found.
    """
    if not title:
        return None
    
    # Pattern: look for 1a, 1b, 2a, 2b, 3a, 3b (case insensitive)
    pattern = r'\b([123][aAbB])\b'
    match = re.search(pattern, title)
    if match:
        return match.group(1).lower()
    return None


def parse_phase_delay(title: str) -> Optional[float]:
    """
    Extract phase delay value from run title.
    
    Examples:
        "chopper 1a, phase delay 1000" -> 1000.0
        "chopper 1a 60hz total delay 2000.00" -> 2000.0
    
    Returns None if no delay found.
    """
    if not title:
        return None
    
    # Pattern: "phase delay XXXX" or "total delay XXXX.XX"
    pattern = r'(?:phase|total)\s+delay\s+([\d.]+)'
    match = re.search(pattern, title, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def get_chopper_distance(chopper_name: str) -> Optional[float]:
    if chopper_name and chopper_name.lower() in CHOPPER_CONFIG:
        return CHOPPER_CONFIG[chopper_name.lower()]["distance"]
    return None


@dataclass
class RunMetadata:
    run_number: int
    title: str
    experiment_title: str
    detector_distance_mm: float
    chopper_name: Optional[str] = None
    chopper_distance_m: Optional[float] = None
    phase_delay_us: Optional[float] = None
    
    @property
    def detector_distance_m(self) -> float:
        return self.detector_distance_mm / 1000.0
    
    @property
    def chopper_label(self) -> str:
        parts = []
        if self.chopper_name:
            if self.chopper_distance_m:
                parts.append(f"Chopper {self.chopper_name.upper()} @ {self.chopper_distance_m:.3f} m")
            else:
                parts.append(f"Chopper {self.chopper_name.upper()}")
        if self.phase_delay_us is not None:
            parts.append(f"Phase Delay {self.phase_delay_us:.0f} µs")
        return ", ".join(parts)
    
    @property
    def filename_suffix(self) -> str:
        parts = []
        if self.chopper_name:
            parts.append(self.chopper_name)
        if self.phase_delay_us is not None:
            parts.append(f"pd{int(self.phase_delay_us)}")
        return "_".join(parts) if parts else ""


def extract_metadata(nexus_path: Path) -> RunMetadata:
    """
    Extract run metadata from NeXus file.
    
    Parameters
    ----------
    nexus_path : Path
        Path to the NeXus file
    
    Returns
    -------
    RunMetadata
        Run title, experiment title, detector distance, etc.
    """
    with h5py.File(nexus_path, "r") as f:
        # Extract run number from filename (e.g., EQSANS_176475.nxs.h5)
        stem = nexus_path.stem  # EQSANS_176475.nxs
        if ".nxs" in stem:
            stem = stem.split(".nxs")[0]  # EQSANS_176475
        run_number = int(stem.split("_")[-1])
        
        # Get run title
        title = ""
        if "entry/title" in f:
            title_data = f["entry/title"][()]
            if isinstance(title_data, np.ndarray):
                title_data = title_data[0]
            if isinstance(title_data, bytes):
                title_data = title_data.decode()
            title = title_data
        
        # Get experiment title
        experiment_title = ""
        if "entry/experiment_title" in f:
            exp_data = f["entry/experiment_title"][()]
            if isinstance(exp_data, np.ndarray):
                exp_data = exp_data[0]
            if isinstance(exp_data, bytes):
                exp_data = exp_data.decode()
            experiment_title = exp_data
        
        # Get detector distance (in mm)
        detector_distance_mm = 0.0
        det_z_path = "entry/DASlogs/BL6:Mot:detectorZ/value"
        if det_z_path in f:
            det_z = f[det_z_path][()]
            if isinstance(det_z, np.ndarray):
                det_z = det_z[0]
            detector_distance_mm = float(det_z)
    
    chopper_name = parse_chopper_name(title)
    chopper_distance = get_chopper_distance(chopper_name) if chopper_name else None
    phase_delay = parse_phase_delay(title)
    
    return RunMetadata(
        run_number=run_number,
        title=title,
        experiment_title=experiment_title,
        detector_distance_mm=detector_distance_mm,
        chopper_name=chopper_name,
        chopper_distance_m=chopper_distance,
        phase_delay_us=phase_delay
    )


def extract_detector_spectrum(
    nexus_path: Path,
    n_bins: int = 1000,
    tof_range: Optional[Tuple[float, float]] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract summed detector spectrum from all detector banks.
    
    Parameters
    ----------
    nexus_path : Path
        Path to the NeXus file
    n_bins : int
        Number of TOF bins for histogramming
    tof_range : tuple of (min, max), optional
        TOF range in microseconds. If None, auto-determined from data.
    
    Returns
    -------
    tof_centers : np.ndarray
        TOF bin centers in microseconds
    intensity : np.ndarray
        Summed counts per bin from all detector banks
    """
    all_tof_events = []
    
    with h5py.File(nexus_path, "r") as f:
        # Find all detector banks
        entry = f["entry"]
        bank_names = [k for k in entry.keys() if k.startswith("bank") and k.endswith("_events")]
        
        if not bank_names:
            raise KeyError("No detector banks found in NeXus file")
        
        # Collect TOF events from all banks
        total_counts = 0
        for bank_name in bank_names:
            bank = entry[bank_name]
            if "event_time_offset" in bank:
                events = bank["event_time_offset"][:]
                all_tof_events.append(events)
                total_counts += len(events)
    
    if not all_tof_events:
        raise ValueError("No detector events found")
    
    # Concatenate all events
    event_tof = np.concatenate(all_tof_events)
    
    print(f"Loaded {len(event_tof):,} detector events from {len(bank_names)} banks")
    
    # Determine TOF range
    if tof_range is None:
        tof_min, tof_max = event_tof.min(), event_tof.max()
    else:
        tof_min, tof_max = tof_range
    
    # Create histogram
    bin_edges = np.linspace(tof_min, tof_max, n_bins + 1)
    intensity, _ = np.histogram(event_tof, bins=bin_edges)
    
    # Calculate bin centers
    tof_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    
    print(f"Detector TOF range: {tof_min:.2f} - {tof_max:.2f} µs ({n_bins} bins)")
    
    return tof_centers, intensity


def find_nexus_file(run_number: int, ipts: Optional[int] = None) -> Path:
    """
    Locate the NeXus file for a given run number.
    
    If IPTS is not provided, searches common EQSANS IPTS directories.
    """
    if ipts is not None:
        path = Path(f"/SNS/EQSANS/IPTS-{ipts}/nexus/EQSANS_{run_number}.nxs.h5")
        if path.exists():
            return path
        raise FileNotFoundError(f"NeXus file not found: {path}")
    
    # Search recent IPTS directories
    base = Path("/SNS/EQSANS")
    for ipts_dir in sorted(base.glob("IPTS-*"), reverse=True):
        nexus_file = ipts_dir / "nexus" / f"EQSANS_{run_number}.nxs.h5"
        if nexus_file.exists():
            return nexus_file
    
    raise FileNotFoundError(
        f"Could not find NeXus file for run {run_number}. "
        "Try specifying --ipts explicitly."
    )


def extract_monitor_spectrum(
    nexus_path: Path,
    n_bins: int = 1000,
    monitor_name: str = "monitor1"
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract monitor spectrum from a NeXus file.
    
    The monitor data is stored as events with time-of-flight (TOF) values.
    This function histograms the events into a spectrum.
    
    Parameters
    ----------
    nexus_path : Path
        Path to the NeXus file
    n_bins : int
        Number of TOF bins for histogramming
    monitor_name : str
        Name of the monitor group (default: monitor1)
    
    Returns
    -------
    tof_centers : np.ndarray
        TOF bin centers in microseconds
    intensity : np.ndarray
        Counts per bin
    """
    with h5py.File(nexus_path, "r") as f:
        monitor_path = f"entry/{monitor_name}"
        
        if monitor_path not in f:
            available = [k for k in f["entry"].keys() if "monitor" in k.lower()]
            raise KeyError(
                f"Monitor '{monitor_name}' not found. Available: {available}"
            )
        
        monitor = f[monitor_path]
        
        # Read event TOF data
        event_tof = monitor["event_time_offset"][:]
        
        # Get units (should be microseconds)
        units = monitor["event_time_offset"].attrs.get("units", b"microsecond")
        if isinstance(units, bytes):
            units = units.decode()
        
        if units != "microsecond":
            print(f"Warning: TOF units are '{units}', expected 'microsecond'")
        
        # Get total counts for verification
        total_counts = monitor["total_counts"][0]
        
    print(f"Loaded {len(event_tof):,} monitor events (total_counts: {total_counts:,})")
    
    # Create histogram
    tof_min, tof_max = event_tof.min(), event_tof.max()
    bin_edges = np.linspace(tof_min, tof_max, n_bins + 1)
    intensity, _ = np.histogram(event_tof, bins=bin_edges)
    
    # Calculate bin centers
    tof_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    
    print(f"TOF range: {tof_min:.2f} - {tof_max:.2f} µs ({n_bins} bins)")
    
    return tof_centers, intensity


def save_spectrum(
    tof: np.ndarray,
    intensity: np.ndarray,
    output_path: Path,
    run_number: int,
    title: str = ""
) -> None:
    with open(output_path, "w") as f:
        if title:
            f.write(f"# {title}\n")
        f.write(f"# Run: {run_number}\n")
        f.write("# Columns: tof_us intensity\n")
        for t, i in zip(tof, intensity):
            f.write(f"{t:.6f} {i}\n")
    
    print(f"Saved: {output_path}")


def plot_spectrum(
    tof: np.ndarray,
    intensity: np.ndarray,
    metadata: RunMetadata,
    output_path: Optional[Path] = None,
    show: bool = False
) -> Path:
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(tof, intensity, linewidth=0.8, color="steelblue")
    ax.fill_between(tof, intensity, alpha=0.3, color="steelblue")
    
    ax.set_xlabel("Time of Flight (µs)", fontsize=12)
    ax.set_ylabel("Intensity (counts)", fontsize=12)
    
    title = f"Monitor Spectrum - Run {metadata.run_number}"
    if metadata.chopper_label:
        title += f"\n{metadata.chopper_label}"
    ax.set_title(title, fontsize=14)
    
    ax.grid(True, alpha=0.3, linestyle="--")
    
    total_counts = intensity.sum()
    peak_tof = tof[intensity.argmax()]
    stats_text = f"Total counts: {total_counts:,}\nPeak TOF: {peak_tof:.1f} µs"
    ax.annotate(
        stats_text,
        xy=(0.97, 0.97),
        xycoords="axes fraction",
        ha="right",
        va="top",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8)
    )
    
    plt.tight_layout()
    
    if output_path is None:
        output_path = _build_output_path(metadata, "_monitor.png")
    
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved plot: {output_path}")
    
    if show:
        plt.show()
    else:
        plt.close(fig)
    
    return output_path


def _build_output_path(metadata: RunMetadata, suffix: str) -> Path:
    if metadata.filename_suffix:
        return Path(f"{metadata.run_number}_{metadata.filename_suffix}{suffix}")
    return Path(f"{metadata.run_number}{suffix}")


def plot_combined_spectra(
    monitor_tof: np.ndarray,
    monitor_intensity: np.ndarray,
    detector_tof: np.ndarray,
    detector_intensity: np.ndarray,
    metadata: RunMetadata,
    output_path: Optional[Path] = None,
    show: bool = False
) -> Path:
    """
    Plot both monitor and detector spectra in a single figure with shared TOF axis.
    
    Parameters
    ----------
    monitor_tof : np.ndarray
        Monitor TOF bin centers in microseconds
    monitor_intensity : np.ndarray
        Monitor counts per bin
    detector_tof : np.ndarray
        Detector TOF bin centers in microseconds
    detector_intensity : np.ndarray
        Detector counts per bin
    metadata : RunMetadata
        Run metadata (title, detector distance, etc.)
    output_path : Path, optional
        Output file path (default: <run_number>_spectra.png)
    show : bool
        Whether to display the plot interactively (default: False)
    
    Returns
    -------
    Path
        Path to the saved figure
    """
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 5), sharex=True,
                                    gridspec_kw={'hspace': 0.25})
    
    # Common TOF range for both plots
    tof_min = min(monitor_tof.min(), detector_tof.min())
    tof_max = max(monitor_tof.max(), detector_tof.max())
    
    # === Monitor spectrum (top) ===
    ax1.plot(monitor_tof, monitor_intensity, linewidth=0.6, color="steelblue")
    ax1.fill_between(monitor_tof, monitor_intensity, alpha=0.3, color="steelblue")
    ax1.set_ylabel("Intensity (counts)", fontsize=9)
    ax1.set_xlim(tof_min, tof_max)
    ax1.grid(True, alpha=0.3, linestyle="--")
    ax1.tick_params(labelsize=8)
    
    monitor_title = f"Monitor - Run {metadata.run_number}"
    if metadata.chopper_label:
        monitor_title += f" - {metadata.chopper_label}"
    elif metadata.title:
        monitor_title += f" ({metadata.title})"
    ax1.set_title(monitor_title, fontsize=9)
    
    # Monitor stats
    mon_total = monitor_intensity.sum()
    mon_peak_tof = monitor_tof[monitor_intensity.argmax()]
    ax1.annotate(
        f"Total: {mon_total:,}\nPeak: {mon_peak_tof:.1f} µs",
        xy=(0.98, 0.95), xycoords="axes fraction",
        ha="right", va="top", fontsize=7,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8)
    )
    
    # === Detector spectrum (bottom) ===
    ax2.plot(detector_tof, detector_intensity, linewidth=0.6, color="darkorange")
    ax2.fill_between(detector_tof, detector_intensity, alpha=0.3, color="darkorange")
    ax2.set_xlabel("Time of Flight (µs)", fontsize=9)
    ax2.set_ylabel("Intensity (counts)", fontsize=9)
    ax2.set_xlim(tof_min, tof_max)
    ax2.grid(True, alpha=0.3, linestyle="--")
    ax2.tick_params(labelsize=8)
    
    # Detector title with distance info
    det_title = f"Detector Sum"
    if metadata.detector_distance_mm > 0:
        det_title += f" (Z = {metadata.detector_distance_mm:.0f} mm)"
    ax2.set_title(det_title, fontsize=9)
    
    # Detector stats
    det_total = detector_intensity.sum()
    det_peak_tof = detector_tof[detector_intensity.argmax()] if detector_intensity.max() > 0 else 0
    ax2.annotate(
        f"Total: {det_total:,}\nPeak: {det_peak_tof:.1f} µs",
        xy=(0.98, 0.95), xycoords="axes fraction",
        ha="right", va="top", fontsize=7,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8)
    )
    
    plt.tight_layout()
    
    if output_path is None:
        output_path = _build_output_path(metadata, "_spectra.png")
    
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Saved combined plot: {output_path}")
    
    if show:
        plt.show()
    else:
        plt.close(fig)
    
    return output_path


DEFAULT_IPTS = 37424


def list_runs(ipts: int) -> None:
    """
    List all runs in an IPTS with their titles.
    
    Parameters
    ----------
    ipts : int
        IPTS number
    """
    nexus_dir = Path(f"/SNS/EQSANS/IPTS-{ipts}/nexus")
    
    if not nexus_dir.exists():
        print(f"Error: IPTS directory not found: {nexus_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Find all NeXus files
    nexus_files = sorted(nexus_dir.glob("EQSANS_*.nxs.h5"))
    
    if not nexus_files:
        print(f"No NeXus files found in {nexus_dir}")
        return
    
    print(f"{'Run':<10} {'Title'}")
    print("-" * 60)
    
    for nxs_file in nexus_files:
        try:
            # Extract run number from filename
            stem = nxs_file.stem
            if ".nxs" in stem:
                stem = stem.split(".nxs")[0]
            run_number = int(stem.split("_")[-1])
            
            # Get title from file
            with h5py.File(nxs_file, "r") as f:
                title = ""
                if "entry/title" in f:
                    title_data = f["entry/title"][()]
                    if isinstance(title_data, np.ndarray):
                        title_data = title_data[0]
                    if isinstance(title_data, bytes):
                        title_data = title_data.decode()
                    title = title_data
            
            print(f"{run_number:<10} {title}")
        except Exception as e:
            # Skip files that can't be read
            print(f"{nxs_file.name:<10} <error reading file>")


def main():
    parser = argparse.ArgumentParser(
        description="Extract monitor and detector spectra from EQSANS NeXus files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "run_number",
        type=int,
        nargs="?",
        default=None,
        help="Run number (e.g., 176475)"
    )
    parser.add_argument(
        "--ipts",
        type=int,
        default=DEFAULT_IPTS,
        help=f"IPTS number (default: {DEFAULT_IPTS})"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_runs",
        help="List all runs in the IPTS with their titles"
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=1000,
        help="Number of TOF bins (default: 1000)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: <run_number>_monitor.dat)"
    )
    parser.add_argument(
        "--monitor",
        type=str,
        default="monitor1",
        help="Monitor name (default: monitor1)"
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate and save a plot (combined monitor + detector)"
    )
    parser.add_argument(
        "--plot-output",
        type=str,
        default=None,
        help="Output path for plot (default: <run_number>_spectra.png)"
    )
    parser.add_argument(
        "--detector",
        action="store_true",
        help="Also extract and save detector spectrum"
    )
    
    args = parser.parse_args()
    
    # Handle --list command
    if args.list_runs:
        list_runs(args.ipts)
        return
    
    # Require run_number if not listing
    if args.run_number is None:
        parser.error("run_number is required (or use --list to see available runs)")
    
    # Find NeXus file
    try:
        nexus_path = find_nexus_file(args.run_number, args.ipts)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Reading: {nexus_path}")
    
    metadata = extract_metadata(nexus_path)
    print(f"Run title: {metadata.title}")
    if metadata.chopper_name:
        print(f"Chopper: {metadata.chopper_label}")
    print(f"Detector Z: {metadata.detector_distance_mm:.1f} mm ({metadata.detector_distance_m:.2f} m)")
    
    # Extract monitor spectrum
    try:
        monitor_tof, monitor_intensity = extract_monitor_spectrum(
            nexus_path,
            n_bins=args.bins,
            monitor_name=args.monitor
        )
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = _build_output_path(metadata, "_monitor.dat")
    
    save_spectrum(monitor_tof, monitor_intensity, output_path, args.run_number, title=metadata.title)
    
    # Extract detector spectrum if requested or if plotting
    detector_tof = None
    detector_intensity = None
    if args.detector or args.plot:
        try:
            # Use same TOF range as monitor for consistency
            tof_range = (monitor_tof.min(), monitor_tof.max())
            detector_tof, detector_intensity = extract_detector_spectrum(
                nexus_path,
                n_bins=args.bins,
                tof_range=tof_range
            )
            
            if args.detector:
                det_output = _build_output_path(metadata, "_detector.dat")
                save_spectrum(detector_tof, detector_intensity, det_output, args.run_number)
        except Exception as e:
            print(f"Warning: Could not extract detector spectrum: {e}", file=sys.stderr)
    
    # Generate plot if requested
    if args.plot:
        plot_path = Path(args.plot_output) if args.plot_output else None
        
        if detector_tof is not None and detector_intensity is not None:
            # Combined plot with both spectra
            plot_combined_spectra(
                monitor_tof, monitor_intensity,
                detector_tof, detector_intensity,
                metadata,
                output_path=plot_path
            )
        else:
            plot_spectrum(monitor_tof, monitor_intensity, metadata, output_path=plot_path)


if __name__ == "__main__":
    main()
