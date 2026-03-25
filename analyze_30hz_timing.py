#!/usr/bin/env python
"""
Analyze 30Hz timing to understand the expected behavior.

At 30Hz mode:
- Source pulses at 60Hz (16666.67 µs period)
- Choppers rotate at 30Hz (33333.33 µs period)
- Each chopper opening sees TWO source pulses

The question: what is the correct OGC timing that the simulator expects?
"""

import numpy as np

H_OVER_MN = 3956.0
SOURCE_PERIOD_US = 1e6 / 60.0  # 16666.67 µs
CHOPPER_PERIOD_30HZ_US = 1e6 / 30.0  # 33333.33 µs

chopper_location_mm = {"1a": 5657.3247, "2a": 7760.1247, "3a": 9497.8, "3b": 9507.8}
chopper_location_m = {k: v/1000 for k, v in chopper_location_mm.items()}
chopper_opening_deg = {"1a": 129.605, "2a": 179.989, "3a": 230.010, "3b": 230.007}

def tof_us(wavelength_A, distance_m):
    """Time of flight in microseconds"""
    return distance_m / (H_OVER_MN / wavelength_A) * 1e6

def main():
    start_wl = 2.5
    sdd_m = 4.0
    stm_m = 14.122
    
    det_dist = sdd_m
    detector_location_m = stm_m + np.sqrt(det_dist**2 + 0.707107**2)
    detector_location_mm = detector_location_m * 1000
    
    bandwidth_at_60Hz = 3.956e6 / detector_location_mm / 60.0
    
    wl = {
        1: start_wl,
        2: start_wl + bandwidth_at_60Hz,
        3: start_wl + 2*bandwidth_at_60Hz,
        4: start_wl + 3*bandwidth_at_60Hz
    }
    
    print("="*80)
    print("30Hz MODE TIMING ANALYSIS")
    print("="*80)
    print(f"\nWavelengths: wl[1]={wl[1]:.2f}, wl[2]={wl[2]:.2f}, wl[3]={wl[3]:.2f}, wl[4]={wl[4]:.2f}")
    print(f"Source period: {SOURCE_PERIOD_US:.2f} µs")
    print(f"Chopper period (30Hz): {CHOPPER_PERIOD_30HZ_US:.2f} µs")
    
    print("\n" + "-"*80)
    print("TOF to each chopper for target wavelengths:")
    print("-"*80)
    
    for name in ["1a", "2a", "3a", "3b"]:
        print(f"\n{name} at {chopper_location_m[name]:.4f} m:")
        for w_idx in [1, 2, 3, 4]:
            tof = tof_us(wl[w_idx], chopper_location_m[name])
            n_frames = tof / SOURCE_PERIOD_US
            print(f"  wl[{w_idx}]={wl[w_idx]:.2f}Å: TOF = {tof:.1f} µs ({n_frames:.2f} source frames)")
    
    print("\n" + "="*80)
    print("EXPECTED ALIGNMENT (per hexaSub.c 30Hz logic):")
    print("="*80)
    print("""
1a: Opening edge aligned to wl[3], from PREVIOUS pulse (subtract 16666.67 µs)
2a: Closing edge aligned to wl[2]
3a: Closing edge aligned to wl[4], from PREVIOUS pulse (subtract 16666.67 µs)
3b: Opening edge aligned to wl[1]
""")
    
    half_angle_to_sec_30 = 1.0 / 360.0 / 30 / 2.0
    
    print("\n" + "-"*80)
    print("Calculating CENTER timing (what hexaSub calculates before adding offset):")
    print("-"*80)
    
    tof_1a_wl3 = tof_us(wl[3], chopper_location_m["1a"])
    if tof_1a_wl3 > SOURCE_PERIOD_US:
        center_1a = tof_1a_wl3 - SOURCE_PERIOD_US
    else:
        center_1a = tof_1a_wl3
    center_1a += chopper_opening_deg["1a"] * half_angle_to_sec_30 * 1e6
    print(f"1a: TOF(wl[3])={tof_1a_wl3:.1f}µs, center = {center_1a:.1f} µs")
    
    tof_2a_wl2 = tof_us(wl[2], chopper_location_m["2a"])
    center_2a = tof_2a_wl2 - chopper_opening_deg["2a"] * half_angle_to_sec_30 * 1e6
    print(f"2a: TOF(wl[2])={tof_2a_wl2:.1f}µs, center = {center_2a:.1f} µs")
    
    tof_3a_wl4 = tof_us(wl[4], chopper_location_m["3a"])
    center_3a = tof_3a_wl4 - SOURCE_PERIOD_US - chopper_opening_deg["3a"] * half_angle_to_sec_30 * 1e6
    print(f"3a: TOF(wl[4])={tof_3a_wl4:.1f}µs, center = {center_3a:.1f} µs")
    
    tof_3b_wl1 = tof_us(wl[1], chopper_location_m["3b"])
    center_3b = tof_3b_wl1 + chopper_opening_deg["3b"] * half_angle_to_sec_30 * 1e6
    print(f"3b: TOF(wl[1])={tof_3b_wl1:.1f}µs, center = {center_3b:.1f} µs")
    
    print("\n" + "="*80)
    print("KEY INSIGHT: THE DIFFERENT PULSE ALIGNMENT")
    print("="*80)
    print("""
In 30Hz mode:
- 1a aligns its opening to wl[3] neutrons from the PREVIOUS source pulse
- 2a aligns its closing to wl[2] neutrons from the CURRENT source pulse  
- 3a aligns its closing to wl[4] neutrons from the PREVIOUS source pulse
- 3b aligns its opening to wl[1] neutrons from the CURRENT source pulse

This means choppers 1a and 3a operate on pulse N-1, while 2a and 3b operate on pulse N.

For a neutron to pass ALL choppers, it must:
- Be from a source pulse that satisfies all timing conditions
- The frame-skipping logic creates a wavelength band where neutrons from TWO 
  different source pulses can arrive at the detector in the same TOF window

The simulator needs to correctly handle this multi-pulse scenario!
""")
    
    print("\n" + "="*80)
    print("WHAT THE SIMULATOR ACTUALLY DOES:")
    print("="*80)
    print("""
The simulator:
1. Iterates through source pulses (at 60Hz)
2. For each pulse, checks if neutrons pass ALL choppers
3. Uses chopper_period (30Hz) for modulo timing

The key function:
  rel = (t_arrival - left_edge_s) % chopper_period
  passes = rel < opening_s

This checks if the neutron arrives during the chopper opening window.

The problem: If the OGC values are wrong, the left_edge times will be wrong,
and neutrons won't pass all choppers from the same source pulse.
""")

    print("\n" + "="*80)
    print("TESTING: What happens for wl=4.0 Å neutron from pulse 0?")
    print("="*80)
    
    test_wl = 4.0
    t_src = 0.0  # pulse 0
    
    period_30_s = CHOPPER_PERIOD_30HZ_US / 1e6
    
    for name in ["1a", "2a", "3a", "3b"]:
        dist = chopper_location_m[name]
        opening_deg = chopper_opening_deg[name]
        
        tof = dist / (H_OVER_MN / test_wl) * 1e6
        t_arrival = t_src + tof
        
        ogc_center_us = eval(f"center_{name}")
        left_edge_us = ogc_center_us - (opening_deg / 360.0) * CHOPPER_PERIOD_30HZ_US / 2.0
        opening_us = (opening_deg / 360.0) * CHOPPER_PERIOD_30HZ_US
        
        rel = (t_arrival - left_edge_us) % CHOPPER_PERIOD_30HZ_US
        passes = rel < opening_us
        
        print(f"{name}: t_arr={t_arrival:.1f}µs, left_edge={left_edge_us:.1f}µs, "
              f"rel={rel:.1f}µs, opening={opening_us:.1f}µs, PASS={passes}")
    
    print("\n" + "="*80)
    print("TESTING: What happens for wl=4.0 Å neutron from pulse -1?")
    print("="*80)
    
    t_src = -SOURCE_PERIOD_US  # pulse -1
    
    for name in ["1a", "2a", "3a", "3b"]:
        dist = chopper_location_m[name]
        opening_deg = chopper_opening_deg[name]
        
        tof = dist / (H_OVER_MN / test_wl) * 1e6
        t_arrival = t_src + tof
        
        ogc_center_us = eval(f"center_{name}")
        left_edge_us = ogc_center_us - (opening_deg / 360.0) * CHOPPER_PERIOD_30HZ_US / 2.0
        opening_us = (opening_deg / 360.0) * CHOPPER_PERIOD_30HZ_US
        
        rel = (t_arrival - left_edge_us) % CHOPPER_PERIOD_30HZ_US
        passes = rel < opening_us
        
        print(f"{name}: t_arr={t_arrival:.1f}µs, left_edge={left_edge_us:.1f}µs, "
              f"rel={rel:.1f}µs, opening={opening_us:.1f}µs, PASS={passes}")


if __name__ == "__main__":
    main()
