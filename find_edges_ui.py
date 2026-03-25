#!/usr/bin/env python
"""
Interactive Edge Finder UI for monitor spectrum data.

Features:
- Load monitor spectrum files (.dat format) or directly from NeXus files
- Click on plot to select edge positions for fitting
- Hover to see (x, y) coordinates
- Adjust axis limits interactively
- Fit edges using error function (erf) model
- Phase offset calculator for chopper calibration

Usage:
    python find_edges_ui.py <spectrum_file>
    python find_edges_ui.py 176475_monitor.dat
    python find_edges_ui.py 176475_monitor.dat --window 500

    Or start without a file and use IPTS/Run inputs in the Phase Calculator window
    to load data directly from NeXus files.

Controls:
    Left-click: Add edge guess at clicked position
    Right-click: Remove nearest edge guess
    Mouse hover: Display (x, y) coordinates
    Keyboard 'f': Fit all marked edges
    Keyboard 'c': Clear all edge markers
    Keyboard 'q': Quit
    Keyboard 'l': Set Left E of blade to current mouse X
    Keyboard 'r': Set Right E of blade to current mouse X
"""

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import h5py
import numpy as np
from scipy.optimize import curve_fit
from scipy.special import erf, erfinv

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox, Button, SpanSelector

matplotlib.rcParams['keymap.yscale'] = []
matplotlib.rcParams['keymap.home'] = ['h', 'home']
matplotlib.rcParams['keymap.fullscreen'] = []




def get_boundary_factor(threshold_low: float = 0.05) -> float:
    """Calculate the boundary factor for erf-based edge boundaries."""
    target = 1 - 2 * threshold_low
    return erfinv(target) * np.sqrt(2)


@dataclass
class EdgeResult:
    """Result of edge fitting."""
    position: float
    position_err: float
    width: float
    width_err: float
    amplitude: float
    baseline: float
    edge_type: str
    initial_guess: float
    fit_success: bool
    threshold_low: float = 0.05
    threshold_high: float = 0.95
    
    @property
    def boundary_factor(self) -> float:
        return get_boundary_factor(self.threshold_low)
    
    @property
    def edge_start(self) -> float:
        return self.position - self.boundary_factor * self.width
    
    @property
    def edge_end(self) -> float:
        return self.position + self.boundary_factor * self.width
    
    def __str__(self) -> str:
        direction = "↑" if self.edge_type == "rising" else "↓"
        return (
            f"Edge {direction} at {self.position:.2f} ± {self.position_err:.2f} "
            f"(width: {self.width:.2f} ± {self.width_err:.2f})"
        )


def erf_edge(x: np.ndarray, x0: float, width: float, 
             y_left: float, y_right: float) -> np.ndarray:
    """Error function model for a step edge."""
    return (y_left + y_right) / 2 + (y_right - y_left) / 2 * erf((x - x0) / (width * np.sqrt(2)))


def load_spectrum(filepath: Path) -> Tuple[np.ndarray, np.ndarray, str]:
    title = ""
    with open(filepath) as f:
        first_line = f.readline().strip()
        if first_line.startswith('#'):
            title = first_line.lstrip('#').strip()
    data = np.loadtxt(filepath, comments='#')
    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError(f"Expected 2-column data, got shape {data.shape}")
    return data[:, 0], data[:, 1], title


def estimate_edge_type(x: np.ndarray, y: np.ndarray, 
                       x_guess: float, window: float) -> str:
    """Determine if edge is rising or falling based on local gradient."""
    mask = (x >= x_guess - window) & (x <= x_guess + window)
    if mask.sum() < 3:
        mask = (x >= x_guess - 2*window) & (x <= x_guess + 2*window)
    
    x_local = x[mask]
    y_local = y[mask]
    
    if len(x_local) < 2:
        return "rising"
    
    slope = np.polyfit(x_local, y_local, 1)[0]
    return "rising" if slope > 0 else "falling"


