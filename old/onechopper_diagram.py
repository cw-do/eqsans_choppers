import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
import argparse

# --- 1. CONSTANTS & INSTRUMENT GEOMETRY ---
FREQ = 60.0                 
PERIOD = 1.0 / FREQ         

CHOPPER_CONFIG = {
    "1a": {"L_CHOP": 5.6978, "OPENING_DEG": 129.600},
    "1b": {"L_CHOP": 5.7078, "OPENING_DEG": 129.600},
    "2a": {"L_CHOP": 7.7978, "OPENING_DEG": 180.000},
    "2b": {"L_CHOP": 7.8078, "OPENING_DEG": 180.000},
    "3a": {"L_CHOP": 9.4978, "OPENING_DEG": 230.010},
    "3b": {"L_CHOP": 9.5078, "OPENING_DEG": 230.007},
}

# Default chopper (can be overridden via --chopper argument)
DEFAULT_CHOPPER = "1b"

# --- 2. DATA LOADING ---
def load_flux_data(file_path):
    try:
        df = pd.read_csv(file_path, sep=r'\s+', comment='#', header=0)
        return df
    except Exception:
        wav_range = np.linspace(0.1, 25, 2000)
        flux_vals = (1/wav_range**4) * np.exp(-5/wav_range**2) * 1e7
        return pd.DataFrame({'x': wav_range, 'Y': flux_vals})

# --- 3. SIMULATION FUNCTIONS ---
def simulate_beam_transmission(t_plot_limit, offset_s, l_det, wav_fine, flux_fine, 
                               l_chop, opening_s):
    """
    Simulate beam transmission through a single chopper.
    
    Parameters
    ----------
    t_plot_limit : float
        Time limit for simulation in seconds
    offset_s : float
        Chopper phase offset in seconds
    l_det : float
        Detector distance in meters
    wav_fine : array
        Wavelength array in Angstroms
    flux_fine : array
        Flux values corresponding to wavelengths
    l_chop : float
        Chopper distance from source in meters
    opening_s : float
        Chopper opening time in seconds
    """
    passed_trajectories = []
    velocities = 3956.0 / wav_fine
    
    for p in range(-6, int(t_plot_limit/PERIOD) + 2):
        t_src = p * PERIOD
        t_arrival = t_src + (l_chop / velocities)
        relative_arrival = (t_arrival - offset_s) % PERIOD
        mask_pass = relative_arrival < opening_s
        
        if np.any(mask_pass):
            t_det = t_src + (l_det / velocities[mask_pass])
            passed_trajectories.append({
                'p': p,
                't_src': t_src,
                'velocities': velocities[mask_pass],
                'fluxes': flux_fine[mask_pass],
                'wavs': wav_fine[mask_pass],
                't_det': t_det
            })
    return passed_trajectories


