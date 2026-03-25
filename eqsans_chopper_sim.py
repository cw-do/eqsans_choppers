import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.collections import LineCollection
from scipy.interpolate import interp1d
import tkinter as tk
from tkinter import ttk
from pathlib import Path

H_OVER_MN   = 3956.0
SOURCE_PERIOD = 1.0 / 60.0

FREQ_OPTIONS = {
    60: {"freq": 60.0, "period": 1.0 / 60.0, "period_us": 1e6 / 60.0},
    30: {"freq": 30.0, "period": 1.0 / 30.0, "period_us": 1e6 / 30.0},
}

CHOPPER_CONFIG = {
    "1b": {"L_CHOP": 5.6757668, "OPENING_DEG": 129.605},
    "2b": {"L_CHOP": 7.7757668, "OPENING_DEG": 179.989},
    "3a": {"L_CHOP": 9.4978, "OPENING_DEG": 230.010},
    "3b": {"L_CHOP": 9.5078, "OPENING_DEG": 230.007},
    "1a": {"L_CHOP": 5.6601247, "OPENING_DEG": 129.605},
    "2a": {"L_CHOP": 7.7601247, "OPENING_DEG": 179.989},
}
CHOPPER_NAMES = ["1b", "2b", "3a", "3b", "1a", "2a"]

HEXASUB_PHASE_OFFSET_30HZ = {
    "1b": 29908.92, "2b": 29610.8, "3a": 29452.12, "3b": 29131.2,
    "1a": 30145.78, "2a": 29668.04,
}
HEXASUB_PHASE_OFFSET_60HZ = {
    "1b": 14954.46, "2b": 14805.4, "3a": 14726.06, "3b": 14565.6,
    "1a": 15072.89, "2a": 14834.04,
}
FRAMESKIP_ALIGN_30HZ = {"3a": 33333.33, "3b": 33333.33}


def load_flux_data(file_path: str):
    try:
        df = pd.read_csv(file_path, sep=r'\s+', comment='#', header=0)
        return df
    except Exception:
        wav = np.linspace(0.1, 25, 2000)
        flux = (1 / wav**4) * np.exp(-5 / wav**2) * 1e7
        return pd.DataFrame({'x': wav, 'Y': flux})


def ogc_to_left_edge_s(ogc_us: float, opening_deg: float, period: float) -> float:
    half_open_s = (opening_deg / 360.0) * period / 2.0
    return ogc_us * 1e-6 - half_open_s


def simulate_multi_chopper(wav_fine, flux_fine, choppers, l_det, t_plot_limit, chopper_period):
    is_30hz = abs(chopper_period - 1.0/30.0) < 0.001
    if is_30hz:
        return _simulate_30hz_frameskip(
            wav_fine, flux_fine, choppers, l_det, t_plot_limit, chopper_period
        )
    
    velocities = H_OVER_MN / wav_fine
    passed_trajectories = []

    for p in range(-12, int(t_plot_limit / SOURCE_PERIOD) + 2):
        t_src = p * SOURCE_PERIOD
        t_arrival = t_src + (np.outer(1.0 / velocities, [c['l_chop'] for c in choppers]))

        mask_pass = np.ones(len(wav_fine), dtype=bool)
        for ci, chop in enumerate(choppers):
            rel = (t_arrival[:, ci] - chop['left_edge_s']) % chopper_period
            mask_pass &= rel < chop['opening_s']

        if np.any(mask_pass):
            t_det = t_src + l_det / velocities[mask_pass]
            passed_trajectories.append({
                'p':          p,
                't_src':      t_src,
                'velocities': velocities[mask_pass],
                'fluxes':     flux_fine[mask_pass],
                'wavs':       wav_fine[mask_pass],
                't_det':      t_det,
            })

    return passed_trajectories


def _simulate_30hz_frameskip(wav_fine, flux_fine, choppers, l_det, t_plot_limit, chopper_period):
    """
    30Hz frame-skip mode: choppers align to different source pulses.
    
    In frame-skip mode, the chopper period (33.33ms) is 2x the source period (16.67ms).
    Different choppers deliberately align to different pulses. We check if each
    wavelength can pass ALL choppers at ANY of their periodic openings.
    """
    velocities = H_OVER_MN / wav_fine
    passed_trajectories = []

    for p in range(-12, int(t_plot_limit / SOURCE_PERIOD) + 2):
        t_src = p * SOURCE_PERIOD
        mask_pass = np.ones(len(wav_fine), dtype=bool)

        for ci, chop in enumerate(choppers):
            t_arr = t_src + chop['l_chop'] / velocities
            rel = (t_arr - chop['left_edge_s']) % chopper_period
            mask_pass &= rel < chop['opening_s']

        if np.any(mask_pass):
            t_det = t_src + l_det / velocities[mask_pass]
            passed_trajectories.append({
                'p':          p,
                't_src':      t_src,
                'velocities': velocities[mask_pass],
                'fluxes':     flux_fine[mask_pass],
                'wavs':       wav_fine[mask_pass],
                't_det':      t_det,
            })

    return passed_trajectories


