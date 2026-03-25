#!/usr/bin/env python
"""
Generate distance-time diagrams for the chopper calibration guide.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import LineCollection
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

H_OVER_MN = 3956.0
SOURCE_PERIOD = 1.0 / 60.0

CHOPPER_CONFIG = {
    "1b": {"L_CHOP": 5.6757668, "OPENING_DEG": 129.605},
    "2b": {"L_CHOP": 7.7757668, "OPENING_DEG": 179.989},
    "3a": {"L_CHOP": 9.4978, "OPENING_DEG": 230.010},
    "3b": {"L_CHOP": 9.5078, "OPENING_DEG": 230.007},
    "1a": {"L_CHOP": 5.6601247, "OPENING_DEG": 129.605},
    "2a": {"L_CHOP": 7.7601247, "OPENING_DEG": 179.989},
}

COLORS = {
    "1a": "#1f77b4", "1b": "#1f77b4",
    "2a": "#ff7f0e", "2b": "#ff7f0e", 
    "3a": "#2ca02c", "3b": "#2ca02c",
}


def calc_wavelengths(start_wl, sdd_m, stm_m):
    det_loc_mm = (stm_m + np.sqrt(sdd_m**2 + 0.707107**2)) * 1000
    bw = 3.956e6 / det_loc_mm / 60.0
    return [0, start_wl, start_wl + bw, start_wl + 2*bw, start_wl + 3*bw], bw


def calc_30hz_phases(start_wl, sdd_m, stm_m):
    wl, bw = calc_wavelengths(start_wl, sdd_m, stm_m)
    period_30 = 1.0 / 30.0
    
    L = {name: cfg["L_CHOP"] for name, cfg in CHOPPER_CONFIG.items()}
    OPENING = {name: cfg["OPENING_DEG"] for name, cfg in CHOPPER_CONFIG.items()}
    
    left_edge = {}
    opening_s = {}
    
    for name in ["1b", "2b", "3a", "3b"]:
        opening_s[name] = (OPENING[name] / 360.0) * period_30
    
    left_edge["3b"] = L["3b"] / H_OVER_MN * wl[1]
    left_edge["2b"] = L["2b"] / H_OVER_MN * wl[2] - opening_s["2b"]
    left_edge["1b"] = L["1b"] / H_OVER_MN * wl[3] - SOURCE_PERIOD
    left_edge["3a"] = (L["3a"] / H_OVER_MN * wl[4] - SOURCE_PERIOD) - opening_s["3a"]
    
    return left_edge, opening_s, wl, bw


def calc_60hz_phases(start_wl, sdd_m, stm_m):
    wl, bw = calc_wavelengths(start_wl, sdd_m, stm_m)
    period_60 = 1.0 / 60.0
    
    L = {name: cfg["L_CHOP"] for name, cfg in CHOPPER_CONFIG.items()}
    OPENING = {name: cfg["OPENING_DEG"] for name, cfg in CHOPPER_CONFIG.items()}
    
    left_edge = {}
    opening_s = {}
    
    for name in ["1b", "2b", "3a", "3b"]:
        opening_s[name] = (OPENING[name] / 360.0) * period_60
    
    left_edge["3b"] = L["3b"] / H_OVER_MN * wl[1]
    left_edge["1b"] = L["1b"] / H_OVER_MN * wl[2] - opening_s["1b"]
    left_edge["2b"] = L["2b"] / H_OVER_MN * wl[1]
    left_edge["3a"] = L["3a"] / H_OVER_MN * wl[2] - opening_s["3a"]
    
    return left_edge, opening_s, wl, bw


def calc_mono_phases_hexasub(mono_wl, spread, sdd_m, stm_m):
    """
    Calculate phases for monochromatic mode using hexaSub.c logic.
    
    hexaSub monochromatic mode alignment:
    - 1A, 2A, 3A: Opening edge at wl[1] (lower wavelength)
    - 1B, 2B, 3B: Closing edge at wl[2] (upper wavelength)
    """
    from math import fmod
    
    period_60 = 1.0 / 60.0
    frame_width = 1.0e6 / 60.0
    half_angle_to_sec = 1.0 / 360.0 / 60.0 / 2.0
    
    wl1 = mono_wl * (1 - spread/2)
    wl2 = mono_wl * (1 + spread/2)
    
    L_mm = {
        "1a": 5657.3247, "2a": 7760.1247, "3a": 9497.8,
        "1b": 5672.7668, "2b": 7775.7668, "3b": 9507.8,
    }
    OPENING_DEG = {
        "1a": 129.605, "1b": 129.605,
        "2a": 179.989, "2b": 179.989,
        "3a": 230.010, "3b": 230.007,
    }
    PHASE_OFFSET_60HZ = {
        "1a": 14954.46, "2a": 14805.4, "3a": 14726.06,
        "1b": 15072.89, "2b": 14834.04, "3b": 14565.6,
    }
    
    phases = {}
    
    for name in ["1a", "2a", "3a"]:
        phase = L_mm[name] / 3.956e6 * wl1
        phase += OPENING_DEG[name] * half_angle_to_sec
        phase = 1.0e6 * phase + PHASE_OFFSET_60HZ[name]
        phase = fmod(phase, frame_width)
        phases[name] = phase
    
    for name in ["1b", "2b", "3b"]:
        phase = L_mm[name] / 3.956e6 * wl2
        phase -= OPENING_DEG[name] * half_angle_to_sec
        phase = 1.0e6 * phase + PHASE_OFFSET_60HZ[name]
        phase = fmod(phase, frame_width)
        phases[name] = phase
    
    left_edge = {}
    opening_s = {}
    
    for name in CHOPPER_CONFIG.keys():
        opening_s[name] = (OPENING_DEG[name] / 360.0) * period_60
        
        ogc_us = phases[name]
        offset = -PHASE_OFFSET_60HZ[name]
        effective_ogc_us = ogc_us + offset
        
        half_open_s = opening_s[name] / 2.0
        left_edge[name] = effective_ogc_us * 1e-6 - half_open_s
    
    return left_edge, opening_s, wl1, wl2, mono_wl, phases


def simulate_choppers(choppers, l_det, chopper_period, t_plot_limit):
    wav_fine = np.arange(0.5, 25, 0.01)
    velocities = H_OVER_MN / wav_fine
    passed = []
    
    for p in range(-2, int(t_plot_limit / SOURCE_PERIOD) + 2):
        t_src = p * SOURCE_PERIOD
        mask = np.ones(len(wav_fine), dtype=bool)
        
        for chop in choppers:
            t_arr = t_src + chop['l_chop'] / velocities
            rel = (t_arr - chop['left_edge_s']) % chopper_period
            mask &= rel < chop['opening_s']
        
        if np.any(mask):
            passed.append({
                't_src': t_src,
                'velocities': velocities[mask],
                'wavs': wav_fine[mask],
            })
    
    return passed


def draw_diagram(ax, choppers, l_det, chopper_period, t_plot_limit, title, 
                 show_trajectories=True, wl_labels=None):
    ax.set_xlim(0, t_plot_limit * 1e3)
    ax.set_ylim(0, l_det + 0.5)
    
    n_frames = int(t_plot_limit / chopper_period) + 2
    
    for chop in choppers:
        name = chop['name']
        l_chop = chop['l_chop']
        left_edge = chop['left_edge_s']
        opening = chop['opening_s']
        color = COLORS.get(name, 'gray')
        
        for k in range(-1, n_frames):
            closed_start = (left_edge + opening + k * chopper_period) * 1e3
            closed_width = (chopper_period - opening) * 1e3
            
            if closed_start + closed_width > 0 and closed_start < t_plot_limit * 1e3:
                rect = patches.Rectangle(
                    (closed_start, l_chop - 0.15), closed_width, 0.3,
                    facecolor=color, alpha=0.4, edgecolor=color, linewidth=0.5
                )
                ax.add_patch(rect)
        
        ax.axhline(l_chop, color=color, linestyle='--', linewidth=0.8, alpha=0.7)
        
        y_offset = 0.25 if 'b' in name else -0.35
        ax.text(0.5, l_chop + y_offset, f"{name}", fontsize=9, 
                color=color, fontweight='bold', va='center')
    
    ax.axhline(l_det, color='red', linestyle='-', linewidth=1.5)
    ax.text(0.5, l_det + 0.2, "Detector", fontsize=9, color='red', fontweight='bold')
    
    if show_trajectories:
        passed = simulate_choppers(choppers, l_det, chopper_period, t_plot_limit)
        
        lines = []
        for pulse in passed:
            t_src = pulse['t_src']
            for v in pulse['velocities'][::20]:
                t_det = t_src + l_det / v
                if 0 <= t_src * 1e3 <= t_plot_limit * 1e3 or 0 <= t_det * 1e3 <= t_plot_limit * 1e3:
                    lines.append([(t_src * 1e3, 0), (t_det * 1e3, l_det)])
        
        if lines:
            lc = LineCollection(lines, colors='steelblue', linewidths=0.3, alpha=0.5)
            ax.add_collection(lc)
    
    for k in range(int(t_plot_limit / chopper_period) + 1):
        t_frame = k * chopper_period * 1e3
        ax.axvline(t_frame, color='gray', linestyle=':', linewidth=0.5, alpha=0.5)
    
    ax.set_xlabel("Time (ms)", fontsize=10)
    ax.set_ylabel("Distance from source (m)", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)


def generate_60hz_diagram():
    start_wl = 2.5
    sdd_m = 4.0
    stm_m = 14.122
    l_det = stm_m + sdd_m
    
    left_edge, opening_s, wl, bw = calc_60hz_phases(start_wl, sdd_m, stm_m)
    
    choppers = []
    for name in ["1b", "2b", "3a", "3b"]:
        choppers.append({
            'name': name,
            'l_chop': CHOPPER_CONFIG[name]['L_CHOP'],
            'left_edge_s': left_edge[name],
            'opening_s': opening_s[name],
        })
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    period_60 = 1.0 / 60.0
    t_plot_limit = 0.05
    
    title = f"60 Hz Mode: {start_wl}–{wl[2]:.1f} Å (SDD={sdd_m}m)"
    draw_diagram(ax, choppers, l_det, period_60, t_plot_limit, title)
    
    ax.text(0.98, 0.02, f"Wavelength band: {wl[1]:.2f}–{wl[2]:.2f} Å\nBandwidth: {bw:.2f} Å",
            transform=ax.transAxes, fontsize=9, va='bottom', ha='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig("figures/diagram_60hz.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("Generated: figures/diagram_60hz.png")


def generate_30hz_diagram():
    start_wl = 2.5
    sdd_m = 4.0
    stm_m = 14.122
    l_det = stm_m + sdd_m
    
    left_edge, opening_s, wl, bw = calc_30hz_phases(start_wl, sdd_m, stm_m)
    
    choppers = []
    for name in ["1b", "2b", "3a", "3b"]:
        choppers.append({
            'name': name,
            'l_chop': CHOPPER_CONFIG[name]['L_CHOP'],
            'left_edge_s': left_edge[name],
            'opening_s': opening_s[name],
        })
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    period_30 = 1.0 / 30.0
    t_plot_limit = 0.07
    
    title = f"30 Hz Frame-Skip Mode: Bands at {wl[1]:.1f}–{wl[2]:.1f} Å and {wl[3]:.1f}–{wl[4]:.1f} Å"
    draw_diagram(ax, choppers, l_det, period_30, t_plot_limit, title)
    
    ax.text(0.98, 0.02, 
            f"Band 1: {wl[1]:.2f}–{wl[2]:.2f} Å (current pulse)\n"
            f"Band 2: {wl[3]:.2f}–{wl[4]:.2f} Å (previous pulse)\n"
            f"Bandwidth per band: {bw:.2f} Å",
            transform=ax.transAxes, fontsize=9, va='bottom', ha='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig("figures/diagram_30hz.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("Generated: figures/diagram_30hz.png")


def generate_mono_diagram():
    mono_wl = 10.0
    spread = 0.10
    sdd_m = 4.0
    stm_m = 14.122
    l_det = stm_m + sdd_m
    
    left_edge, opening_s, wl_min, wl_max, mono_wl, phases = calc_mono_phases_hexasub(mono_wl, spread, sdd_m, stm_m)
    
    print(f"Monochromatic mode: {mono_wl} Å ± {spread*100}%")
    print(f"  Wavelength range: {wl_min:.2f} - {wl_max:.2f} Å")
    print(f"  hexaSub phases (OGC, µs):")
    for name in ["1a", "1b", "2a", "2b", "3a", "3b"]:
        print(f"    {name}: {phases[name]:.2f}")
    
    choppers = []
    for name in ["1a", "1b", "2a", "2b", "3a", "3b"]:
        choppers.append({
            'name': name,
            'l_chop': CHOPPER_CONFIG[name]['L_CHOP'],
            'left_edge_s': left_edge[name],
            'opening_s': opening_s[name],
        })
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    period_60 = 1.0 / 60.0
    t_plot_limit = 0.07
    
    title = f"Monochromatic Mode: {mono_wl:.0f} Å ± {spread*100:.0f}% (All 6 Choppers)"
    draw_diagram(ax, choppers, l_det, period_60, t_plot_limit, title)
    
    ax.text(0.98, 0.02, 
            f"Center wavelength: {mono_wl:.1f} Å\n"
            f"Spread: ±{spread*100:.0f}% ({wl_min:.2f}–{wl_max:.2f} Å)\n"
            f"All 6 choppers active",
            transform=ax.transAxes, fontsize=9, va='bottom', ha='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig("figures/diagram_mono.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("Generated: figures/diagram_mono.png")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("Generating distance-time diagrams...")
    generate_60hz_diagram()
    generate_30hz_diagram()
    generate_mono_diagram()
    print("Done!")
