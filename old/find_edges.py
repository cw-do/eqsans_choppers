#!/usr/bin/env python
"""
Find edges (rising/falling) in monitor spectrum data.

Uses error function (erf) fitting to locate step-like transitions in intensity.
Supports both rising and falling edges with uncertainty estimation.

Usage:
    python find_edges.py <spectrum_file> --edges <x1>,<x2>,...
    
Examples:
    python find_edges.py 176475_monitor.dat --edges 1000,3000
    python find_edges.py 176475_monitor.dat --edges 5000,10000,15000 --window 500
    python find_edges.py 176475_monitor.dat --edges 1000 --output my_edges.png
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from scipy.optimize import curve_fit
from scipy.special import erf, erfinv


# Chopper configuration (same as extract_monitor.py and onechopper_diagram.py)
CHOPPER_CONFIG = {
    "1a": {"distance": 5.6978, "opening_deg": 129.600},
    "1b": {"distance": 5.7078, "opening_deg": 129.600},
    "2a": {"distance": 7.7978, "opening_deg": 180.000},
    "2b": {"distance": 7.8078, "opening_deg": 180.000},
    "3a": {"distance": 9.4978, "opening_deg": 230.010},
    "3b": {"distance": 9.5078, "opening_deg": 230.007},
}


def get_chopper_distance(chopper_name: str) -> Optional[float]:
    if chopper_name and chopper_name.lower() in CHOPPER_CONFIG:
        return CHOPPER_CONFIG[chopper_name.lower()]["distance"]
    return None


def format_chopper_label(chopper_name: Optional[str], phase_delay_us: Optional[float] = None) -> str:
    parts = []
    if chopper_name:
        distance = get_chopper_distance(chopper_name)
        if distance:
            parts.append(f"Chopper {chopper_name.upper()} @ {distance:.3f} m")
        else:
            parts.append(f"Chopper {chopper_name.upper()}")
    if phase_delay_us is not None:
        parts.append(f"Phase Delay {phase_delay_us:.0f} µs")
    return ", ".join(parts)


# Default threshold percentages for edge boundaries
DEFAULT_THRESHOLD_LOW = 0.05   # 5%
DEFAULT_THRESHOLD_HIGH = 0.95  # 95%


def get_boundary_factor(threshold_low: float = 0.05) -> float:
    """
    Calculate the boundary factor for erf-based edge boundaries.
    
    For threshold_low=0.05, we get 5%-95% boundaries.
    For threshold_low=0.01, we get 1%-99% boundaries.
    """
    # erf(x) ranges from -1 to 1
    # We want to find x where erf(x) = 2*threshold_low - 1 (for lower bound)
    # and erf(x) = 1 - 2*threshold_low (for upper bound)
    target = 1 - 2 * threshold_low  # e.g., 0.9 for 5%, 0.98 for 1%
    return erfinv(target) * np.sqrt(2)


@dataclass
class EdgeResult:
    """Result of edge fitting."""
    position: float          # Fitted edge position (midpoint, x value)
    position_err: float      # Uncertainty in position
    width: float             # Edge width (transition sharpness)
    width_err: float         # Uncertainty in width
    amplitude: float         # Step height
    baseline: float          # Baseline level
    edge_type: str           # 'rising' or 'falling'
    initial_guess: float     # Initial guess provided
    fit_success: bool        # Whether fit converged
    # Raw data boundary positions (if computed)
    raw_edge_start: Optional[float] = None
    raw_edge_end: Optional[float] = None
    # Threshold used for boundaries
    threshold_low: float = 0.05
    threshold_high: float = 0.95
    
    @property
    def boundary_factor(self) -> float:
        """Get the erf boundary factor for current threshold."""
        return get_boundary_factor(self.threshold_low)
    
    @property
    def edge_start(self) -> float:
        """
        Start of edge transition (low% level) from erf fit.
        For rising edge: where intensity starts increasing
        For falling edge: where intensity starts decreasing
        """
        return self.position - self.boundary_factor * self.width
    
    @property
    def edge_end(self) -> float:
        """
        End of edge transition (high% level) from erf fit.
        For rising edge: where intensity stops increasing (top)
        For falling edge: where intensity stops decreasing (bottom)
        """
        return self.position + self.boundary_factor * self.width
    
    @property
    def edge_start_err(self) -> float:
        """Uncertainty in edge start position."""
        # Error propagation: start = position - factor * width
        return np.sqrt(self.position_err**2 + (self.boundary_factor * self.width_err)**2)
    
    @property
    def edge_end_err(self) -> float:
        """Uncertainty in edge end position."""
        return np.sqrt(self.position_err**2 + (self.boundary_factor * self.width_err)**2)
    
    def __str__(self) -> str:
        direction = "↑" if self.edge_type == "rising" else "↓"
        return (
            f"Edge {direction} at {self.position:.2f} ± {self.position_err:.2f} "
            f"(width: {self.width:.2f} ± {self.width_err:.2f})"
        )
    
    def boundaries_str(self, use_raw: bool = False) -> str:
        """String representation with boundary positions."""
        low_pct = int(self.threshold_low * 100)
        high_pct = int(self.threshold_high * 100)
        
        if use_raw and self.raw_edge_start is not None:
            start = self.raw_edge_start
            end = self.raw_edge_end
            method = "raw"
            # No error estimates for raw data approach
            if self.edge_type == "rising":
                return (
                    f"  Start ({low_pct}%):  {start:.2f} µs [raw]\n"
                    f"  End ({high_pct}%):   {end:.2f} µs [raw]"
                )
            else:
                return (
                    f"  Start ({high_pct}%): {start:.2f} µs [raw]\n"
                    f"  End ({low_pct}%):    {end:.2f} µs [raw]"
                )
        else:
            if self.edge_type == "rising":
                return (
                    f"  Start ({low_pct}%):  {self.edge_start:.2f} ± {self.edge_start_err:.2f} µs [fit]\n"
                    f"  End ({high_pct}%):   {self.edge_end:.2f} ± {self.edge_end_err:.2f} µs [fit]"
                )
            else:
                return (
                    f"  Start ({high_pct}%): {self.edge_start:.2f} ± {self.edge_start_err:.2f} µs [fit]\n"
                    f"  End ({low_pct}%):    {self.edge_end:.2f} ± {self.edge_end_err:.2f} µs [fit]"
                )


def erf_edge(x: np.ndarray, x0: float, width: float, 
             y_left: float, y_right: float) -> np.ndarray:
    """
    Error function model for a step edge.
    
    Parameters
    ----------
    x : array
        Independent variable (TOF)
    x0 : float
        Edge position (midpoint of transition)
    width : float
        Edge width (controls sharpness of transition)
    y_left : float
        Intensity level to the left of edge
    y_right : float
        Intensity level to the right of edge
    
    Returns
    -------
    array
        Model intensity values
    """
    # erf goes from -1 to +1, so scale and shift appropriately
    # When x << x0: erf -> -1, result -> y_left
    # When x >> x0: erf -> +1, result -> y_right
    return (y_left + y_right) / 2 + (y_right - y_left) / 2 * erf((x - x0) / (width * np.sqrt(2)))


def load_spectrum(filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load spectrum from .dat file.
    
    Expected format: space-separated columns with optional header lines starting with #
    First column: x values (TOF in microseconds)
    Second column: intensity values
    """
    data = np.loadtxt(filepath, comments='#')
    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError(f"Expected 2-column data, got shape {data.shape}")
    return data[:, 0], data[:, 1]