def build_tof_histogram(passed_data, t_plot_limit, n_bins=800):
    tof_bins = np.linspace(0, t_plot_limit, n_bins + 1)
    intensity = np.zeros(n_bins)
    for pulse in passed_data:
        h, _ = np.histogram(pulse['t_det'], bins=tof_bins, weights=pulse['fluxes'])
        intensity += h
    return tof_bins, intensity


class ChopperSimApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("EQSANS Multi-Chopper Simulator")

        self._load_flux()
        self._build_ui()

    def _load_flux(self):
        df = load_flux_data('bl6_flux_2025A_Jan_rebinned.txt')
        wav_raw = df['x'].values
        flux_raw = df['Y'].values
        wav_fine = np.arange(wav_raw.min(), wav_raw.max(), 0.005)
        f_interp = interp1d(wav_raw, flux_raw, kind='linear',
                            fill_value=0, bounds_error=False)
        self._wav_fine  = wav_fine
        self._flux_fine = np.maximum(0, f_interp(wav_fine))

    def _get_freq_settings(self):
        freq_hz = self._freq_var.get()
        return FREQ_OPTIONS[freq_hz]

    def _build_ui(self):
        PAD = dict(padx=6, pady=3)

        ctrl = tk.Frame(self.root, bd=1, relief='groove')
        ctrl.pack(side='left', fill='y', padx=6, pady=6)

        tk.Label(ctrl, text="Detector distance (m):", font=("", 9)).grid(
            row=0, column=0, sticky='e', **PAD)
        self._det_var = tk.StringVar(value="10.006")
        det_entry = tk.Entry(ctrl, textvariable=self._det_var, width=10)
        det_entry.grid(row=0, column=1, **PAD)
        det_entry.bind('<Return>', lambda e: self._on_calculate())

        self._all_entries: list = [det_entry]

        freq_frame = tk.Frame(ctrl)
        freq_frame.grid(row=0, column=2, columnspan=2, sticky='w', **PAD)
        tk.Label(freq_frame, text="Frequency:", font=("", 9)).pack(side='left')
        self._freq_var = tk.IntVar(value=60)
        tk.Radiobutton(freq_frame, text="60 Hz", variable=self._freq_var,
                       value=60, font=("", 9),
                       command=self._on_freq_change).pack(side='left', padx=2)
        tk.Radiobutton(freq_frame, text="30 Hz", variable=self._freq_var,
                       value=30, font=("", 9),
                       command=self._on_freq_change).pack(side='left', padx=2)

        sep = ttk.Separator(ctrl, orient='horizontal')
        sep.grid(row=1, column=0, columnspan=4, sticky='ew', pady=6)

        headers = ["Chopper", "Enable", "OGC phase (µs)", "Mech. offset (µs)"]
        for col, h in enumerate(headers):
            tk.Label(ctrl, text=h, font=("", 9, "bold")).grid(
                row=2, column=col, sticky='w', **PAD)

        self._enabled_vars: dict[str, tk.BooleanVar] = {}
        self._ogc_vars:     dict[str, tk.StringVar]  = {}
        self._mech_vars:    dict[str, tk.StringVar]  = {}
        self._opening_labels: dict[str, tk.Label]   = {}

        default_ogc = {
            "1a": "8000", "1b": "8000",
            "2a": "11000", "2b": "11000",
            "3a": "13500", "3b": "13500",
        }

        period_us = self._get_freq_settings()["period_us"]
        for i, name in enumerate(CHOPPER_NAMES):
            row = i + 3
            cfg = CHOPPER_CONFIG[name]

            opening_us = (cfg['OPENING_DEG'] / 360.0) * period_us
            lbl_frame = tk.Frame(ctrl)
            lbl_frame.grid(row=row, column=0, sticky='w', **PAD)
            tk.Label(lbl_frame,
                     text=f"{name}  ({cfg['L_CHOP']:.4f} m, {cfg['OPENING_DEG']:.1f}°)",
                     font=("", 9)).pack(anchor='w')
            opening_lbl = tk.Label(lbl_frame,
                     text=f"  opening gap: {opening_us:.1f} µs",
                     font=("", 8), fg='#555555')
            opening_lbl.pack(anchor='w')
            self._opening_labels[name] = opening_lbl

            en_var = tk.BooleanVar(value=False)
            self._enabled_vars[name] = en_var
            tk.Checkbutton(ctrl, variable=en_var,
                           command=self._on_calculate).grid(row=row, column=1, **PAD)

            ogc_var = tk.StringVar(value=default_ogc[name])
            self._ogc_vars[name] = ogc_var
            ogc_entry = tk.Entry(ctrl, textvariable=ogc_var, width=10)
            ogc_entry.grid(row=row, column=2, **PAD)
            ogc_entry.bind('<Return>', lambda e: self._on_calculate())
            self._all_entries.append(ogc_entry)

            mech_var = tk.StringVar(value="0")
            self._mech_vars[name] = mech_var
            mech_entry = tk.Entry(ctrl, textvariable=mech_var, width=10)
            mech_entry.grid(row=row, column=3, **PAD)
            mech_entry.bind('<Return>', lambda e: self._on_calculate())
            self._all_entries.append(mech_entry)

        sep2 = ttk.Separator(ctrl, orient='horizontal')
        sep2.grid(row=10, column=0, columnspan=4, sticky='ew', pady=6)

        hexasub_frame = tk.Frame(ctrl)
        hexasub_frame.grid(row=11, column=0, columnspan=4, sticky='w', **PAD)
        self._hexasub_var = tk.BooleanVar(value=False)
        tk.Checkbutton(hexasub_frame, text="hexaSub phases",
                       variable=self._hexasub_var, font=("", 9),
                       command=self._on_hexasub_toggle).pack(side='left')
        self._hexasub_label = tk.Label(hexasub_frame, 
                                       text="(auto-apply calibration offset)",
                                       font=("", 8), fg='#666666')
        self._hexasub_label.pack(side='left', padx=4)

        self._status_var = tk.StringVar(value="Ready.")
        tk.Label(ctrl, textvariable=self._status_var, fg='darkblue',
                 font=("", 9), wraplength=220, justify='left').grid(
            row=12, column=0, columnspan=3, sticky='w', **PAD)

        btn_frame = tk.Frame(ctrl)
        btn_frame.grid(row=13, column=0, columnspan=3, pady=8)

        tk.Button(btn_frame, text="Calculate", font=("", 10, "bold"),
                  bg="#4CAF50", fg="white", padx=10,
                  command=self._on_calculate).pack(side='left', padx=4)

        tk.Button(btn_frame, text="Clear", font=("", 10),
                  command=self._on_clear).pack(side='left', padx=4)

        self._log_scale = False
        self._btn_loglin = tk.Button(btn_frame, text="Log scale", font=("", 10),
                                     command=self._toggle_log_scale)
        self._btn_loglin.pack(side='left', padx=4)

        plot_frame = tk.Frame(self.root)
        plot_frame.pack(side='left', fill='both', expand=True, padx=6, pady=6)

        self._fig, (self._ax_dist, self._ax_tof) = plt.subplots(
            2, 1, figsize=(9, 7),
            gridspec_kw={'height_ratios': [3, 2], 'hspace': 0.42}
        )
        self._fig.subplots_adjust(left=0.1, right=0.97, top=0.95, bottom=0.09)
        self._fig.patch.set_facecolor('#f8f8f8')
        self._ax_dist.set_title("Distance–Time Diagram", fontsize=11)
        self._ax_dist.set_xlabel("Time (ms)", fontsize=9)
        self._ax_dist.set_ylabel("Distance from source (m)", fontsize=9)
        self._ax_tof.set_title("Detector TOF Spectrum", fontsize=11)
        self._ax_tof.set_xlabel("TOF at detector (µs)", fontsize=9)
        self._ax_tof.set_ylabel("Intensity (a.u.)", fontsize=9)

        self._canvas = FigureCanvasTkAgg(self._fig, master=plot_frame)
        self._canvas.get_tk_widget().pack(fill='both', expand=True)
        self._canvas.draw()

    def _on_freq_change(self):
        period_us = self._get_freq_settings()["period_us"]
        for name in CHOPPER_NAMES:
            cfg = CHOPPER_CONFIG[name]
            opening_us = (cfg['OPENING_DEG'] / 360.0) * period_us
            self._opening_labels[name].config(text=f"  opening gap: {opening_us:.1f} µs")
        self._update_hexasub_offsets()

    def _on_hexasub_toggle(self):
        self._update_hexasub_offsets()
        self._on_calculate()

    def _update_hexasub_offsets(self):
        if not self._hexasub_var.get():
            for name in CHOPPER_NAMES:
                self._mech_vars[name].set("0")
            return
        
        freq_hz = self._freq_var.get()
        if freq_hz == 30:
            for name in CHOPPER_NAMES:
                offset = -HEXASUB_PHASE_OFFSET_30HZ[name]
                align = FRAMESKIP_ALIGN_30HZ.get(name, 0)
                self._mech_vars[name].set(f"{offset + align:.2f}")
        else:
            for name in CHOPPER_NAMES:
                offset = -HEXASUB_PHASE_OFFSET_60HZ[name]
                self._mech_vars[name].set(f"{offset:.2f}")

    def _active_choppers(self):
        period = self._get_freq_settings()["period"]
        choppers = []
        for name in CHOPPER_NAMES:
            if not self._enabled_vars[name].get():
                continue
            cfg = CHOPPER_CONFIG[name]
            try:
                ogc_us   = float(self._ogc_vars[name].get())
                mech_us  = float(self._mech_vars[name].get())
            except ValueError:
                self._status_var.set(f"Invalid OGC or mech. offset for chopper {name}.")
                return None
            effective_ogc_us = ogc_us + mech_us
            left_edge_s = ogc_to_left_edge_s(effective_ogc_us, cfg['OPENING_DEG'], period)
            choppers.append({
                'name':        name,
                'l_chop':      cfg['L_CHOP'],
                'opening_s':   (cfg['OPENING_DEG'] / 360.0) * period,
                'left_edge_s': left_edge_s,
                'ogc_us':      ogc_us,
                'mech_us':     mech_us,
                'eff_ogc_us':  effective_ogc_us,
            })
        return choppers

    def _on_calculate(self):
        choppers = self._active_choppers()
        if choppers is None:
            return
        if not choppers:
            self._status_var.set("No choppers enabled. Check at least one.")
            return

        try:
            l_det = float(self._det_var.get())
        except ValueError:
            self._status_var.set("Invalid detector distance.")
            return

        self._status_var.set("Calculating…")
        self.root.update_idletasks()

        period = self._get_freq_settings()["period"]
        t_plot_limit = max(0.08, l_det / H_OVER_MN * 25 * 1.5)

        passed = simulate_multi_chopper(
            self._wav_fine, self._flux_fine, choppers, l_det, t_plot_limit, period
        )
        tof_bins, intensity = build_tof_histogram(passed, t_plot_limit)

        self._draw_plots(choppers, passed, tof_bins, intensity, l_det, t_plot_limit, period)

        n_pulses = len(passed)
        self._status_var.set(
            f"Done. {n_pulses} pulse groups passed. "
            f"Peak TOF: {tof_bins[:-1][np.argmax(intensity)] * 1e6:.1f} µs"
            if intensity.any() else "Done. No neutrons passed all choppers."
        )

    def _draw_plots(self, choppers, passed, tof_bins, intensity, l_det, t_plot_limit, period):
        self._ax_dist.cla()
        self._ax_tof.cla()

        ax1 = self._ax_dist
        ax2 = self._ax_tof

        tof_ms = tof_bins[:-1] * 1e3

        ax1.set_xlabel("Time (ms)", fontsize=9)
        ax1.set_ylabel("Distance from source (m)", fontsize=9)
        ax1.set_xlim(0, t_plot_limit * 1e3)
        ax1.set_ylim(0, l_det * 1.05)

        colors_chop = ['red', 'tomato', 'darkorange', 'orange', 'darkred', 'firebrick']
        for ci, chop in enumerate(choppers):
            color = colors_chop[ci % len(colors_chop)]
            for k in range(-2, int(t_plot_limit / period) + 2):
                t_closed_start = (chop['left_edge_s'] + chop['opening_s'] + k * period) * 1e3
                closed_width   = (period - chop['opening_s']) * 1e3
                ax1.add_patch(plt.Rectangle(
                    (t_closed_start, chop['l_chop'] - 0.08),
                    closed_width, 0.16,
                    color=color, alpha=0.5, zorder=3
                ))
            ax1.axhline(chop['l_chop'], color=color, lw=0.5, ls=':', alpha=0.6)
            label = f"{chop['name']}  OGC={chop['ogc_us']:.0f} µs"
            if chop['mech_us'] != 0:
                label += f"  mech={chop['mech_us']:.0f}  eff={chop['eff_ogc_us']:.0f} µs"
            is_b = chop['name'].endswith('b')
            y_offset = +0.1 if is_b else -0.18
            va = 'bottom' if is_b else 'top'
            ax1.text(t_plot_limit * 1e3 * 0.01, chop['l_chop'] + y_offset,
                     label, fontsize=7, color=color, va=va)

        ax1.axhline(l_det, color='green', lw=1, ls='--', alpha=0.7)
        ax1.text(t_plot_limit * 1e3 * 0.01, l_det + 0.1,
                 f"Detector ({l_det} m)", fontsize=7, color='green')

        all_lines = []
        for pulse in passed:
            step = max(1, len(pulse['velocities']) // 15)
            for v in pulse['velocities'][::step]:
                t0_ms = pulse['t_src'] * 1e3
                t1_ms = (pulse['t_src'] + l_det / v) * 1e3
                all_lines.append([(t0_ms, 0), (t1_ms, l_det)])

        if all_lines:
            lc = LineCollection(all_lines, colors='royalblue', alpha=0.15, linewidths=0.5)
            ax1.add_collection(lc)

        ax1.set_title(
            f"Distance–Time Diagram  —  "
            f"{', '.join(c['name'] for c in choppers)}",
            fontsize=10
        )

        ax2.plot(tof_ms, intensity, color='purple', lw=1.2)
        ax2.fill_between(tof_ms, 0, intensity, color='purple', alpha=0.25)
        ax2.set_xlabel("TOF at detector (ms)", fontsize=9)
        ax2.set_ylabel("Intensity (a.u.)", fontsize=9)
        ax2.set_xlim(0, t_plot_limit * 1e3)
        ax2.set_title("Detector TOF Spectrum", fontsize=10)
        ax2.grid(True, alpha=0.3, ls='--')

        if self._log_scale:
            ax2.set_yscale('log')

        frame_ms = period * 1e3
        n_frames = int(t_plot_limit / period) + 1
        for n in range(1, n_frames + 1):
            t_frame = n * frame_ms
            ax2.axvline(t_frame, color='black', ls='--', lw=0.8, alpha=0.5)
            ax2.text(t_frame, 1.0, f"{n}×frame",
                     fontsize=7, color='gray', ha='right', va='top', rotation=90,
                     transform=ax2.get_xaxis_transform())

        if intensity.any():
            peak_ms = tof_ms[np.argmax(intensity)]
            ax2.axvline(peak_ms, color='red', ls='--', lw=1, alpha=0.7)
            ax2.text(peak_ms, 0.95, f"{peak_ms * 1e3:.0f} µs",
                     fontsize=8, color='red', ha='left',
                     transform=ax2.get_xaxis_transform())

        self._canvas.draw()

    def _toggle_log_scale(self):
        self._log_scale = not self._log_scale
        self._ax_tof.set_yscale('log' if self._log_scale else 'linear')
        self._btn_loglin.config(text='Linear scale' if self._log_scale else 'Log scale')
        self._canvas.draw_idle()

    def _on_clear(self):
        self._ax_dist.cla()
        self._ax_tof.cla()
        self._ax_dist.set_title("Distance–Time Diagram", fontsize=11)
        self._ax_dist.set_xlabel("Time (ms)", fontsize=9)
        self._ax_dist.set_ylabel("Distance from source (m)", fontsize=9)
        self._ax_tof.set_title("Detector TOF Spectrum", fontsize=11)
        self._ax_tof.set_xlabel("TOF at detector (µs)", fontsize=9)
        self._ax_tof.set_ylabel("Intensity (a.u.)", fontsize=9)
        self._log_scale = False
        self._btn_loglin.config(text='Log scale')
        self._canvas.draw()
        self._status_var.set("Ready.")


def main():
    import signal
    root = tk.Tk()
    matplotlib.rcParams['keymap.yscale'] = []
    matplotlib.rcParams['keymap.home']   = ['h', 'home']
    app = ChopperSimApp(root)

    _quit_flag = [False]

    def _on_sigint(sig, frame):
        _quit_flag[0] = True

    def _poll():
        if _quit_flag[0]:
            plt.close('all')
            root.quit()
            return
        root.after(100, _poll)

    def _on_close():
        _quit_flag[0] = True

    signal.signal(signal.SIGINT, _on_sigint)
    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.after(100, _poll)
    root.mainloop()
    plt.close('all')


if __name__ == "__main__":
    main()
