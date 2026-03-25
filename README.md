# EQSANS Chopper Calibration Tools

Python tools for extracting, visualizing, and analyzing TOF spectra from EQSANS neutron scattering data.

## Requirements

### Option 1: Local Virtual Environment (Recommended)

A pre-configured virtual environment is included in this directory:

```bash
source .venv/bin/activate
```

To deactivate when done:

```bash
deactivate
```

### Option 2: Conda Environment

Alternatively, use the shared conda environment:

```bash
source /SNS/users/ccd/miniforge3/etc/profile.d/conda.sh
conda activate py312
```

### Required Packages

numpy, scipy, pandas, matplotlib, h5py

To recreate the virtual environment from scratch:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install numpy scipy pandas matplotlib h5py
```

## Tools

### 1. find_edges_ui.py (Primary Tool)

Interactive GUI for finding edges in monitor spectra and calculating phase offsets for chopper calibration.

**Features:**
- Load monitor spectrum from .dat file or directly from NeXus (IPTS/Run)
- Click on plot to mark edge positions
- Fit edges using error function (erf) model
- Phase offset calculator with chopper configurations
- Export monitor/detector spectra as ASCII files

**Usage:**

```bash
# Start with a spectrum file (60 Hz mode, default)
python find_edges_ui.py 176475_monitor.dat

# Start in 30 Hz mode (for 30 Hz chopper operation)
python find_edges_ui.py --30hz 176475_monitor.dat

# Start without file (load from NeXus via IPTS/Run)
python find_edges_ui.py

# 30 Hz mode without file
python find_edges_ui.py --30hz
```

**30 Hz Mode:**

Use `--30hz` flag when choppers are operating at 30 Hz. In this mode:
- Frame period = 33333.33 µs (instead of 16666.67 µs at 60 Hz)
- Chopper opening times are doubled (same angle, slower rotation)
- Phase calculations use the 30 Hz chopper period
- Window title and Phase Calculator show "[30 Hz MODE]" indicator

Note: The SNS source still operates at 60 Hz. In 30 Hz chopper mode, two source pulses arrive during each chopper opening window.

**Controls:**
| Key | Action |
|-----|--------|
| Left-click | Add edge marker |
| Right-click | Remove nearest marker |
| `f` | Fit all marked edges |
| `c` | Clear all markers |
| `s` | Save fit results |
| `g` | Toggle log/linear scale |
| `l` | Set Left E of blade to mouse X |
| `r` | Set Right E of blade to mouse X |
| `q` | Quit |

**Phase Calculator Window:**
- Select chopper (1a, 1b, 2a, 2b, 3a, 3b)
- Enter IPTS and Run number, click **Load** to fetch spectrum from NeXus
- Enter edge positions manually or use `l`/`r` keys to capture from plot
- Click **Export Spectrum** to save monitor/detector data as ASCII

**Chopper configurations:**

| Chopper | Distance (m) | Opening (°) |
|---------|-------------|-------------|
| 1a | 5.6601 | 129.605 |
| 1b | 5.6758 | 129.605 |
| 2a | 7.7601 | 179.989 |
| 2b | 7.7758 | 179.989 |
| 3a | 9.4978 | 230.010 |
| 3b | 9.5078 | 230.007 |

---

### 2. extract_monitor.py

Extract monitor and detector spectra from NeXus files.

```bash
# Extract spectrum and save to file
python extract_monitor.py 176475

# Extract with plot
python extract_monitor.py 176475 --plot

# Specify IPTS (default: 37424)
python extract_monitor.py 176475 --ipts 12345 --plot

# List all runs in IPTS
python extract_monitor.py --list
python extract_monitor.py --list --ipts 12345
```

**Output files:**
- `{run}_monitor.dat` - Monitor spectrum (TOF µs, intensity)
- `{run}_detector.dat` - Detector sum spectrum
- `{run}_spectra.png` - Two-panel plot (if --plot)

---

### 3. find_edges.py

Find rising/falling edges in spectrum data using error function (erf) fitting (command-line version).

```bash
# Find two edges with initial guesses
python find_edges.py 176475_monitor.dat --edges 5000,10000

# Adjust search window (default: 500 µs)
python find_edges.py 176475_monitor.dat --edges 5000,10000 --window 800

# Use 1%/99% thresholds instead of 5%/95%
python find_edges.py 176475_monitor.dat --edges 5000,10000 --threshold 1,99

# Include raw data threshold crossing
python find_edges.py 176475_monitor.dat --edges 5000,10000 --raw
```

**Output:**
- Edge positions (midpoint ± uncertainty)
- Edge boundaries (start/end at threshold levels)
- `{input}_edges.png` - Spectrum with fitted edges

---

### 4. onechopper_diagram.py

Simulate single chopper transmission and detect edges in TOF space.

```bash
# Basic simulation with default chopper (1b)
python onechopper_diagram.py

# Select chopper (1a, 1b, 2a, 2b, 3a, 3b)
python onechopper_diagram.py --chopper 3a

# Set phase offset (microseconds)
python onechopper_diagram.py --chopper 3a --offset 1000

# Set detector distance (meters)
python onechopper_diagram.py --chopper 3a --dd 4.0

# Detect edges with initial guesses
python onechopper_diagram.py --chopper 3a --offset 1000 --edges 12500,14500

# Adjust edge search window (default: 1000 µs)
python onechopper_diagram.py --chopper 3a --edges 12500,14500 --window 500

