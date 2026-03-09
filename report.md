# Phase Delay Reference Point Analysis: bl6-SkfChopper Code

## Executive Summary

**The phase delay (called "TotalDelay" in the EPICS system) output by the old `calcPhases.py` / `calc6Phases()` code references the CENTER OF THE CHOPPER OPENING (midpoint of the open gap), not a blade edge.** The code explicitly calculates the time when a specific blade edge (opening or closing) should align with a specific neutron wavelength, then shifts the result by `chopper_opening * half_angle_to_sec` to **"move to center"** before adding the experimentally-determined offset constant. This "move to center" step is the key evidence.

---

## 1. Code Architecture Overview

The chopper phase calculation lives in three related implementations:

| File | Language | Purpose |
|------|----------|---------|
| `calcPhases.py` | Python | Original 4-chopper calculation (standalone, for testing) |
| `calcBandwidth.py` | Python | Reverse calculation: phase values back to wavelength band |
| `hexaSub.c` (`calc6Phases`) | C | Production EPICS subroutine, 6-chopper version |
| `hexaSub.c` (`calc6Wavelengths`) | C | Production EPICS subroutine, reverse bandwidth calc |

All three share identical physics and logic. The C code (`hexaSub.c`) is the live production code called by EPICS `aSub` records, while the Python files are development/testing scripts.

### Chopper Mapping (Old 4-blade to New 6-blade)

| Old Index | Old Name | New Index | New Name | Location (mm) | Opening Angle |
|-----------|----------|-----------|----------|---------------|---------------|
| 1 | Chopper 1 | 1 | 1a | 5700 | 129.605 deg |
| - | - | 5 | 1b | 5700 | 129.605 deg |
| 2 | Chopper 2 | 2 | 2a | 7800 | 179.989 deg |
| - | - | 6 | 2b | 7800 | 179.989 deg |
| 3 | Chopper 3 | 3 | 3a | 9497 | 230.010 deg |
| 4 | Chopper 4 | 4 | 3b | 9507 | 230.007 deg |

In the 6-blade C code, choppers 5 and 6 (1b, 2b) are computed identically to choppers 1 and 2 (1a, 2a) respectively, using the same distances and angles. Old choppers 3 and 4 map to new 3a and 3b.

---

## 2. Detailed Phase Calculation Logic

### 2.1 The Fundamental Pattern

Every chopper phase calculation in the code follows the same 4-step pattern:

```
Step 1: Calculate the time a specific wavelength neutron arrives at the chopper
Step 2: Apply beam-crosssection adjustment (currently zero)
Step 3: Apply "move to center" shift (+/- chopper_opening * half_angle_to_sec)
Step 4: Convert to microseconds and add experimentally-determined offset
```

The variable `half_angle_to_sec` is defined as:

```python
half_angle_to_sec = 1.0 / 360.0 / chopper_speed_in_Hz / 2.0
```

This converts half of a chopper opening angle (in degrees) into a time duration (in seconds). The factor `chopper_opening * half_angle_to_sec` therefore represents **half the opening time** of the chopper gap.

### 2.2 The Critical Step 3: "Move to Center"

This is the key operation that reveals the reference point. Let us trace each chopper:

#### 60 Hz Mode, `wl1 <= 13` (normal operation):

**Chopper 1 (T1) — closing edge aligned to wl2:**
```python
phase1 = chopper1_location/3.956e6 * wl2         # closing edge time for wl2
phase1 -= chopper1_opening * half_angle_to_sec    # SUBTRACT half-opening -> move to center
```
The code starts at the closing edge (when the blade shuts) and SUBTRACTS half the opening time. This moves the reference point backward in time from the closing edge to the center of the gap.

**Chopper 2 (T2) — opening edge aligned to wl1:**
```python
phase2 = chopper2_location/3.956e6 * wl1         # opening edge time for wl1
phase2 += chopper2_opening * half_angle_to_sec    # ADD half-opening -> move to center
```
The code starts at the opening edge (when the gap starts) and ADDS half the opening time. This moves the reference point forward in time from the opening edge to the center of the gap.

**Chopper 3 (T3) — closing edge aligned to wl2:**
```python
phase3 = chopper3_location/3.956e6 * wl2         # closing edge time for wl2
phase3 -= chopper3_opening * half_angle_to_sec    # SUBTRACT half-opening -> move to center
```
Same pattern as T1: closing edge minus half-opening = center.

