# Phase Delay Test Proposal for New Chopper Series

## Background

The new series of EQSANS choppers have been found to have phase offsets all close to **14650 µs**, which differs from the old phase offsets currently hardcoded in `calcPhases.py`:

| Chopper | Old Phase Offset (µs) | New Phase Offset (µs) |
|---------|----------------------|----------------------|
| 1a/1b   | 9507                 | 14650                |
| 2a/2b   | 9471                 | 14650                |
| 3a      | 9829.7               | 14650                |
| 3b      | 9584.3               | 14650                |

## Objective

Verify that the new phase offsets are reasonable by reproducing a known wavelength configuration (2.5 Å) using calculated phase delay values.

## Theory

The relationship between phase delay and phase offset is:

```
phase_delay = calculated_phase_from_physics + phase_offset
```

Where `calculated_phase_from_physics` depends on:
- Wavelength requested
- Chopper location
- Chopper opening angle
- Detector distance

To reproduce the same physical timing with new phase offsets:

```
new_phase_delay = old_phase_delay - old_phase_offset + new_phase_offset
```

(with modulo applied to keep within frame width of 16666.67 µs at 60 Hz)

## Test Configuration

- **Wavelength**: 2.5 Å
- **Chopper Speed**: 60 Hz
- **Sample-to-Detector Distance (SDD)**: 4.0 m
- **Sample-to-Moderator Distance**: 14.122 m (default)
- **Choppers Used**: 1a, 2a, 3a, 3b (not using 1b, 2b)

## Calculated Phase Delays

### Old System (for reference)

Using the old phase offsets in `calcPhases.py`:

| Chopper | Phase Delay (µs) |
|---------|-----------------|
| 1a      | 15351.3         |
| 2a      | 1900.0          |
| 3a      | 2574.7          |
| 3b      | 4249.8          |

### New System (to test)

**Phase delays to set with new phase offset = 14650 µs:**

| Chopper | Phase Delay (µs) |
|---------|-----------------|
| **1a**  | **3827.6**      |
| **2a**  | **7079.0**      |
| **3a**  | **7395.0**      |
| **3b**  | **9315.5**      |

## Verification Calculation

For each chopper, the conversion was calculated as follows:

### Chopper 1a
- Old phase delay: 15351.3 µs (with old offset 9507)
- Calculated physics phase: 15351.3 - 9507 = 5844.3 µs
- New phase delay: 5844.3 + 14650 = 20494.3 µs
- After modulo (frame = 16666.7 µs): **3827.6 µs**

### Chopper 2a
- Old phase delay: 1900.0 µs (with old offset 9471)
- Calculated physics phase: 1900.0 - 9471 = -7571.0 µs
- New phase delay: -7571.0 + 14650 = 7079.0 µs
- After modulo: **7079.0 µs**

### Chopper 3a
- Old phase delay: 2574.7 µs (with old offset 9829.7)
- Calculated physics phase: 2574.7 - 9829.7 = -7255.0 µs
- New phase delay: -7255.0 + 14650 = 7395.0 µs
- After modulo: **7395.0 µs**

### Chopper 3b
- Old phase delay: 4249.8 µs (with old offset 9584.3)
- Calculated physics phase: 4249.8 - 9584.3 = -5334.5 µs
- New phase delay: -5334.5 + 14650 = 9315.5 µs
- After modulo: **9315.5 µs**

## Sanity Check

The offset differences are consistent across all choppers:

| Chopper | Offset Change (µs) |
|---------|-------------------|
| 1a      | +5143             |
| 2a      | +5179             |
| 3a      | +4820.3           |
| 3b      | +5065.7           |

All changes are in a similar range (~5000 µs), which is consistent with a systematic offset change in the new chopper series.

## Expected Result

When the new phase delay values are applied to choppers 1a, 2a, 3a, 3b with the new phase offset of 14650 µs, the instrument should produce the same wavelength band as the old system configured for 2.5 Å at 4.0 m SDD.

## Phase Delays for Other SDD Values

For reference, here are the calculated phase delays for other common detector distances:

| SDD (m) | 1a (µs) | 2a (µs) | 3a (µs) | 3b (µs) |
|---------|---------|---------|---------|---------|
| 1.3     | 4745.4  | 7079.0  | 8924.1  | 9315.5  |
| 2.5     | 4300.7  | 7079.0  | 8183.2  | 9315.5  |
| 4.0     | 3827.6  | 7079.0  | 7395.0  | 9315.5  |
| 8.0     | 2879.7  | 7079.0  | 5815.7  | 9315.5  |

---

*Generated: 2026-03-06*
*Source: calcPhases.py analysis*