def fit_edge(x: np.ndarray, y: np.ndarray, 
             x_guess: float, window: float) -> EdgeResult:
    """Fit an edge near the initial guess position."""
    mask = (x >= x_guess - window) & (x <= x_guess + window)
    x_fit = x[mask]
    y_fit = y[mask]
    
    if len(x_fit) < 5:
        return EdgeResult(
            position=x_guess, position_err=np.inf,
            width=np.nan, width_err=np.inf,
            amplitude=np.nan, baseline=np.nan,
            edge_type="unknown", initial_guess=x_guess,
            fit_success=False
        )
    
    edge_type = estimate_edge_type(x, y, x_guess, window)
    
    y_left_guess = np.median(y_fit[:len(y_fit)//4]) if len(y_fit) >= 4 else y_fit[0]
    y_right_guess = np.median(y_fit[-len(y_fit)//4:]) if len(y_fit) >= 4 else y_fit[-1]
    width_guess = window / 10
    
    p0 = [x_guess, width_guess, y_left_guess, y_right_guess]
    
    bounds = (
        [x_guess - window, 1e-6, 0, 0],
        [x_guess + window, window, np.inf, np.inf]
    )
    
    try:
        popt, pcov = curve_fit(
            erf_edge, x_fit, y_fit, 
            p0=p0, bounds=bounds,
            maxfev=10000
        )
        
        perr = np.sqrt(np.diag(pcov))
        actual_edge_type = "rising" if popt[3] > popt[2] else "falling"
        
        return EdgeResult(
            position=popt[0],
            position_err=perr[0],
            width=abs(popt[1]),
            width_err=perr[1],
            amplitude=abs(popt[3] - popt[2]),
            baseline=min(popt[2], popt[3]),
            edge_type=actual_edge_type,
            initial_guess=x_guess,
            fit_success=True
        )
        
    except (RuntimeError, ValueError) as e:
        print(f"Warning: Fit failed for edge near {x_guess}: {e}")
        return EdgeResult(
            position=x_guess, position_err=np.inf,
            width=np.nan, width_err=np.inf,
            amplitude=np.nan, baseline=np.nan,
            edge_type=edge_type, initial_guess=x_guess,
            fit_success=False
        )




CHOPPER_CONFIG = {
    "1a": {"distance": 5.6601, "opening_deg": 129.600},
    "1b": {"distance": 5.6758, "opening_deg": 129.600},
    "2a": {"distance": 7.7601, "opening_deg": 180.000},
    "2b": {"distance": 7.7758, "opening_deg": 180.000},
    "3a": {"distance": 9.4978, "opening_deg": 230.010},
    "3b": {"distance": 9.5078, "opening_deg": 230.007},
}

CHOPPER_NAMES = ["1a", "1b", "2a", "2b", "3a", "3b"]

TOF_CONSTANT = 10.006

DEFAULT_IPTS = 37424

FRAME_PERIOD_60HZ = 1e6 / 60.0
FRAME_PERIOD_30HZ = 1e6 / 30.0


@dataclass
class LoadedSpectra:
    """Container for loaded spectra from NeXus file."""
    monitor_tof: np.ndarray
    monitor_intensity: np.ndarray
    detector_tof: Optional[np.ndarray] = None
    detector_intensity: Optional[np.ndarray] = None
    run_number: int = 0
    ipts: int = 0
    title: str = ""
    nexus_path: Optional[Path] = None


def find_nexus_file(run_number: int, ipts: Optional[int] = None) -> Path:
    """Locate the NeXus file for a given run number."""
    if ipts is not None:
        path = Path(f"/SNS/EQSANS/IPTS-{ipts}/nexus/EQSANS_{run_number}.nxs.h5")
        if path.exists():
            return path
        raise FileNotFoundError(f"NeXus file not found: {path}")
    
    base = Path("/SNS/EQSANS")
    for ipts_dir in sorted(base.glob("IPTS-*"), reverse=True):
        nexus_file = ipts_dir / "nexus" / f"EQSANS_{run_number}.nxs.h5"
        if nexus_file.exists():
            return nexus_file
    
    raise FileNotFoundError(
        f"Could not find NeXus file for run {run_number}. "
        "Try specifying IPTS explicitly."
    )


def extract_monitor_spectrum(
    nexus_path: Path,
    n_bins: int = 1000,
    monitor_name: str = "monitor1"
) -> Tuple[np.ndarray, np.ndarray]:
    """Extract monitor spectrum from a NeXus file."""
    with h5py.File(nexus_path, "r") as f:
        monitor_path = f"entry/{monitor_name}"
        
        if monitor_path not in f:
            available = [k for k in f["entry"].keys() if "monitor" in k.lower()]
            raise KeyError(f"Monitor '{monitor_name}' not found. Available: {available}")
        
        monitor = f[monitor_path]
        event_tof = monitor["event_time_offset"][:]
        units = monitor["event_time_offset"].attrs.get("units", b"microsecond")
        if isinstance(units, bytes):
            units = units.decode()
        
        if units != "microsecond":
            print(f"Warning: TOF units are '{units}', expected 'microsecond'")
    
    tof_min, tof_max = event_tof.min(), event_tof.max()
    bin_edges = np.linspace(tof_min, tof_max, n_bins + 1)
    intensity, _ = np.histogram(event_tof, bins=bin_edges)
    tof_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    
    return tof_centers, intensity


def extract_detector_spectrum(
    nexus_path: Path,
    n_bins: int = 1000,
    tof_range: Optional[Tuple[float, float]] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """Extract summed detector spectrum from all detector banks."""
    all_tof_events = []
    
    with h5py.File(nexus_path, "r") as f:
        entry = f["entry"]
        bank_names = [k for k in entry.keys() if k.startswith("bank") and k.endswith("_events")]
        
        if not bank_names:
            raise KeyError("No detector banks found in NeXus file")
        
        for bank_name in bank_names:
            bank = entry[bank_name]
            if "event_time_offset" in bank:
                events = bank["event_time_offset"][:]
                all_tof_events.append(events)
    
    if not all_tof_events:
        raise ValueError("No detector events found")
    
    event_tof = np.concatenate(all_tof_events)
    
    if tof_range is None:
        tof_min, tof_max = event_tof.min(), event_tof.max()
    else:
        tof_min, tof_max = tof_range
    
    bin_edges = np.linspace(tof_min, tof_max, n_bins + 1)
    intensity, _ = np.histogram(event_tof, bins=bin_edges)
    tof_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    
    return tof_centers, intensity


def extract_run_title(nexus_path: Path) -> str:
    """Extract run title from NeXus file."""
    with h5py.File(nexus_path, "r") as f:
        if "entry/title" in f:
            title_data = f["entry/title"][()]
            if isinstance(title_data, np.ndarray):
                title_data = title_data[0]
            if isinstance(title_data, bytes):
                title_data = title_data.decode()
            return title_data
    return ""


def save_spectrum_file(
    tof: np.ndarray,
    intensity: np.ndarray,
    output_path: Path,
    run_number: int,
    title: str = ""
) -> None:
    """Save spectrum to ASCII file."""
    with open(output_path, "w") as f:
        if title:
            f.write(f"# {title}\n")
        f.write(f"# Run: {run_number}\n")
        f.write("# Columns: tof_us intensity\n")
        for t, i in zip(tof, intensity):
            f.write(f"{t:.6f} {i}\n")


def _patch_textbox(tb):
    def _fast_rendercursor(self=tb):
        if self.ax.figure._get_renderer() is None:
            self.ax.figure.canvas.draw()
            return
        text = self.text_disp.get_text()
        widthtext = text[:self.cursor_index]
        bb_text = self.text_disp.get_window_extent()
        self.text_disp.set_text(widthtext or ",")
        bb_widthtext = self.text_disp.get_window_extent()
        if bb_text.y0 == bb_text.y1:
            bb_text.y0 -= bb_widthtext.height / 2
            bb_text.y1 += bb_widthtext.height / 2
        elif not widthtext:
            bb_text.x1 = bb_text.x0
        else:
            bb_text.x1 = bb_text.x0 + bb_widthtext.width
        self.cursor.set(
            segments=[[(bb_text.x1, bb_text.y0), (bb_text.x1, bb_text.y1)]],
            visible=True)
        self.text_disp.set_text(text)
        self.ax.figure.canvas.draw_idle()
    tb._rendercursor = _fast_rendercursor


class PhaseCalcWindow:

    def __init__(self, on_load_callback: Optional[Callable[[LoadedSpectra], None]] = None,
                 mode_30hz: bool = False):
        import tkinter as tk
        self._tk = tk
        self.selected_chopper = "1a"
        self.on_load_callback = on_load_callback
        self.loaded_spectra: Optional[LoadedSpectra] = None
        self.mode_30hz = mode_30hz
        self.frame_period = FRAME_PERIOD_30HZ if mode_30hz else FRAME_PERIOD_60HZ

        self.root = tk.Toplevel()
        title = "Phase Offset Calculator"
        if mode_30hz:
            title += "  [30 Hz MODE]"
        self.root.title(title)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._alive = True

        self._build(tk)

    def _on_close(self):
        self._alive = False
        self.root.destroy()

    def _build(self, tk):
        PAD = dict(padx=6, pady=3)

        # === Row 0: IPTS / Run / Load / Export ===
        tk.Label(self.root, text="IPTS:", font=("", 10)).grid(
            row=0, column=0, sticky="e", **PAD)
        self._ipts_var = tk.StringVar(value=str(DEFAULT_IPTS))
        tk.Entry(self.root, textvariable=self._ipts_var, width=8).grid(
            row=0, column=1, sticky="w", **PAD)

        tk.Label(self.root, text="Run:", font=("", 10)).grid(
            row=0, column=2, sticky="e", **PAD)
        self._run_var = tk.StringVar(value="")
        tk.Entry(self.root, textvariable=self._run_var, width=10).grid(
            row=0, column=3, sticky="w", **PAD)

        tk.Button(self.root, text="Load", font=("", 9, "bold"),
                  bg="#2196F3", fg="white", command=self._on_load).grid(
            row=0, column=4, padx=6)
        tk.Button(self.root, text="Export Spectrum", font=("", 9),
                  command=self._on_export).grid(
            row=0, column=5, padx=6)

        self._load_status_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self._load_status_var,
                 fg="#666666", font=("", 8)).grid(
            row=0, column=6, sticky="w", padx=6)

        # === Row 1: Chopper selector ===
        tk.Label(self.root, text="Chopper:", font=("", 10, "bold")).grid(
            row=1, column=0, sticky="w", **PAD)

        btn_frame = tk.Frame(self.root)
        btn_frame.grid(row=1, column=1, columnspan=6, sticky="w", pady=3)

        self._chopper_btns = {}
        for i, name in enumerate(CHOPPER_NAMES):
            cfg = CHOPPER_CONFIG[name]
            label = f"{name}\n{cfg['opening_deg']:.1f}°\n{cfg['distance']:.4f} m"
            bg = "#4CAF50" if name == self.selected_chopper else "#dddddd"
            btn = tk.Button(btn_frame, text=label, bg=bg, font=("", 8),
                            width=10, relief="raised",
                            command=lambda n=name: self._select_chopper(n))
            btn.grid(row=0, column=i, padx=2)
            self._chopper_btns[name] = btn

        # === Row 2: Status ===
        self._status_var = tk.StringVar(value=self._status_text())
        tk.Label(self.root, textvariable=self._status_var,
                 fg="#1a5f1a", font=("", 9)).grid(
            row=2, column=0, columnspan=7, sticky="w", **PAD)

        # === Row 3: Separator ===
        sep = tk.Frame(self.root, height=2, bg="#cccccc")
        sep.grid(row=3, column=0, columnspan=7, sticky="ew", pady=4)

        # === Row 4: Left edge inputs ===
        tk.Label(self.root, text="Left E of blade [l]",
                 font=("", 9, "bold")).grid(row=4, column=0, sticky="e", **PAD)
        self._left_var = tk.StringVar(value="0")
        left_frame = tk.Frame(self.root)
        left_frame.grid(row=4, column=1, **PAD)
        tk.Button(left_frame, text="−", width=2, font=("", 9),
                  command=lambda: self._shift_var(self._left_var, -self.frame_period)).pack(side="left")
        tk.Entry(left_frame, textvariable=self._left_var, width=10).pack(side="left")
        tk.Button(left_frame, text="+", width=2, font=("", 9),
                  command=lambda: self._shift_var(self._left_var, +self.frame_period)).pack(side="left")

        tk.Label(self.root, text="Current offset",
                 font=("", 9)).grid(row=4, column=2, sticky="e", **PAD)
        self._left_offset_var = tk.StringVar(value="0")
        tk.Entry(self.root, textvariable=self._left_offset_var, width=12).grid(
            row=4, column=3, **PAD)

        self._left_ogc_var    = tk.StringVar(value="OGC: —")
        self._left_phase_var  = tk.StringVar(value="Phase offset: —")
        self._left_frame_var  = tk.StringVar(value="+frame: —")
        tk.Label(self.root, textvariable=self._left_ogc_var,
                 bg="#fffde7", relief="groove", width=14).grid(row=4, column=4, **PAD)
        tk.Label(self.root, textvariable=self._left_phase_var,
                 bg="#fffde7", relief="groove", width=18).grid(row=4, column=5, **PAD)
        tk.Label(self.root, textvariable=self._left_frame_var,
                 bg="#e8f5e9", relief="groove", width=18).grid(row=4, column=6, **PAD)

        # === Row 5: Right edge inputs ===
        tk.Label(self.root, text="Right E of blade [r]",
                 font=("", 9, "bold")).grid(row=5, column=0, sticky="e", **PAD)
        self._right_var = tk.StringVar(value="0")
        right_frame = tk.Frame(self.root)
        right_frame.grid(row=5, column=1, **PAD)
        tk.Button(right_frame, text="−", width=2, font=("", 9),
                  command=lambda: self._shift_var(self._right_var, -self.frame_period)).pack(side="left")
        tk.Entry(right_frame, textvariable=self._right_var, width=10).pack(side="left")
        tk.Button(right_frame, text="+", width=2, font=("", 9),
                  command=lambda: self._shift_var(self._right_var, +self.frame_period)).pack(side="left")

        tk.Label(self.root, text="Current offset",
                 font=("", 9)).grid(row=5, column=2, sticky="e", **PAD)
        self._right_offset_var = tk.StringVar(value="0")
        tk.Entry(self.root, textvariable=self._right_offset_var, width=12).grid(
            row=5, column=3, **PAD)

        self._right_ogc_var   = tk.StringVar(value="OGC: —")
        self._right_phase_var = tk.StringVar(value="Phase offset: —")
        self._right_frame_var = tk.StringVar(value="+frame: —")
        tk.Label(self.root, textvariable=self._right_ogc_var,
                 bg="#fffde7", relief="groove", width=14).grid(row=5, column=4, **PAD)
        tk.Label(self.root, textvariable=self._right_phase_var,
                 bg="#fffde7", relief="groove", width=18).grid(row=5, column=5, **PAD)
        tk.Label(self.root, textvariable=self._right_frame_var,
                 bg="#e8f5e9", relief="groove", width=18).grid(row=5, column=6, **PAD)

        # === Row 6: Capture status ===
        self._capture_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self._capture_var,
                 fg="darkred", font=("", 9)).grid(
            row=6, column=0, columnspan=7, sticky="w", **PAD)

        for sv in (self._left_var, self._left_offset_var):
            sv.trace_add("write", lambda *_: self._recalc_left())
        for sv in (self._right_var, self._right_offset_var):
            sv.trace_add("write", lambda *_: self._recalc_right())

    def _status_text(self):
        cfg = CHOPPER_CONFIG[self.selected_chopper]
        return (f"Selected: {self.selected_chopper}  |  "
                f"Distance: {cfg['distance']:.4f} m  |  "
                f"Opening: {cfg['opening_deg']:.3f}°")

    def _shift_var(self, var, delta: float):
        try:
            var.set(f"{float(var.get()) + delta:.2f}")
        except ValueError:
            pass

    def _select_chopper(self, name):
        self.selected_chopper = name
        for n, btn in self._chopper_btns.items():
            btn.configure(bg="#4CAF50" if n == name else "#dddddd")
        self._status_var.set(self._status_text())
        self._recalc_left()
        self._recalc_right()

    def _recalc_left(self):
        try:
            left_edge  = float(self._left_var.get())
            cur_offset = float(self._left_offset_var.get())
        except ValueError:
            self._left_ogc_var.set("OGC: —")
            self._left_phase_var.set("Phase offset: —")
            self._left_frame_var.set("+frame: —")
            return
        cfg = CHOPPER_CONFIG[self.selected_chopper]
        half_open_tof = (cfg["opening_deg"] / 360.0) * self.frame_period / 2.0
        ogc = cfg["distance"] * left_edge / TOF_CONSTANT - half_open_tof
        phase_offset = cur_offset - ogc
        self._left_ogc_var.set(f"OGC: {ogc:.2f} µs")
        self._left_phase_var.set(f"Phase offset: {phase_offset:.2f} µs")
        self._left_frame_var.set(f"+frame: {phase_offset + self.frame_period:.2f} µs")

    def _recalc_right(self):
        try:
            right_edge = float(self._right_var.get())
            cur_offset = float(self._right_offset_var.get())
        except ValueError:
            self._right_ogc_var.set("OGC: —")
            self._right_phase_var.set("Phase offset: —")
            self._right_frame_var.set("+frame: —")
            return
        cfg = CHOPPER_CONFIG[self.selected_chopper]
        half_open_tof = (cfg["opening_deg"] / 360.0) * self.frame_period / 2.0
        ogc = cfg["distance"] * right_edge / TOF_CONSTANT + half_open_tof
        phase_offset = cur_offset - ogc
        self._right_ogc_var.set(f"OGC: {ogc:.2f} µs")
        self._right_phase_var.set(f"Phase offset: {phase_offset:.2f} µs")
        self._right_frame_var.set(f"+frame: {phase_offset + self.frame_period:.2f} µs")

    def set_left_edge(self, value: float):
        self._left_var.set(f"{value:.2f}")
        self._capture_var.set(f"Left E of blade set to {value:.2f} µs")

    def set_right_edge(self, value: float):
        self._right_var.set(f"{value:.2f}")
        self._capture_var.set(f"Right E of blade set to {value:.2f} µs")

    def _on_load(self):
        try:
            ipts = int(self._ipts_var.get())
            run_number = int(self._run_var.get())
        except ValueError:
            self._load_status_var.set("Enter valid IPTS and Run")
            return

        self._load_status_var.set("Loading...")
        self.root.update()

        try:
            nexus_path = find_nexus_file(run_number, ipts)
            self._load_status_var.set(f"Reading {nexus_path.name}...")
            self.root.update()

            monitor_tof, monitor_intensity = extract_monitor_spectrum(nexus_path, n_bins=1000)

            detector_tof = None
            detector_intensity = None
            try:
                tof_range = (monitor_tof.min(), monitor_tof.max())
                detector_tof, detector_intensity = extract_detector_spectrum(
                    nexus_path, n_bins=1000, tof_range=tof_range)
            except Exception:
                pass

            title = extract_run_title(nexus_path)

            self.loaded_spectra = LoadedSpectra(
                monitor_tof=monitor_tof,
                monitor_intensity=monitor_intensity,
                detector_tof=detector_tof,
                detector_intensity=detector_intensity,
                run_number=run_number,
                ipts=ipts,
                title=title,
                nexus_path=nexus_path
            )

            self._load_status_var.set(f"Run {run_number} loaded")

            if self.on_load_callback:
                self.on_load_callback(self.loaded_spectra)

        except FileNotFoundError as e:
            self._load_status_var.set(f"File not found")
        except Exception as e:
            self._load_status_var.set(f"Error: {e}")

    def _on_export(self):
        if self.loaded_spectra is None:
            self._load_status_var.set("No data loaded")
            return

        spectra = self.loaded_spectra
        base_name = f"{spectra.run_number}"

        monitor_path = Path(f"{base_name}_monitor.dat")
        save_spectrum_file(
            spectra.monitor_tof,
            spectra.monitor_intensity,
            monitor_path,
            spectra.run_number,
            spectra.title
        )

        if spectra.detector_tof is not None and spectra.detector_intensity is not None:
            detector_path = Path(f"{base_name}_detector.dat")
            save_spectrum_file(
                spectra.detector_tof,
                spectra.detector_intensity,
                detector_path,
                spectra.run_number,
                spectra.title
            )
            self._load_status_var.set(f"Saved {monitor_path.name}, {detector_path.name}")
        else:
            self._load_status_var.set(f"Saved {monitor_path.name}")


class EdgeFinderUI:

    def __init__(self, x: np.ndarray, y: np.ndarray,
                 window: float = 500.0,
                 filename: str = "",
                 run_title: str = "",
                 mode_30hz: bool = False):
        self.x = x
        self.y = y
        self.window = window
        self.filename = filename
        self.run_title = run_title
        self.mode_30hz = mode_30hz

        self.edge_guesses: List[float] = []
        self.edge_results: List[EdgeResult] = []

        self.guess_markers = []
        self.fit_lines = []
        self.fit_regions = []
        self.boundary_lines = []

        self.selected_chopper: str = "1a"
        self._mouse_x: float = 0.0
        self._capture_next_mouse_to_left_edge: bool = False
        self._log_scale: bool = False
        self._last_motion_time: float = 0.0

        self.calc_window = PhaseCalcWindow(on_load_callback=self._on_spectra_loaded,
                                           mode_30hz=mode_30hz)
        self.setup_figure()

    def _on_spectra_loaded(self, spectra: LoadedSpectra):
        self.x = spectra.monitor_tof
        self.y = spectra.monitor_intensity
        self.filename = f"IPTS-{spectra.ipts}/EQSANS_{spectra.run_number}.nxs.h5"
        self.run_title = spectra.title

        self.edge_guesses = []
        self.edge_results = []

        for marker in self.guess_markers:
            marker.remove()
        self.guess_markers = []

        self.clear_fit_display()

        self.spectrum_line.set_data(self.x, self.y)

        self.ax.relim()
        self.ax.autoscale()

        title_line1 = 'Interactive Edge Finder'
        if self.mode_30hz:
            title_line1 += '  [30 Hz MODE]'
        if self.filename:
            title_line1 += '  |  ' + self.filename
        title_line2 = self.run_title if self.run_title else ''
        if title_line2:
            self.ax.set_title(title_line1 + '\n' + title_line2, fontsize=12)
        else:
            self.ax.set_title(title_line1, fontsize=12)

        self.textbox_xmin.set_val(f'{self.x.min():.0f}')
        self.textbox_xmax.set_val(f'{self.x.max():.0f}')
        self.textbox_ymin.set_val(f'{self.y.min():.0f}')
        self.textbox_ymax.set_val(f'{self.y.max() * 1.1:.0f}')

        self.update_results_text()
        self.fig.canvas.draw_idle()

    def setup_figure(self):
        self.fig = plt.figure(figsize=(11.2, 6.2))
        self.ax = self.fig.add_axes([0.08, 0.20, 0.60, 0.65])

        self.spectrum_line, = self.ax.plot(self.x, self.y, 'b-', linewidth=0.8,
                                            alpha=0.7, label='Data')

        self.ax.set_xlabel('Time of Flight (µs)', fontsize=12)
        self.ax.set_ylabel('Intensity (counts)', fontsize=12)
        title_line1 = 'Interactive Edge Finder'
        if self.mode_30hz:
            title_line1 += '  [30 Hz MODE]'
        if self.filename:
            title_line1 += '  |  ' + self.filename
        title_line2 = self.run_title if self.run_title else ''
        if title_line2:
            self.ax.set_title(title_line1 + '\n' + title_line2, fontsize=12)
        else:
            self.ax.set_title(title_line1, fontsize=12)
        self.ax.grid(True, alpha=0.3, linestyle='--')

        self.coord_text = self.ax.text(0.02, 0.98, '', transform=self.ax.transAxes,
                                        fontsize=10, verticalalignment='top',
                                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        self.results_text = self.fig.text(0.70, 0.83, '', fontsize=8,
                                          verticalalignment='top',
                                          family='monospace')

        instructions = (
            "Left-click: add marker  |  Right-click: remove  |  "
            "'f': fit  'c': clear  's': save  'g': log/lin  'l': Left E of blade  'r': Right E of blade  'q': quit"
        )
        self.fig.text(0.5, 0.97, instructions, fontsize=9,
                     horizontalalignment='center', verticalalignment='top',
                     bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

        self.setup_controls()
        self.connect_events()

        try:
            self.fig.canvas.get_tk_widget().winfo_toplevel().master.iconify()
        except Exception:
            pass

    def setup_controls(self):
        ax_xmin = self.fig.add_axes([0.10, 0.09, 0.10, 0.035])
        ax_xmax = self.fig.add_axes([0.28, 0.09, 0.10, 0.035])
        ax_ymin = self.fig.add_axes([0.52, 0.09, 0.10, 0.035])
        ax_ymax = self.fig.add_axes([0.70, 0.09, 0.10, 0.035])
        ax_window = self.fig.add_axes([0.10, 0.04, 0.10, 0.035])

        self.textbox_xmin = TextBox(ax_xmin, 'X min:', initial=f'{self.x.min():.0f}')
        self.textbox_xmax = TextBox(ax_xmax, 'X max:', initial=f'{self.x.max():.0f}')
        self.textbox_ymin = TextBox(ax_ymin, 'Y min:', initial=f'{self.y.min():.0f}')
        self.textbox_ymax = TextBox(ax_ymax, 'Y max:', initial=f'{self.y.max() * 1.1:.0f}')
        self.textbox_window = TextBox(ax_window, 'Window µs:', initial=f'{self.window:.0f}')

        self.textbox_xmin.on_submit(self.update_xlim)
        self.textbox_xmax.on_submit(self.update_xlim)
        self.textbox_ymin.on_submit(self.update_ylim)
        self.textbox_ymax.on_submit(self.update_ylim)
        self.textbox_window.on_submit(self.update_window)

        ax_fit       = self.fig.add_axes([0.28, 0.04, 0.07, 0.035])
        ax_clear     = self.fig.add_axes([0.37, 0.04, 0.07, 0.035])
        ax_save      = self.fig.add_axes([0.46, 0.04, 0.07, 0.035])
        ax_autoscale = self.fig.add_axes([0.55, 0.04, 0.09, 0.035])
        ax_loglin    = self.fig.add_axes([0.65, 0.04, 0.09, 0.035])

        self.btn_fit       = Button(ax_fit,       'Fit (f)')
        self.btn_clear     = Button(ax_clear,     'Clear (c)')
        self.btn_save      = Button(ax_save,      'Save (s)')
        self.btn_autoscale = Button(ax_autoscale, 'Autoscale')
        self.btn_loglin    = Button(ax_loglin,    'Log/Lin (g)')

        self.btn_fit.on_clicked(self.fit_edges)
        self.btn_clear.on_clicked(self.clear_all)
        self.btn_save.on_clicked(self.save_results)
        self.btn_autoscale.on_clicked(self.autoscale)
        self.btn_loglin.on_clicked(self.toggle_log_scale)

        for tb in [self.textbox_xmin, self.textbox_xmax,
                   self.textbox_ymin, self.textbox_ymax,
                   self.textbox_window]:
            _patch_textbox(tb)

    def toggle_log_scale(self, event=None):
        self._log_scale = not self._log_scale
        self.ax.set_yscale('log' if self._log_scale else 'linear')
        self.btn_loglin.label.set_text('Linear (g)' if self._log_scale else 'Log/Lin (g)')
        self.fig.canvas.draw_idle()

    def connect_events(self):
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)

    def on_motion(self, event):
        now = time.monotonic()
        if now - self._last_motion_time < 0.05:
            if event.inaxes == self.ax and event.xdata is not None:
                self._mouse_x = event.xdata
            return
        self._last_motion_time = now

        if event.inaxes == self.ax:
            x_pos = event.xdata
            y_pos = event.ydata
            self._mouse_x = x_pos

            idx = np.argmin(np.abs(self.x - x_pos))
            self.coord_text.set_text(
                f'Cursor: ({x_pos:.1f}, {y_pos:.1f})\n'
                f'Data:   ({self.x[idx]:.1f}, {self.y[idx]:.1f})'
            )
        else:
            self.coord_text.set_text('')
        self.fig.canvas.draw_idle()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        if event.button == 1:
            x_pos = event.xdata
            self.add_edge_guess(x_pos)
        elif event.button == 3:
            if self.edge_guesses:
                self.remove_nearest_guess(event.xdata)

    def on_key(self, event):
        if event.key == 'f':
            self.fit_edges(None)
        elif event.key == 'c':
            self.clear_all(None)
        elif event.key == 's':
            self.save_results(None)
        elif event.key == 'g':
            self.toggle_log_scale()
        elif event.key == 'q':
            plt.close(self.fig)
        elif event.key == 'l':
            if event.inaxes == self.ax and event.xdata is not None:
                self._mouse_x = event.xdata
            if self.calc_window._alive:
                self.calc_window.set_left_edge(self._mouse_x)
        elif event.key == 'r':
            if event.inaxes == self.ax and event.xdata is not None:
                self._mouse_x = event.xdata
            if self.calc_window._alive:
                self.calc_window.set_right_edge(self._mouse_x)
            
    def add_edge_guess(self, x_pos: float):
        """Add an edge guess marker."""
        self.edge_guesses.append(x_pos)
        
        # Add vertical line marker
        line = self.ax.axvline(x_pos, color='red', linestyle='--', 
                               alpha=0.7, linewidth=1.5)
        self.guess_markers.append(line)
        
        # Add marker number
        marker_num = len(self.edge_guesses)
        text = self.ax.text(x_pos, self.ax.get_ylim()[1] * 0.95, 
                           f'{marker_num}', color='red', fontsize=10,
                           ha='center', va='top',
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
        self.guess_markers.append(text)
        
        self.update_results_text()
        self.fig.canvas.draw_idle()
        print(f"Added edge guess at {x_pos:.1f} µs (#{marker_num})")
        
    def remove_nearest_guess(self, x_pos: float):
        """Remove the nearest edge guess."""
        if not self.edge_guesses:
            return
            
        # Find nearest guess
        distances = [abs(g - x_pos) for g in self.edge_guesses]
        idx = np.argmin(distances)
        removed_pos = self.edge_guesses[idx]
        
        self.edge_guesses.pop(idx)
        
        # Clear and redraw all markers
        self.redraw_markers()
        
        self.update_results_text()
        self.fig.canvas.draw_idle()
        print(f"Removed edge guess at {removed_pos:.1f} µs")
        
    def redraw_markers(self):
        """Redraw all edge guess markers."""
        for marker in self.guess_markers:
            marker.remove()
        self.guess_markers = []
        
        # Redraw markers with correct numbering
        for i, x_pos in enumerate(self.edge_guesses, 1):
            line = self.ax.axvline(x_pos, color='red', linestyle='--', 
                                   alpha=0.7, linewidth=1.5)
            self.guess_markers.append(line)
            
            text = self.ax.text(x_pos, self.ax.get_ylim()[1] * 0.95, 
                               f'{i}', color='red', fontsize=10,
                               ha='center', va='top',
                               bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
            self.guess_markers.append(text)
            
    def fit_edges(self, event):
        """Fit all marked edges."""
        if not self.edge_guesses:
            print("No edge guesses to fit. Click on the plot to add markers.")
            return
            
        # Clear previous fit results display
        self.clear_fit_display()
        
        self.edge_results = []
        colors = plt.cm.Set1(np.linspace(0, 1, max(len(self.edge_guesses), 1)))
        
        print("\n=== Fitting Edges ===")
        for i, guess in enumerate(sorted(self.edge_guesses)):
            result = fit_edge(self.x, self.y, guess, self.window)
            self.edge_results.append(result)
            
            color = colors[i]
            
            if result.fit_success:
                # Plot fitted curve
                x_edge = np.linspace(
                    result.position - 3 * result.width - 100,
                    result.position + 3 * result.width + 100,
                    200
                )
                if result.edge_type == "rising":
                    y_left = result.baseline
                    y_right = result.baseline + result.amplitude
                else:
                    y_left = result.baseline + result.amplitude
                    y_right = result.baseline
                
                y_edge = erf_edge(x_edge, result.position, result.width, y_left, y_right)
                fit_line, = self.ax.plot(x_edge, y_edge, '-', color=color, 
                                         linewidth=2.5, alpha=0.8)
                self.fit_lines.append(fit_line)
                
                # Mark fitted position
                pos_line = self.ax.axvline(result.position, color=color, 
                                           linestyle='-', alpha=0.8, linewidth=2)
                self.boundary_lines.append(pos_line)
                
                # Mark edge boundaries
                start_line = self.ax.axvline(result.edge_start, color=color, 
                                             linestyle=':', alpha=0.7, linewidth=1.5)
                end_line = self.ax.axvline(result.edge_end, color=color, 
                                           linestyle=':', alpha=0.7, linewidth=1.5)
                self.boundary_lines.extend([start_line, end_line])
                
                # Shade transition region
                region = self.ax.axvspan(result.edge_start, result.edge_end, 
                                         color=color, alpha=0.15)
                self.fit_regions.append(region)
                
                print(f"  Edge {i+1}: {result}")
                print(f"    Boundaries: {result.edge_start:.1f} - {result.edge_end:.1f} µs")
            else:
                print(f"  Edge {i+1}: FAILED at {result.initial_guess:.1f} µs")
                
        self.update_results_text()
        self.fig.canvas.draw_idle()
        
    def clear_fit_display(self):
        """Clear fit lines and regions from display."""
        for line in self.fit_lines:
            line.remove()
        self.fit_lines = []
        
        for region in self.fit_regions:
            region.remove()
        self.fit_regions = []
        
        for line in self.boundary_lines:
            line.remove()
        self.boundary_lines = []
        
    def clear_all(self, event):
        """Clear all markers and fit results."""
        self.edge_guesses = []
        self.edge_results = []
        
        for marker in self.guess_markers:
            marker.remove()
        self.guess_markers = []
        
        self.clear_fit_display()
        self.update_results_text()
        self.fig.canvas.draw_idle()
        print("Cleared all markers and fit results")
        
    def update_xlim(self, text):
        """Update x-axis limits."""
        try:
            xmin = float(self.textbox_xmin.text)
            xmax = float(self.textbox_xmax.text)
            if xmin < xmax:
                self.ax.set_xlim(xmin, xmax)
                self.fig.canvas.draw_idle()
        except ValueError:
            pass
            
    def update_ylim(self, text):
        """Update y-axis limits."""
        try:
            ymin = float(self.textbox_ymin.text)
            ymax = float(self.textbox_ymax.text)
            if ymin < ymax:
                self.ax.set_ylim(ymin, ymax)
                self.redraw_markers()
                self.fig.canvas.draw_idle()
        except ValueError:
            pass
            
    def update_window(self, text):
        """Update fitting window size."""
        try:
            self.window = float(text)
            print(f"Window size set to {self.window:.0f} µs")
        except ValueError:
            pass
            
    def autoscale(self, event):
        """Reset to autoscale."""
        self.ax.autoscale()
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()
        
        self.textbox_xmin.set_val(f'{xmin:.0f}')
        self.textbox_xmax.set_val(f'{xmax:.0f}')
        self.textbox_ymin.set_val(f'{ymin:.0f}')
        self.textbox_ymax.set_val(f'{ymax:.0f}')
        
        self.redraw_markers()
        self.fig.canvas.draw_idle()
        
    def update_results_text(self):
        """Update the results text display."""
        lines = []
        
        if self.edge_guesses:
            lines.append(f"Edge guesses ({len(self.edge_guesses)}): " + 
                        ", ".join(f"{g:.0f}" for g in sorted(self.edge_guesses)) + " µs")
        
        if self.edge_results:
            lines.append("\nFit Results:")
            for i, result in enumerate(self.edge_results, 1):
                if result.fit_success:
                    direction = "↑" if result.edge_type == "rising" else "↓"
                    lines.append(
                        f"  {i}. {direction} {result.position:.1f} ± {result.position_err:.1f} µs"
                    )
                    lines.append(
                        f"     [{result.edge_start:.1f} - {result.edge_end:.1f}]  width={result.width:.1f}"
                    )
                else:
                    lines.append(f"  {i}. FAILED at {result.initial_guess:.1f} µs")
                    
        self.results_text.set_text('\n'.join(lines))
        
    def save_results(self, event):
        """Save results to file."""
        if not self.edge_results:
            print("No fit results to save. Fit edges first.")
            return
            
        # Generate output filename
        if self.filename:
            stem = Path(self.filename).stem
            output_path = Path(f"{stem}_edges_ui.dat")
            plot_path = Path(f"{stem}_edges_ui.png")
        else:
            output_path = Path("edges_ui.dat")
            plot_path = Path("edges_ui.png")
            
        # Save data file
        with open(output_path, 'w') as f:
            f.write("# Edge Detection Results (Interactive UI)\n")
            f.write("# Columns: edge_num edge_type position position_err start end width amplitude\n")
            
            for i, r in enumerate(self.edge_results, 1):
                if r.fit_success:
                    f.write(f"{i} {r.edge_type} {r.position:.4f} {r.position_err:.4f} "
                           f"{r.edge_start:.4f} {r.edge_end:.4f} "
                           f"{r.width:.4f} {r.amplitude:.4f}\n")
                else:
                    f.write(f"{i} FAILED {r.initial_guess:.4f} nan nan nan nan nan\n")
                    
        print(f"Saved results: {output_path}")
        
        # Save plot
        self.fig.savefig(plot_path, dpi=150, bbox_inches='tight')
        print(f"Saved plot: {plot_path}")
        
    def show(self):
        """Display the interactive figure."""
        plt.show()




def main():
    parser = argparse.ArgumentParser(
        description="Interactive edge finder UI for monitor spectrum data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "spectrum_file",
        type=str,
        nargs="?",
        default=None,
        help="Input spectrum file (.dat format). If not provided, use IPTS/Run in Phase Calculator."
    )
    parser.add_argument(
        "--window",
        type=float,
        default=500.0,
        help="Initial window size for fitting (default: 500 µs)"
    )
    parser.add_argument(
        "--30hz",
        dest="mode_30hz",
        action="store_true",
        help="Enable 30 Hz mode (chopper period = 33333.33 µs instead of 16666.67 µs)"
    )
    
    args = parser.parse_args()
    
    mode_str = "[30 Hz MODE]" if args.mode_30hz else "[60 Hz MODE]"
    
    if args.spectrum_file:
        spectrum_path = Path(args.spectrum_file)
        if not spectrum_path.exists():
            print(f"Error: File not found: {spectrum_path}", file=sys.stderr)
            sys.exit(1)
        
        print(f"Loading: {spectrum_path}")
        try:
            x, y, run_title = load_spectrum(spectrum_path)
        except Exception as e:
            print(f"Error loading spectrum: {e}", file=sys.stderr)
            sys.exit(1)

        if run_title:
            print(f"Title: {run_title}")
        print(f"Data range: TOF {x.min():.1f} - {x.max():.1f} µs, {len(x)} points")
        print("\n" + "="*60)
        print(f"Interactive Edge Finder  {mode_str}")
        print("="*60)
        print("  Left-click on plot to add edge markers")
        print("  Right-click to remove nearest marker")
        print("  'f': fit edges   'c': clear   's': save   'g': log/lin   'q': quit")
        print("  'l': set Left E of blade to current mouse X position")
        print("  'r': set Right E of blade to current mouse X position")
        print("="*60 + "\n")

        ui = EdgeFinderUI(x, y, window=args.window, filename=spectrum_path.name,
                          run_title=run_title, mode_30hz=args.mode_30hz)
    else:
        print("="*60)
        print(f"Interactive Edge Finder  {mode_str}")
        print("="*60)
        print("No file provided. Use IPTS/Run inputs in the Phase Calculator")
        print("window to load data from NeXus files.")
        print("")
        print("  Left-click on plot to add edge markers")
        print("  Right-click to remove nearest marker")
        print("  'f': fit edges   'c': clear   's': save   'g': log/lin   'q': quit")
        print("  'l': set Left E of blade to current mouse X position")
        print("  'r': set Right E of blade to current mouse X position")
        print("="*60 + "\n")
        
        x = np.array([0.0, 1.0])
        y = np.array([0.0, 0.0])
        ui = EdgeFinderUI(x, y, window=args.window, filename="", run_title="",
                          mode_30hz=args.mode_30hz)
    
    ui.show()


if __name__ == "__main__":
    main()