def find_raw_boundaries(x: np.ndarray, y: np.ndarray,
                        result: EdgeResult,
                        window: float,
                        threshold_low: float = 0.01,
                        threshold_high: float = 0.99) -> Tuple[float, float]:
    """
    Find edge boundaries from raw data by interpolating where intensity
    crosses threshold levels.
    
    Parameters
    ----------
    x : array
        X values (TOF)
    y : array
        Intensity values
    result : EdgeResult
        Fitted edge result (used to determine baseline and amplitude)
    window : float
        Window around edge position to search
    threshold_low : float
        Lower threshold (e.g., 0.01 for 1%)
    threshold_high : float
        Upper threshold (e.g., 0.99 for 99%)
    
    Returns
    -------
    tuple of (start_x, end_x)
        X positions where intensity crosses thresholds
    """
    # Use fit results to determine intensity levels
    y_low = result.baseline + result.amplitude * threshold_low
    y_high = result.baseline + result.amplitude * threshold_high
    
    # Select data in search window (wider than fit window)
    search_window = window * 2
    mask = (x >= result.position - search_window) & (x <= result.position + search_window)
    x_search = x[mask]
    y_search = y[mask]
    
    if len(x_search) < 3:
        return result.edge_start, result.edge_end  # Fallback to fit
    
    # For rising edge: start is where y crosses y_low (going up), end is where y crosses y_high
    # For falling edge: start is where y crosses y_high (going down), end is where y crosses y_low
    
    def find_crossing(x_arr, y_arr, y_target, direction='rising'):
        """Find x where y crosses y_target using linear interpolation."""
        if direction == 'rising':
            # Find where y goes from below to above y_target
            for i in range(len(y_arr) - 1):
                if y_arr[i] <= y_target <= y_arr[i+1]:
                    # Linear interpolation
                    if y_arr[i+1] - y_arr[i] != 0:
                        frac = (y_target - y_arr[i]) / (y_arr[i+1] - y_arr[i])
                        return x_arr[i] + frac * (x_arr[i+1] - x_arr[i])
        else:  # falling
            # Find where y goes from above to below y_target
            for i in range(len(y_arr) - 1):
                if y_arr[i] >= y_target >= y_arr[i+1]:
                    # Linear interpolation
                    if y_arr[i] - y_arr[i+1] != 0:
                        frac = (y_arr[i] - y_target) / (y_arr[i] - y_arr[i+1])
                        return x_arr[i] + frac * (x_arr[i+1] - x_arr[i])
        return None
    
    if result.edge_type == 'rising':
        start = find_crossing(x_search, y_search, y_low, 'rising')
        end = find_crossing(x_search, y_search, y_high, 'rising')
    else:  # falling
        start = find_crossing(x_search, y_search, y_high, 'falling')
        end = find_crossing(x_search, y_search, y_low, 'falling')
    
    # Fallback to fit-based boundaries if crossing not found
    if start is None:
        start = result.edge_start
    if end is None:
        end = result.edge_end
    
    return start, end