def detect_tof_edges(tof_bins, intensity_hist, edge_guesses=None, window_us=1000.0, 
                     nth_edges=None, edge_types=None, threshold_pct=None, use_log=False):
    """
    Detect edges in TOF space. If edge_guesses provided, search around those locations.
    edge_guesses: list of TOF values in microseconds [edge1_us, edge2_us, ...]
    window_us: search window in microseconds around each guess
    nth_edges: list of which edge to pick for each guess (1=biggest, 2=2nd biggest, etc.)
    threshold_pct: if set, find where intensity drops to this % of local max (e.g., 50 for 50%)
    First edge assumed to be falling (primary drop), subsequent edges are rising.
    use_log: if True, use log of intensity for edge detection (better for weak signals)
    """
    log_hist = np.log10(np.maximum(intensity_hist, 1))
    smoothed = gaussian_filter1d(log_hist, sigma=1)
    derivative = np.gradient(smoothed)
    max_intensity = np.max(smoothed)
    
    bin_width_s = tof_bins[1] - tof_bins[0]
    window_bins = int((window_us * 1e-6) / bin_width_s)
    window_bins = max(5, window_bins)
    
    detected_edges = []
    
    if edge_guesses is not None and len(edge_guesses) > 0:
        for i, guess_us in enumerate(edge_guesses):
            guess_s = guess_us * 1e-6
            guess_idx = np.searchsorted(tof_bins, guess_s)
            
            search_start = max(0, guess_idx - window_bins)
            search_end = min(len(derivative), guess_idx + window_bins)
            window_deriv = derivative[search_start:search_end]
            window_smooth = smoothed[search_start:search_end]
            
            nth = 1
            if nth_edges is not None and i < len(nth_edges):
                nth = nth_edges[i]
            
            is_falling = True
            if edge_types is not None and i < len(edge_types):
                is_falling = edge_types[i].lower().startswith('f')
            elif i > 0:
                is_falling = False
            
            if threshold_pct is not None:
                local_max = np.max(window_smooth)
                local_min = np.min(window_smooth)
                
                if is_falling:
                    threshold_level = local_max - (local_max - local_min) * (1 - threshold_pct / 100.0)
                    for j in range(len(window_smooth) - 1):
                        if window_smooth[j] >= threshold_level and window_smooth[j+1] < threshold_level:
                            local_idx = j
                            break
                    else:
                        local_idx = np.argmin(window_deriv)
                else:
                    peaks_in_window, _ = find_peaks(window_smooth, prominence=0.01)
                    if len(peaks_in_window) > 0:
                        local_idx = peaks_in_window[0]
                    else:
                        local_idx = np.argmax(window_smooth)
            elif is_falling:
                neg_deriv = -window_deriv
                peaks, properties = find_peaks(neg_deriv, prominence=0.01)
                if len(peaks) > 0:
                    prominences = properties['prominences']
                    sorted_indices = np.argsort(prominences)[::-1]
                    pick_idx = min(nth - 1, len(sorted_indices) - 1)
                    local_idx = peaks[sorted_indices[pick_idx]]
                else:
                    local_idx = np.argmin(window_deriv)
            else:
                peaks, properties = find_peaks(window_deriv, prominence=0.01)
                if len(peaks) > 0:
                    prominences = properties['prominences']
                    sorted_indices = np.argsort(prominences)[::-1]
                    pick_idx = min(nth - 1, len(sorted_indices) - 1)
                    local_idx = peaks[sorted_indices[pick_idx]]
                else:
                    local_idx = np.argmax(window_deriv)
            
            edge_idx = search_start + local_idx
            detected_edges.append(tof_bins[edge_idx])
    else:
        # Auto-detect: find primary drop then previous rise
        primary_drop_idx = None
        high_signal_threshold = max_intensity * 0.5
        
        in_primary_pulse = False
        for i in range(len(smoothed)):
            if smoothed[i] > high_signal_threshold:
                in_primary_pulse = True
            elif in_primary_pulse and smoothed[i] < high_signal_threshold * 0.3:
                search_window = slice(max(0, i-30), min(len(derivative), i+10))
                local_min_deriv_idx = np.argmin(derivative[search_window]) + search_window.start
                primary_drop_idx = local_min_deriv_idx
                detected_edges.append(tof_bins[primary_drop_idx])
                break
        
        # Find previous pulse rise
        if primary_drop_idx is not None:
            search_start = primary_drop_idx + 3
            search_end = min(len(intensity_hist) - 1, primary_drop_idx + 150)
            
            if search_start < search_end:
                search_region = smoothed[search_start:search_end]
                
                if len(search_region) > 5:
                    min_local_idx = np.argmin(search_region[:len(search_region)//2])
                    rise_threshold = max_intensity * 0.00001
                    for j in range(min_local_idx + 1, len(search_region)):
                        if search_region[j] > rise_threshold:
                            refine_start = search_start + max(0, j - 5)
                            refine_end = min(len(derivative), search_start + j + 10)
                            local_max_deriv = np.argmax(derivative[refine_start:refine_end])
                            detected_edges.append(tof_bins[refine_start + local_max_deriv])
                            break
    
    return detected_edges


def plot_edges_zoom(tof_bins, intensity_hist, offset_us, l_det, detected_edges,
                    chopper_name, l_chop):
    """
    Create a zoomed 6x4 figure of detector TOF signal with edge annotations.
    Uses log scale to show weak previous pulse signal clearly.
    """
    fig, ax = plt.subplots(figsize=(6, 4))
    
    tof_us = tof_bins[:-1] * 1e6
    intensity_plot = np.maximum(intensity_hist, 1)
    
    ax.semilogy(tof_us, intensity_plot, color='purple', lw=1.5, label='Detector Signal')
    ax.fill_between(tof_us, 1, intensity_plot, color='purple', alpha=0.2)
    ax.set_ylim(bottom=1)
    
    colors = ['red', 'blue', 'green', 'orange', 'cyan', 'magenta']
    edge_text_lines = [f"Chopper: {chopper_name.upper()} at {l_chop} m"]
    
    for i, edge_tof in enumerate(detected_edges):
        edge_us = edge_tof * 1e6
        color = colors[i % len(colors)]
        ax.axvline(edge_us, color=color, ls='--', lw=2)
        idx = np.searchsorted(tof_bins[:-1], edge_tof)
        y_pos = intensity_plot[min(idx, len(intensity_plot)-1)]
        ax.annotate(f'{edge_us:.2f} μs', 
                    xy=(edge_us, y_pos),
                    xytext=(edge_us, y_pos * 0.1),
                    fontsize=9, color=color,
                    ha='center',
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
        edge_text_lines.append(f"Edge {i+1}: {edge_us:.2f} μs")
    
    textstr = '\n'.join(edge_text_lines)
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)
    
    ax.set_xlabel('TOF at Detector (μs)', fontsize=11)
    ax.set_ylabel('Intensity (a.u.) [log scale]', fontsize=11)
    ax.set_title(f'TOF Edge Detection - Chopper {chopper_name.upper()} (Offset={offset_us} μs, $L_{{det}}$={l_det} m)', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.5, which='both')
    ax.set_xlim(0, 33000)  # Show 2 pulses (~33 ms at 60 Hz)
    
    plt.tight_layout()
    filename = f'onechopper_{chopper_name.lower()}_dd{l_det}_off{offset_us}_edges.png'
    plt.savefig(filename, dpi=200)
    print(f"Saved edge detection plot to: {filename}")
    #plt.show()
    
    return filename


def plot_research_model(passed_data, t_plot_limit, offset_us, l_det, wav_fine, flux_fine,
                        chopper_name, l_chop, opening_s):
    """
    Original 3-panel plot from onechopper.py - maintained as default output.
    """
    fig = plt.figure(figsize=(8, 5), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[2.5, 1], width_ratios=[4, 1], hspace=0.05, wspace=0.02)
    
    ax1 = fig.add_subplot(gs[0, 0]) 
    ax2 = fig.add_subplot(gs[1, 0], sharex=ax1) 
    ax3 = fig.add_subplot(gs[:, 1]) 

    # --- Panel 1 & 2: Timing and TOF ---
    offset_s = offset_us * 1e-6
    for k in range(-6, int(t_plot_limit/PERIOD) + 2):
        t_start = offset_s + opening_s + k * PERIOD
        ax1.add_patch(plt.Rectangle((t_start, l_chop-0.1), (PERIOD - opening_s), 0.2, color='red', alpha=0.5))

    tof_bins = np.linspace(0, t_plot_limit, 800)
    intensity_hist = np.zeros(len(tof_bins) - 1)

    # Collect all trajectory lines for batch plotting (much faster than individual plot calls)
    all_lines = []
    for pulse in passed_data:
        hist, _ = np.histogram(pulse['t_det'], bins=tof_bins, weights=pulse['fluxes'])
        intensity_hist += hist
        
        step = max(1, len(pulse['velocities']) // 20)  # Fewer lines for speed
        for v in pulse['velocities'][::step]:
            all_lines.append([(pulse['t_src'], 0), (pulse['t_src'] + l_det/v, l_det)])
    
    # Add all trajectory lines at once using LineCollection
    if all_lines:
        lc = LineCollection(all_lines, colors='royalblue', alpha=0.2, linewidths=0.5)
        ax1.add_collection(lc)
        ax1.set_ylim(0, l_det * 1.05)
        ax1.set_xlim(0, t_plot_limit)

    ax1.set_ylabel("Distance (m)")
    ax1.set_title(rf"Chopper {chopper_name.upper()} Timing (Offset={offset_us}$\mu$s, $L_{{det}}$={l_det}m)")
    
    ax2.plot(tof_bins[:-1], intensity_hist, color='purple', lw=1.5)
    ax2.fill_between(tof_bins[:-1], 0, intensity_hist, color='purple', alpha=0.2)
    ax2.set_xlabel("Absolute Time at Detector (s)")
    ax2.set_xlim(0, t_plot_limit)

    # --- Panel 3: Corrected FORWARD MODEL Wavelength Bandpass ---
    t_chop = (l_chop * wav_fine) / 3956.0
    relative_arrival = (t_chop - offset_s) % PERIOD
    n_periods = np.floor((t_chop - offset_s) / PERIOD)
    
    passes = relative_arrival < opening_s
    
    # Explicitly capture the fast neutrons wrapping backward in phase (n_periods == -1)
    mask_green = passes & (n_periods == -1)  # Prompt fast neutrons
    mask_red   = passes & (n_periods == 0)   # Primary bandpass
    mask_blue  = passes & (n_periods == 1)   # Slow tail passing next rotation
    mask_gray  = ~passes                     # Physically blocked by the blade

    max_flux = np.max(flux_fine) * 1.1
    ax3.set_xlim(max_flux, 0)
    ax3.yaxis.tick_right()              
    ax3.yaxis.set_label_position("right")
    
    # Plot layers
    ax3.plot(flux_fine, wav_fine, color='lightgray', alpha=0.5, lw=1)
    ax3.fill_betweenx(wav_fine, 0, flux_fine, where=mask_green, color='green', alpha=0.6, label='Passed (Prompt)')
    ax3.fill_betweenx(wav_fine, 0, flux_fine, where=mask_red, color='red', alpha=0.4, label='Passed (1st Opening)')
    ax3.fill_betweenx(wav_fine, 0, flux_fine, where=mask_blue, color='blue', alpha=0.6, label='Passed (2nd Opening)')
    ax3.fill_betweenx(wav_fine, 0, flux_fine, where=mask_gray, color='gray', alpha=0.4, label='Blocked by Chopper')

    def draw_exact_boundaries(mask, color):
        if not np.any(mask): return
        padded = np.concatenate(([False], mask, [False]))
        diff = np.diff(padded.astype(int))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0] - 1
        
        for s, e in zip(starts, ends):
            ws, we = wav_fine[s], wav_fine[e]
            ax3.axhline(ws, color=color, ls='--', lw=0.8)
            ax3.axhline(we, color=color, ls='--', lw=0.8)
            ax3.text(max_flux * 0.05, ws, f"{ws:.2f} Å", va='top', color=color, fontsize=8)
            ax3.text(max_flux * 0.05, we, f"{we:.2f} Å", va='bottom', color=color, fontsize=8)

    draw_exact_boundaries(mask_green, 'green')
    draw_exact_boundaries(mask_red, 'red')
    draw_exact_boundaries(mask_blue, 'blue')

    ax3.set_ylabel("Wavelength (Å)")
    ax3.set_xlabel("Flux (a.u.)")
    ax3.set_title(f"Chopper {chopper_name.upper()} Bandpass")
    ax3.legend(loc='upper right', fontsize='small')

    # Note: using constrained_layout=True in figure creation instead of tight_layout()
    filename = f'onechopper_{chopper_name.lower()}_dd{l_det}_off{offset_us}.png'
    plt.savefig(filename, dpi=200)
    print(f"Saved main plot to: {filename}")
    #plt.show()
    
    return tof_bins, intensity_hist


# --- 4. EXECUTE ---
if __name__ == "__main__":
    # Get available chopper names for help text
    available_choppers = list(CHOPPER_CONFIG.keys())
    
    parser = argparse.ArgumentParser(
        description="Single chopper calibration tool with edge detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available choppers: {', '.join(available_choppers)}

Examples:
    python onechopper_diagram.py --chopper 1a --offset 0
    python onechopper_diagram.py --chopper 3a --edges 12500,14500 --window 500
    python onechopper_diagram.py --chopper 3a --edges 4000,9500 --window 3000 --nth 2,1
    python onechopper_diagram.py --chopper 2a --edges 1550,10900 --edge-types f,f
    
The --nth option selects which edge to find when multiple exist in the window:
    --nth 1,1  = find biggest drop, then biggest rise (default)
    --nth 2,1  = find 2nd biggest drop, then biggest rise

The --edge-types option specifies falling (f) or rising (r) for each edge:
    --edge-types f,r  = falling edge, then rising edge (default behavior)
    --edge-types f,f  = two falling edges
    --edge-types r,r  = two rising edges
"""
    )
    parser.add_argument("--chopper", type=str, default=DEFAULT_CHOPPER,
                        choices=available_choppers,
                        help=f"Chopper to simulate (default: {DEFAULT_CHOPPER})")
    parser.add_argument("--offset", type=float, default=0.0, 
                        help="Fixed offset in microseconds for the simulation")
    parser.add_argument("--dd", type=float, default=10.006, 
                        help="Detector distance in meters (default: 10.006m)")
    parser.add_argument("--edges-only", action="store_true",
                        help="Generate only the edge detection plot, skip 3-panel plot")
    parser.add_argument("--edges", type=str, default=None,
                        help="Initial edge guesses in microseconds, comma-separated (e.g., --edges 10700,13000)")
    parser.add_argument("--window", type=float, default=1000.0,
                        help="Search window around each edge guess in microseconds (default: 1000)")
    parser.add_argument("--nth", type=str, default=None,
                        help="Which edge to find for each guess (1=biggest, 2=2nd biggest). Comma-separated (e.g., --nth 2,1)")
    parser.add_argument("--threshold", type=float, default=None,
                        help="Find where intensity crosses this %% of local max (e.g., --threshold 90 for 90%%)")
    parser.add_argument("--log", action="store_true",
                        help="Use log scale for edge detection (better for weak signals)")
    parser.add_argument("--edge-types", type=str, default=None,
                        help="Edge types: f=falling, r=rising. Comma-separated (e.g., --edge-types f,f for two falling edges)")
    args = parser.parse_args()
    
    # Get chopper configuration
    chopper_name = args.chopper.lower()
    chopper_cfg = CHOPPER_CONFIG[chopper_name]
    l_chop = chopper_cfg["L_CHOP"]
    opening_deg = chopper_cfg["OPENING_DEG"]
    opening_s = (opening_deg / 360.0) * PERIOD
    
    print(f"=== Chopper Configuration ===")
    print(f"Chopper: {chopper_name.upper()}")
    print(f"Distance from source: {l_chop} m")
    print(f"Opening angle: {opening_deg}°")
    print(f"Opening time: {opening_s * 1e6:.2f} µs")
    print(f"Phase offset: {args.offset} µs")
    print(f"Detector distance: {args.dd} m")
    print()
    
    edge_guesses = None
    if args.edges:
        edge_guesses = [float(x.strip()) for x in args.edges.split(',')]
    
    nth_edges = None
    if args.nth:
        nth_edges = [int(x.strip()) for x in args.nth.split(',')]

    edge_types = None
    if getattr(args, 'edge_types', None):
        edge_types = [x.strip() for x in args.edge_types.split(',')]

    # Load and prep data
    df_flux = load_flux_data('bl6_flux_2025A_Jan_rebinned.txt')
    wav_fine = np.arange(df_flux['x'].min(), df_flux['x'].max(), 0.005) 
    f_interp = interp1d(df_flux['x'], df_flux['Y'], kind='linear', fill_value=0, bounds_error=False)
    flux_fine = np.maximum(0, f_interp(wav_fine))

    # Set time plot limit based on detector distance
    t_plot_limit = 0.08  # 80 ms default

    # Run simulation with chopper parameters
    results = simulate_beam_transmission(
        t_plot_limit, args.offset * 1e-6, args.dd, wav_fine, flux_fine,
        l_chop, opening_s
    )

    if not args.edges_only:
        # Generate the standard 3-panel Forward Model (default output)
        tof_bins, intensity_hist = plot_research_model(
            results, t_plot_limit, args.offset, args.dd, wav_fine, flux_fine,
            chopper_name, l_chop, opening_s
        )
    else:
        # Just compute TOF histogram for edge detection
        tof_bins = np.linspace(0, t_plot_limit, 800)
        intensity_hist = np.zeros(len(tof_bins) - 1)
        for pulse in results:
            hist, _ = np.histogram(pulse['t_det'], bins=tof_bins, weights=pulse['fluxes'])
            intensity_hist += hist

    detected_edges = detect_tof_edges(tof_bins, intensity_hist, edge_guesses, 
                                      window_us=args.window, nth_edges=nth_edges,
                                      edge_types=edge_types,
                                      threshold_pct=args.threshold, use_log=args.log)
    
    print("=== Edge Detection Results ===")
    for i, edge in enumerate(detected_edges):
        print(f"Edge {i+1}: {edge * 1e6:.2f} μs")
    if not detected_edges:
        print("No edges detected")
    
    # Generate the zoomed edge detection figure
    plot_edges_zoom(tof_bins, intensity_hist, args.offset, args.dd, detected_edges,
                    chopper_name, l_chop)