**Chopper 4 (T4) — opening edge aligned to wl1:**
```python
phase4 = chopper4_location/3.956e6 * wl1         # opening edge time for wl1
phase4 += chopper4_opening * half_angle_to_sec    # ADD half-opening -> move to center
```
Same pattern as T2: opening edge plus half-opening = center.

#### 60 Hz Mode, `wl1 > 13` (long wavelength):

The alignment swaps:
- T1 **opening edge** aligned to wl1, then `+= half_angle` -> center
- T2 **closing edge** aligned to wl2, then `-= half_angle` -> center

Same center-seeking logic, just with swapped edge assignments.

#### 30 Hz Mode (Frame Skipping):

Identical pattern:
- T1: opening edge + half_angle -> center
- T2: closing edge - half_angle -> center
- T3: closing edge - half_angle -> center
- T4: opening edge + half_angle -> center

### 2.3 Direction Convention

The sign convention is always:
- **Opening edge + half_angle = center** (shift forward from where gap opens)
- **Closing edge - half_angle = center** (shift backward from where gap closes)

Both converge to the same point: the **midpoint of the opening gap**.

---

## 3. The Experimentally-Determined Offset Constants

After the "move to center" calculation, the code adds a constant offset:

```python
phase1 = 1e6 * phase1 + phase1_offset   # convert to microseconds, add offset
phase1 %= frame_width                     # wrap into frame
```

### 60 Hz Offsets:

| Chopper | Offset (us) |
|---------|-------------|
| 1 (1a) | 9507 |
| 2 (2a) | 9471 |
| 3 (3a) | 9829.7 |
| 4 (3b) | 9584.3 |
| 5 (1b) | 9507 |
| 6 (2b) | 9471 |

### 30 Hz Offsets:

| Chopper | Offset (us) |
|---------|-------------|
| 1 (1a) | 19024.3 |
| 2 (2a) | 18820 |
| 3 (3a) | 19714 |
| 4 (3b) | 19361.4 |
| 5 (1b) | 19024.3 |
| 6 (2b) | 18820 (Note: typo in C code shows 1882, likely should be 18820) |

These offsets absorb the difference between the calculated "ideal" phase (referenced to T0 of the SNS source pulse relative to the center of the chopper gap) and the actual hardware timing. They are the calibration constants that account for:

1. The physical angular position of the gap center relative to the hardware's zero reference (pickup sensor)
2. Electronic and mechanical delays in the SKF controller
3. Cable/signal propagation times

---

## 4. The Reverse Calculation Confirms: Center Reference

In `calcBandwidth.py` and `calc6Wavelengths()`, the reverse calculation goes from phase values back to wavelengths:

```python
chopper_actual_phase[i] = chopper_set_phase[i] - CHOPPER_PHASE_OFFSET[i + m*4]

x1 = chopper_actual_phase[i] - (tmp_frame_width * 0.5 * CHOPPER_ANGLE[i] / 360.0)  # opening edge
x2 = chopper_actual_phase[i] + (tmp_frame_width * 0.5 * CHOPPER_ANGLE[i] / 360.0)  # closing edge
```

This explicitly shows:
- `chopper_actual_phase[i]` (after removing the offset) represents the **center** of the opening
- Subtracting `half_angle_time` gives the **opening edge** (x1)
- Adding `half_angle_time` gives the **closing edge** (x2)

The comments `/* opening edge */` and `/* closing edge */` in the C code (`hexaSub.c`, lines 79 and 81) make this unambiguous.

---

## 5. Data Flow: From Calculation to Hardware

The EPICS database (`hexaDskScanAssist.db`) shows the complete data flow:

```
InitWvlenSet (start wavelength) 
    + ProcDistSet (detector distance)
    + SpeedReq (chopper speed)
    + DistModSamp (moderator-to-sample distance)
         |
         v
    calc6Phases (aSub record)
         |
         v
    Skf1:TotalDelaySet ... Skf6:TotalDelaySet
         |
         v
    SKF chopper controller hardware (via Modbus)
```