# Select which edge to find when multiple exist (1=biggest, 2=2nd biggest)
python onechopper_diagram.py --chopper 3a --offset 9000 --edges 4000,9500 --window 3000 --nth 2,1

# Use threshold mode to find where intensity crosses a percentage level
python onechopper_diagram.py --chopper 3a --offset 9000 --edges 3000,9500 --window 2000 --threshold 95

# Generate only edge detection plot (skip 3-panel diagram)
python onechopper_diagram.py --chopper 3a --edges-only --edges 12500,14500

# Specify edge types: f=falling, r=rising (default: first=falling, rest=rising)
python onechopper_diagram.py --chopper 2a --edges 1550,10900 --edge-types f,f
```

**Note:** The `--offset` parameter defines the **left edge of the chopper opening gap** (i.e., when the gap starts to open, not the center of the opening).

**Output files:**
- `onechopper_{chopper}_dd{distance}_off{offset}.png` - 3-panel diagram
- `onechopper_{chopper}_dd{distance}_off{offset}_edges.png` - Edge detection plot

---

### 5. eqsans_chopper_sim.py

Multi-chopper neutron beam simulator with GUI.

```bash
python eqsans_chopper_sim.py
```

**Features:**
- **Frequency selector**: Choose between 60 Hz and 30 Hz chopper operation modes
- Enable/disable individual choppers (1a, 1b, 2a, 2b, 3a, 3b)
- Set OGC phase and mechanical offset per chopper
- **hexaSub phases checkbox**: Apply calibration offsets for hexaSub-calculated phases
- Distance–time diagram showing chopper blade positions and neutron trajectories
  - a-series chopper labels appear **below** the blade
  - b-series chopper labels appear **above** the blade
- Detector TOF spectrum with frame boundary markers
- Toggle log/linear scale on the TOF spectrum
- Calculate button for on-demand simulation

**30 Hz Mode:**

Select "30 Hz" radio button to simulate 30 Hz chopper operation:
- Choppers rotate at 30 Hz (period = 33333.33 µs)
- Opening gap times are doubled compared to 60 Hz
- Source pulses still arrive at 60 Hz (SNS source frequency)
- Two source pulses contribute to each detector frame
- Frame boundary markers adjust to 30 Hz period

**hexaSub Phases Checkbox:**

The `hexaSub phases` checkbox enables compatibility with phase values calculated by `hexaSub.c` (the EPICS IOC that controls EQSANS choppers).

When a user requests a starting wavelength, hexaSub calculates the OGC (Opening Gap Center) phase for each chopper. These phases include hardware calibration offsets (~29000-30000 µs) that account for encoder alignment, cable delays, and other instrument-specific factors.

To use hexaSub phases in the simulator:
1. Select the appropriate frequency (30 Hz or 60 Hz)
2. Check the **hexaSub phases** checkbox
3. Enter the OGC phase values from hexaSub directly into the OGC fields
4. The simulator automatically applies the necessary corrections

The checkbox sets the mechanical offset for each chopper to:
- **Subtract** the hardware calibration offset (to recover physical timing)
- **Add** frame-skip alignment corrections (30 Hz mode only, to compensate for period wrapping)

**Example (30 Hz, 2.5 Å start wavelength, SDD=4m):**

| Chopper | hexaSub OGC (µs) | Mech Offset (µs) |
|---------|------------------|------------------|
| 1b | 33233.61 | -29908.92 |
| 2b | 33318.81 | -29610.80 |
| 3a | 921.45 | +3881.21 |
| 3b | 12454.81 | +4202.13 |

This produces two wavelength bands: 2.5–6.1 Å and 9.8–13.4 Å.

**Relationship to hexaSub.c:**

The `bl6chopper_src/hexaSub.c` file contains the EPICS subroutine that calculates chopper phases for a requested wavelength setting. The key function `calc6Phases()` determines the OGC timing for each chopper based on:
- Starting wavelength
- Detector distance (SDD)
- Sample-to-moderator distance
- Chopper speed (30 Hz or 60 Hz)

In 30 Hz frame-skip mode, hexaSub aligns different choppers to different source pulses:
- **Band 1** (current pulse): 3b opens at λ₁, 2b closes at λ₂
- **Band 2** (previous pulse): 1b opens at λ₃, 3a closes at λ₄

The simulator reproduces these bands by ray-tracing neutrons through all choppers, allowing verification that hexaSub-calculated phases produce the expected wavelength bands.

---

## Typical Workflow

```bash
# 1. Start the interactive edge finder
python find_edges_ui.py

# 2. In the Phase Calculator window:
#    - Enter IPTS and Run number
#    - Click "Load" to fetch spectrum from NeXus
#    - Click on plot to mark edge positions
#    - Press 'f' to fit edges
#    - Use 'l'/'r' keys to capture edge positions for phase calculation

# 3. (Optional) Compare with simulation
python onechopper_diagram.py --chopper 1b --offset 1000 --edges 5000,10000
```

## Edge Detection Methods

| Tool | Method | Output |
|------|--------|--------|
| find_edges_ui.py | Interactive erf fitting | Position, width, uncertainty, boundaries |
| find_edges.py | Command-line erf fitting | Position, width, uncertainty, boundaries |
| onechopper_diagram.py | Derivative maximum | Position only |

For precise edge analysis on real data, use `find_edges_ui.py` (interactive) or `find_edges.py` (batch). The `onechopper_diagram.py` edge detection is for quick visualization of simulated data.