def estimate_edge_type(x: np.ndarray, y: np.ndarray, 
                       x_guess: float, window: float) -> str:
    """
    Determine if edge is rising or falling based on local gradient.
    """
    mask = (x >= x_guess - window) & (x <= x_guess + window)
    if mask.sum() < 3:
        # Not enough points, use wider window
        mask = (x >= x_guess - 2*window) & (x <= x_guess + 2*window)
    
    x_local = x[mask]
    y_local = y[mask]
    
    # Simple linear regression to get slope
    if len(x_local) < 2:
        return "rising"  # Default
    
    slope = np.polyfit(x_local, y_local, 1)[0]
    return "rising" if slope > 0 else "falling"


def fit_edge(x: np.ndarray, y: np.ndarray, 
             x_guess: float, window: float) -> EdgeResult:
    """
    Fit an edge near the initial guess position.
    
    Parameters
    ----------
    x : array
        X values (TOF)
    y : array
        Intensity values  
    x_guess : float
        Initial guess for edge position
    window : float
        Window size around guess to use for fitting
    
    Returns
    -------
    EdgeResult
        Fitted edge parameters with uncertainties
    """
    # Select data within window
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
    
    # Determine edge type
    edge_type = estimate_edge_type(x, y, x_guess, window)
    
    # Initial parameter estimates
    y_left_guess = np.median(y_fit[:len(y_fit)//4]) if len(y_fit) >= 4 else y_fit[0]
    y_right_guess = np.median(y_fit[-len(y_fit)//4:]) if len(y_fit) >= 4 else y_fit[-1]
    width_guess = window / 10  # Start with relatively sharp edge
    
    p0 = [x_guess, width_guess, y_left_guess, y_right_guess]
    
    # Bounds: position within window, width positive but not too large
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
        
        # Extract uncertainties from covariance matrix
        perr = np.sqrt(np.diag(pcov))
        
        # Determine actual edge type from fit
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
        print(f"Warning: Fit failed for edge near {x_guess}: {e}", file=sys.stderr)
        return EdgeResult(
            position=x_guess, position_err=np.inf,
            width=np.nan, width_err=np.inf,
            amplitude=np.nan, baseline=np.nan,
            edge_type=edge_type, initial_guess=x_guess,
            fit_success=False
        )


def find_edges(x: np.ndarray, y: np.ndarray,
               edge_guesses: List[float],
               window: Optional[float] = None,
               threshold_low: float = 0.05,
               threshold_high: float = 0.95,
               use_raw: bool = False) -> List[EdgeResult]:
    """
    Find multiple edges in spectrum data.
    
    Parameters
    ----------
    x : array
        X values (TOF in microseconds)
    y : array
        Intensity values
    edge_guesses : list of float
        Initial guesses for edge positions
    window : float, optional
        Window size for fitting. If None, auto-calculated.
    threshold_low : float
        Lower threshold percentage (default: 0.05 for 5%)
    threshold_high : float
        Upper threshold percentage (default: 0.95 for 95%)
    use_raw : bool
        If True, also compute boundaries from raw data interpolation
    
    Returns
    -------
    list of EdgeResult
        Fitted edge results
    """
    if window is None:
        # Auto-calculate window based on data spacing and range
        x_range = x.max() - x.min()
        dx = np.median(np.diff(x))
        window = max(50 * dx, x_range / 20)
    
    results = []
    for guess in edge_guesses:
        result = fit_edge(x, y, guess, window)
        
        # Set threshold values
        result.threshold_low = threshold_low
        result.threshold_high = threshold_high
        
        # Optionally compute raw data boundaries
        if use_raw and result.fit_success:
            raw_start, raw_end = find_raw_boundaries(
                x, y, result, window,
                threshold_low=threshold_low,
                threshold_high=threshold_high
            )
            result.raw_edge_start = raw_start
            result.raw_edge_end = raw_end
        
        results.append(result)
    
    return results


def plot_results(x: np.ndarray, y: np.ndarray,
                 results: List[EdgeResult],
                 output_path: Path,
                 run_info: str = "",
                 show_raw: bool = False,
                 chopper_name: Optional[str] = None,
                 phase_delay_us: Optional[float] = None) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), 
                              gridspec_kw={'height_ratios': [3, 1]})
    
    ax1 = axes[0]
    ax1.plot(x, y, 'b-', linewidth=0.8, alpha=0.7, label='Data')
    
    colors = plt.cm.Set1(np.linspace(0, 1, max(len(results), 1)))
    
    for i, result in enumerate(results):
        color = colors[i]
        
        if result.fit_success:
            # Plot fitted edge
            x_edge = np.linspace(
                result.position - 3 * result.width - 100,
                result.position + 3 * result.width + 100,
                200
            )
            # Reconstruct fit parameters
            if result.edge_type == "rising":
                y_left = result.baseline
                y_right = result.baseline + result.amplitude
            else:
                y_left = result.baseline + result.amplitude
                y_right = result.baseline
            
            y_edge = erf_edge(x_edge, result.position, result.width, y_left, y_right)
            ax1.plot(x_edge, y_edge, '-', color=color, linewidth=2, 
                    label=f'Edge {i+1}: {result.position:.1f} ± {result.position_err:.1f}')
            
            # Mark edge midpoint with vertical line
            ax1.axvline(result.position, color=color, linestyle='--', alpha=0.8, linewidth=1.5)
            
            # Mark edge boundaries (fit-based) - dotted lines
            low_pct = int(result.threshold_low * 100)
            high_pct = int(result.threshold_high * 100)
            ax1.axvline(result.edge_start, color=color, linestyle=':', alpha=0.9, linewidth=2,
                       label=f'Edge {i+1} fit: {result.edge_start:.1f} - {result.edge_end:.1f}')
            ax1.axvline(result.edge_end, color=color, linestyle=':', alpha=0.9, linewidth=2)
            
            # Shade the transition region (fit-based)
            ax1.axvspan(result.edge_start, result.edge_end, color=color, alpha=0.15)
            
            # If raw boundaries available, mark them with different style (solid thin, darker)
            if show_raw and result.raw_edge_start is not None:
                # Use a contrasting color - darken the original color
                raw_color = tuple(c * 0.6 for c in color[:3]) + (1.0,)  # Darker version
                ax1.axvline(result.raw_edge_start, color=raw_color, linestyle='-', alpha=0.9, linewidth=2.5,
                           label=f'Edge {i+1} raw: {result.raw_edge_start:.1f} - {result.raw_edge_end:.1f}')
                ax1.axvline(result.raw_edge_end, color=raw_color, linestyle='-', alpha=0.9, linewidth=2.5)
            
            # Add arrow indicating edge direction
            arrow_y = (y_left + y_right) / 2
            if result.edge_type == "rising":
                ax1.annotate('', xy=(result.position + 50, arrow_y + result.amplitude * 0.3),
                           xytext=(result.position - 50, arrow_y - result.amplitude * 0.3),
                           arrowprops=dict(arrowstyle='->', color=color, lw=2))
            else:
                ax1.annotate('', xy=(result.position + 50, arrow_y - result.amplitude * 0.3),
                           xytext=(result.position - 50, arrow_y + result.amplitude * 0.3),
                           arrowprops=dict(arrowstyle='->', color=color, lw=2))
        else:
            # Mark failed fit with X
            ax1.axvline(result.initial_guess, color=color, linestyle=':', alpha=0.5)
            ax1.plot(result.initial_guess, y[np.argmin(np.abs(x - result.initial_guess))],
                    'x', color=color, markersize=15, markeredgewidth=3,
                    label=f'Edge {i+1}: FAILED at {result.initial_guess:.1f}')
    
    ax1.set_xlabel('Time of Flight (µs)', fontsize=12)
    ax1.set_ylabel('Intensity (counts)', fontsize=12)
    title = 'Edge Detection Results'
    if run_info:
        title += f' - {run_info}'
    chopper_label = format_chopper_label(chopper_name, phase_delay_us)
    if chopper_label:
        title += f'\n{chopper_label}'
    ax1.set_title(title, fontsize=14)
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # Derivative plot (helps visualize edges)
    ax2 = axes[1]
    dy = np.gradient(y, x)
    ax2.plot(x, dy, 'g-', linewidth=0.8, alpha=0.7)
    ax2.set_xlabel('Time of Flight (µs)', fontsize=12)
    ax2.set_ylabel('dI/dTOF', fontsize=12)
    ax2.set_title('Derivative (for edge visualization)', fontsize=11)
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    # Mark edge positions and boundaries on derivative plot
    for i, result in enumerate(results):
        if result.fit_success:
            color = colors[i]
            ax2.axvline(result.position, color=color, linestyle='--', alpha=0.8)
            # Fit-based boundaries (dotted)
            ax2.axvline(result.edge_start, color=color, linestyle=':', alpha=0.6, linewidth=1.5)
            ax2.axvline(result.edge_end, color=color, linestyle=':', alpha=0.6, linewidth=1.5)
            ax2.axvspan(result.edge_start, result.edge_end, color=color, alpha=0.1)
            # Raw boundaries on derivative plot (solid, darker)
            if show_raw and result.raw_edge_start is not None:
                raw_color = tuple(c * 0.6 for c in color[:3]) + (1.0,)
                ax2.axvline(result.raw_edge_start, color=raw_color, linestyle='-', alpha=0.7, linewidth=2)
                ax2.axvline(result.raw_edge_end, color=raw_color, linestyle='-', alpha=0.7, linewidth=2)
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Saved plot: {output_path}")
    plt.close(fig)


def save_results(results: List[EdgeResult], output_path: Path, include_raw: bool = False) -> None:
    """Save edge results to text file."""
    if not results:
        return
    
    low_pct = int(results[0].threshold_low * 100)
    high_pct = int(results[0].threshold_high * 100)
    
    with open(output_path, 'w') as f:
        f.write(f"# Edge Detection Results ({low_pct}%-{high_pct}% transition boundaries)\n")
        if include_raw:
            f.write("# Columns: edge_num edge_type midpoint midpoint_err fit_start fit_start_err fit_end fit_end_err raw_start raw_end width amplitude\n")
        else:
            f.write("# Columns: edge_num edge_type midpoint midpoint_err fit_start fit_start_err fit_end fit_end_err width amplitude\n")
        
        for i, r in enumerate(results, 1):
            if r.fit_success:
                base = (f"{i} {r.edge_type} {r.position:.4f} {r.position_err:.4f} "
                       f"{r.edge_start:.4f} {r.edge_start_err:.4f} "
                       f"{r.edge_end:.4f} {r.edge_end_err:.4f} ")
                if include_raw:
                    raw_start = r.raw_edge_start if r.raw_edge_start is not None else float('nan')
                    raw_end = r.raw_edge_end if r.raw_edge_end is not None else float('nan')
                    base += f"{raw_start:.4f} {raw_end:.4f} "
                base += f"{r.width:.4f} {r.amplitude:.4f}\n"
                f.write(base)
            else:
                if include_raw:
                    f.write(f"{i} FAILED {r.initial_guess:.4f} nan nan nan nan nan nan nan nan nan\n")
                else:
                    f.write(f"{i} FAILED {r.initial_guess:.4f} nan nan nan nan nan nan nan\n")
    print(f"Saved results: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Find edges in monitor spectrum data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "spectrum_file",
        type=str,
        help="Input spectrum file (.dat format)"
    )
    parser.add_argument(
        "--edges",
        type=str,
        required=True,
        help="Comma-separated initial guesses for edge positions (e.g., 1000,3000)"
    )
    parser.add_argument(
        "--window",
        type=float,
        default=None,
        help="Window size around each edge guess for fitting (default: auto)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output figure path (default: <input_basename>_edges.png)"
    )
    parser.add_argument(
        "--save-data",
        action="store_true",
        help="Also save edge results to a .dat file"
    )
    parser.add_argument(
        "--threshold",
        type=str,
        default="5,95",
        help="Threshold percentages for edge boundaries as 'low,high' (default: 5,95 for 5%%-95%%)"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Also compute boundaries from raw data interpolation (in addition to erf fit)"
    )
    parser.add_argument(
        "--chopper",
        type=str,
        default=None,
        choices=["1a", "1b", "2a", "2b", "3a", "3b"],
        help="Chopper name (1a, 1b, 2a, 2b, 3a, 3b) - auto-detected from filename if present"
    )
    parser.add_argument(
        "--phase-delay",
        type=float,
        default=None,
        help="Phase delay in microseconds - auto-detected from filename if present"
    )
    
    args = parser.parse_args()
    
    # Parse threshold values
    try:
        thresh_parts = args.threshold.split(',')
        threshold_low = float(thresh_parts[0].strip()) / 100.0
        threshold_high = float(thresh_parts[1].strip()) / 100.0
        if not (0 < threshold_low < threshold_high < 1):
            raise ValueError("Thresholds must satisfy 0 < low < high < 100")
    except (ValueError, IndexError) as e:
        print(f"Error parsing threshold: {e}. Use format 'low,high' e.g., '1,99' or '5,95'", file=sys.stderr)
        sys.exit(1)
    
    # Parse edge guesses
    try:
        edge_guesses = [float(x.strip()) for x in args.edges.split(',')]
    except ValueError as e:
        print(f"Error parsing edge positions: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not edge_guesses:
        print("Error: No edge positions provided", file=sys.stderr)
        sys.exit(1)
    
    # Load spectrum
    spectrum_path = Path(args.spectrum_file)
    if not spectrum_path.exists():
        print(f"Error: File not found: {spectrum_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading: {spectrum_path}")
    try:
        x, y = load_spectrum(spectrum_path)
    except Exception as e:
        print(f"Error loading spectrum: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Data range: TOF {x.min():.1f} - {x.max():.1f} µs, {len(x)} points")
    print(f"Looking for edges near: {edge_guesses}")
    
    # Find edges
    results = find_edges(x, y, edge_guesses, window=args.window,
                         threshold_low=threshold_low, threshold_high=threshold_high,
                         use_raw=args.raw)
    
    low_pct = int(threshold_low * 100)
    high_pct = int(threshold_high * 100)
    
    # Print results
    print("\n=== Edge Detection Results ===")
    for i, result in enumerate(results, 1):
        status = "✓" if result.fit_success else "✗"
        print(f"  [{status}] Edge {i}: {result}")
        if result.fit_success:
            print(result.boundaries_str(use_raw=False))  # Always show fit-based
            if args.raw and result.raw_edge_start is not None:
                print(result.boundaries_str(use_raw=True))  # Also show raw if requested
    
    # Print summary of all boundary positions
    if any(r.fit_success for r in results):
        print(f"\n=== Edge Boundary Positions ({low_pct}%-{high_pct}% transition) ===")
        
        # Fit-based boundaries
        print("\n  [From erf fit]:")
        boundary_count = 0
        for i, result in enumerate(results, 1):
            if result.fit_success:
                boundary_count += 1
                print(f"    Edge {i} ({result.edge_type}):")
                print(f"      {boundary_count}. Start: {result.edge_start:.2f} ± {result.edge_start_err:.2f} µs")
                boundary_count += 1
                print(f"      {boundary_count}. End:   {result.edge_end:.2f} ± {result.edge_end_err:.2f} µs")
        
        # Raw data boundaries (if computed)
        if args.raw and any(r.raw_edge_start is not None for r in results if r.fit_success):
            print("\n  [From raw data interpolation]:")
            boundary_count = 0
            for i, result in enumerate(results, 1):
                if result.fit_success and result.raw_edge_start is not None:
                    boundary_count += 1
                    print(f"    Edge {i} ({result.edge_type}):")
                    print(f"      {boundary_count}. Start: {result.raw_edge_start:.2f} µs")
                    boundary_count += 1
                    print(f"      {boundary_count}. End:   {result.raw_edge_end:.2f} µs")
    
    # Determine output paths
    stem = spectrum_path.stem
    if args.output:
        plot_path = Path(args.output)
    else:
        plot_path = Path(f"{stem}_edges.png")
    
    run_info = ""
    chopper_name = args.chopper
    phase_delay = args.phase_delay
    
    # Try to extract run number, chopper, and phase delay from filename
    # Pattern: {run}_{chopper}_pd{delay}_monitor or {run}_{chopper}_monitor or {run}_monitor
    full_pattern = r'(\d+)_([123][aAbB])_pd(\d+)_monitor'
    chopper_pattern = r'(\d+)_([123][aAbB])_monitor'
    simple_pattern = r'(\d+)_monitor'
    
    match = re.search(full_pattern, stem)
    if match:
        run_info = f"Run {match.group(1)}"
        if not chopper_name:
            chopper_name = match.group(2).lower()
        if phase_delay is None:
            phase_delay = float(match.group(3))
    else:
        match = re.search(chopper_pattern, stem)
        if match:
            run_info = f"Run {match.group(1)}"
            if not chopper_name:
                chopper_name = match.group(2).lower()
        else:
            match = re.search(simple_pattern, stem)
            if match:
                run_info = f"Run {match.group(1)}"
    
    if chopper_name or phase_delay is not None:
        chopper_label = format_chopper_label(chopper_name, phase_delay)
        print(f"Chopper info: {chopper_label}")
    
    plot_results(x, y, results, plot_path, run_info=run_info, show_raw=args.raw,
                 chopper_name=chopper_name, phase_delay_us=phase_delay)
    
    if args.save_data:
        data_path = plot_path.with_suffix('.dat')
        save_results(results, data_path, include_raw=args.raw)


if __name__ == "__main__":
    main()