The output PVs are named `TotalDelaySet`, and the choppers operate in `totalDelay` mode (PhaseEntryMode = 3). The "TotalDelay" is the phase value in microseconds, referenced to the center of the gap, that gets sent to each SKF controller.

The IOC boot scripts (e.g., `st-6.cmd`) show each chopper is loaded with:
```
OfsTime=19361.4, OfsAngle=0.0
```
The `OfsTime` matches the 30Hz offset for that particular chopper, suggesting the SKF controller firmware also uses a center-of-gap convention internally (or at least that the offset constant absorbs any difference).

---

## 6. Physical Interpretation: What "Center of Gap" Means

On the physical chopper disc:

```
    Blade (absorbing)
    ==================
    |                |  <- Closing edge (trailing edge in rotation direction)
    |                |
    |   OPEN GAP     |  <- Center of gap = REFERENCE POINT for phase delay
    |                |
    |                |  <- Opening edge (leading edge in rotation direction)
    ==================
    Blade (absorbing)
```

The phase delay value tells the controller: "At time T (microseconds after T0), the **center of the open gap** should be at the beam position."

When the code says "chopper 1 opening edge aligned to wl2, then move to center":
1. It computes when wl2 neutrons arrive at the chopper
2. At that moment, the closing edge should be at beam position
3. It then shifts by half the gap to get the center timing
4. This center timing is what gets sent to the controller

---

## 7. Implications for New 6-Blade System

To use this old code with the new chopper discs (1a, 1b, 2a, 2b, 3a, 3b):

1. **You need to know the angular position of the center of each gap** on the new discs, not just the closing edges.

2. **If you know the closing edge positions** from experiment, you can derive the center:
   - Center position = Closing edge position - (opening_angle / 2)
   - Or equivalently: Center position = Opening edge position + (opening_angle / 2)

3. **The experimentally-determined offsets** (`phase_offset[]`) will need to be re-calibrated for the new discs. These offsets encode the relationship between the hardware's zero reference (pickup sensor position) and the center-of-gap convention.

4. **The C code (`hexaSub.c`) already supports 6 choppers.** Choppers 5 and 6 use the same logic as choppers 1 and 2. The arrays `CHOPPER_LOCATION`, `CHOPPER_ANGLE`, and `CHOPPER_PHASE_OFFSET` are already sized for 6 elements.

---

## 8. Cross-Reference with New Simulation Tool

The `onechopper_diagram.py` tool in the parent directory uses a different convention for its `--offset` parameter. From the README:

> **Note:** The `--offset` parameter defines the **left edge of the chopper opening gap** (i.e., when the gap starts to open, not the center of the opening).

This is **different** from the old `calcPhases.py` / `calc6Phases()` convention, which references the **center** of the gap. When comparing values between these tools, a conversion of `+/- half_opening_time` is needed.

Specifically, for `onechopper_diagram.py`:
```python
relative_arrival = (t_arrival - offset_s) % PERIOD
mask_pass = relative_arrival < opening_s
```

This means `offset_s` is the time when the gap **starts** opening (opening edge), and `opening_s` after that is when it closes. The center would be at `offset_s + opening_s/2`.

For the old `calcPhases.py` code, the calculated phase (before offset addition) represents the center, so:
```
old_code_center = new_tool_offset + opening_s / 2
```

---

## 9. Summary Table

| Aspect | Old Code (calcPhases / calc6Phases) | New Tool (onechopper_diagram.py) |
|--------|-------------------------------------|----------------------------------|
| **Reference point** | Center of gap | Opening (left) edge of gap |
| **Output unit** | Microseconds | Microseconds |
| **Includes hardware offset** | Yes (experimentally calibrated) | No (pure geometric) |
| **Comment in code** | "move to center" | "left edge of the chopper opening gap" |

## 10. Conclusion

**The phase delay in the old bl6-SkfChopper code references the CENTER (midpoint) of the chopper disc's open gap.** This is proven by the consistent `+/- chopper_opening * half_angle_to_sec` operation annotated "move to center" applied in every phase calculation, and confirmed by the reverse calculation in `calcBandwidth.py` / `calc6Wavelengths()` which derives opening and closing edges symmetrically from the actual phase value. The experimentally-determined offset constants then translate this center-of-gap timing into the hardware-specific delay value sent to the SKF controllers.
