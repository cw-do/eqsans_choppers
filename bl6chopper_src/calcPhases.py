# optional distances in mm
def calcChopperByStartingWavelength(start_wavelenth, chopper_speed_in_Hz, sample_to_detector_in_mm=None,sample_to_moderator_in_mm=None):
	"""
		calculate chopper phases using chopper_speed_in_Hz , sample_to_detector_in_mm,sample_to_moderator_in_mm,
		and call setChopperSpeedsAndPhases(...)
		if sample_to_detector_in_mm is not given, or <=0, detector location (z) is read in
		if sample_to_moderator_in_mm is not given, or <=0, a default value is given (~13964mm)

	"""
        eqsans_verbose_level = 0
	#print_self()
	
	
	#if checkHelperApps() <0 :
	#	return (0,0,0,0)
	
	#if eqsans_verbose_level : 
	#	print_status('\nStarting wavelength = %g'% start_wavelenth)
	
	#if sample_to_moderator_in_mm==None or sample_to_moderator_in_mm<= 0:
	#	try:	sample_to_moderator_in_mm=sampToMod.getvalue()
	#	except : sample_to_moderator_in_mm = default_sample_to_moderator
		
	#	if sample_to_moderator_in_mm<=10000. or sample_to_moderator_in_mm>=24000:
	#		sample_to_moderator_in_mm=default_sample_to_moderator 	# mili meters

	#if sample_to_detector_in_mm ==None or sample_to_detector_in_mm <= 0:
	#	sample_to_detector_in_mm= detectorZ.getvalue()

	detector_location=sample_to_detector_in_mm+sample_to_moderator_in_mm

	if eqsans_verbose_level : 
		print(( 'Detector to sample [mm] =%g, \tto moderator [mm]) = %g' %( sample_to_detector_in_mm,detector_location)))

	chopper1_location=5700 		# in mili meters
	chopper2_location=7800
	chopper3_location=9497
	chopper4_location=9507
	chopper1_opening=129.605	# angle in degree
	chopper2_opening=179.989
	chopper3_opening=230.010
	chopper4_opening=230.007

	pulse_width = 0
	#pulse_width = 20. * 1e-6		# in sec per Angstrom
	beam_crosssection=0	# 40 mm
	chopper_disc_diameter = 578.5		#mm, disc diameter is ~635mm. disc center to beam center ~578.5/2

	bandwidth_at_60Hz=3.956e6/detector_location/60.	# 60Hz bandwidth
	wl1=start_wavelenth
	wl2=start_wavelenth+bandwidth_at_60Hz
	
	if chopper_speed_in_Hz == 30 :		# we assume frame skipping mode for 30Hz. Pulse rejection is not considered.
		detector_z_tol=5
		if sample_to_detector_in_mm > 5000 + detector_z_tol :
			print(( 'Frame Skipping operation does not work for SDD > 5m!\n',
							'Returning without any action'))
			return (0,0,0,0)

		phase1_offset=19024.3 			# experimentally determined value in micro sec. needs to be added to calc. value.
		phase2_offset=18820
		phase3_offset=19714
		phase4_offset=19361.4
		frame_width=1e6/chopper_speed_in_Hz
		beam_crosssection_adjust = beam_crosssection/ (chopper_disc_diameter * 3.1415926) /chopper_speed_in_Hz /2	 # delay the opening by half the beam cross section
																													# or close it earlier by half the beam cross section
		half_angle_to_sec= 1./ 360. /chopper_speed_in_Hz /2.

		wl3=wl2+bandwidth_at_60Hz						#second frame
		wl4=wl3+bandwidth_at_60Hz
		phase1 = chopper1_location/3.956e6*wl3 - 1./60.		# chopper 1 opening edge aligned to wl3, now in sec, this come from previous pulse
		phase1 +=  beam_crosssection_adjust				# delay the opening by half the beam cross section
		phase1 += chopper1_opening * half_angle_to_sec	# move to center
		phase1 = 1e6 * phase1 + phase1_offset			# add adjust, now in micro sec
		phase1 %= frame_width

		phase2 = chopper2_location/3.956e6*wl2			# chopper 2 closing edge aligned to wl2,now in sec
		phase2 -= beam_crosssection_adjust				# close the choppler by half the beam cross section earlier
		phase2 -= chopper2_opening * half_angle_to_sec	# move to center
		phase2 = 1e6 * phase2 + phase2_offset			# adjust, now in micro sec
		phase2 %= frame_width

		phase3 = chopper3_location/3.956e6*wl4 - 1./60.		# chopper 3 closing edge aligned to wl4
		phase3 -=  beam_crosssection_adjust				# close the choppler by half the beam cross section earlier
		phase3 -= chopper3_opening * half_angle_to_sec	# move to center
		phase3 = 1e6 * phase3 + phase3_offset			# adjust
		phase3 %= frame_width

		phase4 = chopper4_location/3.956e6*wl1			# chopper 4 opening edge aligned to wl1,now in sec
		phase4 += beam_crosssection_adjust				# delay the opening by half the beam cross section
		phase4 += pulse_width * wl1	/detector_location * chopper4_location			# only T4 need pulse width adjust
		phase4 += chopper4_opening * half_angle_to_sec	# move to center
		phase4 = 1e6 * phase4 + phase4_offset			# adjust, now in micro sec
		phase4 %= frame_width

		if eqsans_verbose_level > 1 :
			print('Beam cross section adjust to choppers: ')
			print('	T1: opens later    by ', int(beam_crosssection_adjust	* 1e6+0.5),' micro sec')
			print('	T2: closes earlier by ', int(beam_crosssection_adjust	* 1e6+0.5),' micro sec')
			print('	T3: closes earlier by ', int(beam_crosssection_adjust	* 1e6+0.5),' micro sec')
			print('	T4: opens later    by ', int(beam_crosssection_adjust	* 1e6+0.5),' micro sec')
			print()
			print('Pulse width adjust: T4 open later by ', int(pulse_width * wl1 /detector_location * chopper4_location*1e6+0.5)	,' micro sec')
			print()
		
		
		#return setChopperSpeedsAndPhases(chopper_speed_in_Hz, phase1, phase2, phase3,phase4)
                print(chopper_speed_in_Hz, start_wavelenth, sample_to_detector_in_mm, phase1, phase2, phase3,phase4)
		return (chopper_speed_in_Hz, phase1, phase2, phase3,phase4)

	elif chopper_speed_in_Hz == 60 :				# this is the normal op.
		phase1_offset=9507					# experimentally determined value in micro sec. needs to be added to calc. value.
		phase2_offset=9471
		phase3_offset=9829.7
		phase4_offset=9584.3
		frame_width=1e6/ chopper_speed_in_Hz		# in micro sec
		half_angle_to_sec= 1./ 360. /chopper_speed_in_Hz /2.
		beam_crosssection_adjust = beam_crosssection/ (chopper_disc_diameter * 3.1415926) /chopper_speed_in_Hz /2	 # delay the opening by half the beam cross section
																												# or close it earlier by half the beam cross section
		if wl1 > 13 :	# we align the chopper differently between wl1>13 and wl1<=13 to stop leaks.
			phase1 = chopper1_location/3.956e6*wl1	 		# chopper 1 opening edge aligned to wl1, now in sec, T1 does not need adjust for 60Hz
			phase1 += chopper1_opening * half_angle_to_sec		# move to center
			phase2 = chopper2_location/3.956e6*wl2			# chopper 2 closing edge aligned to wl2,now in sec, T2 does not need adjust for 60Hz
			phase2 -= chopper2_opening * half_angle_to_sec		# move to center
		else:
			phase1 = chopper1_location/3.956e6*wl2	 		# chopper 1 closing edge aligned to wl2, now in sec, T1 does not need adjust for 60Hz
			phase1 -= chopper1_opening * half_angle_to_sec		# move to center
			phase2 = chopper2_location/3.956e6*wl1			# chopper 2 opening edge aligned to wl1,now in sec, T2 does not need adjust for 60Hz
			phase2 += chopper2_opening * half_angle_to_sec		# move to center
		phase1 = 1e6 * phase1 + phase1_offset			# add adjust, now in micro sec
		phase1 %= frame_width
		phase2 = 1e6 * phase2 + phase2_offset			# adjust, now in micro sec
		phase2 %= frame_width

		phase3 = chopper3_location/3.956e6* wl2 			# chopper 3 closing edge aligned to wl2
		phase3 -= beam_crosssection_adjust				# close the choppler by half the beam cross section earlier
		phase3 -= chopper3_opening * half_angle_to_sec	# move to center
		phase3 = 1e6 * phase3 + phase3_offset			# adjust
		phase3 %= frame_width
		
		#print chopper3_location,chopper3_opening,phase3_offset,phase3
		
		phase4 = chopper4_location/3.956e6*wl1			# chopper 4 opening edge aligned to wl1,now in sec
		phase4 += beam_crosssection_adjust				# delay the opening by half the beam cross section
		#print phase4
		phase4 += pulse_width * wl1	/detector_location * chopper4_location			# only T4 need pulse width adjust
		#print phase4
		phase4 += chopper4_opening * half_angle_to_sec	# move to center
		phase4 = 1e6 * phase4 + phase4_offset			# adjust, now in micro sec
		phase4 %= frame_width

		if detector_location < 360/chopper1_opening*chopper1_location : # T1 is not opened enough
			x1=3.956*(phase1 - phase1_offset - 1e6*chopper1_opening * half_angle_to_sec)/chopper1_location
			x1 -= wl1
			#print wl1,x1,phase1
			if x1>0 and x1<.2: # shouldn't be too big	
				phase1 -= x1*chopper1_location/3.956
			#print phase1
			#x2=3.956*(phase2 - phase2_offset - 1e6*chopper2_opening * half_angle_to_sec)/chopper2_location
			#x3=3.956*(phase3 - phase3_offset - 1e6*chopper3_opening * half_angle_to_sec)/chopper3_location
			#x4=3.956*(phase4 - phase4_offset - 1e6*chopper4_opening * half_angle_to_sec)/chopper4_location
			#print x2,x3,x4
			
		if eqsans_verbose_level >1 :
			print('Beam cross section adjust to choppers: ')
			print('	T3: closes earlier by ', int(beam_crosssection_adjust	* 1e6+0.5),' micro sec')
			print('	T4: opens later    by ', int(beam_crosssection_adjust	* 1e6+0.5),' micro sec')
			print()
			print('Pulse width adjust: T4 opens later by ', int(pulse_width * wl1/detector_location * chopper4_location	* 1e6+0.5)	,' micro sec')
			print()
		#return setChopperSpeedsAndPhases(chopper_speed_in_Hz, phase1, phase2, phase3,phase4)
                print(chopper_speed_in_Hz, start_wavelenth, sample_to_detector_in_mm,phase1, phase2, phase3,phase4)
		return (chopper_speed_in_Hz, phase1, phase2, phase3,phase4)
	else :
		print_status( 'only 30Hz and 60Hz operations are allowed')
		return (0,0,0,0)

#def calcChopperByStartingWavelength(start_wavelenth, chopper_speed_in_Hz, sample_to_detector_in_mm=None,sample_to_moderator_in_mm=None):

#calcChopperByStartingWavelength(2.5, 60, 1300, 14122)
#calcChopperByStartingWavelength(2.5, 30, 4000, 14122)
#calcChopperByStartingWavelength(4.0, 30, 4000, 14122)
#calcChopperByStartingWavelength(2.0, 60, 4000, 14122)
#calcChopperByStartingWavelength(2.0, 60, 8000, 14122)

print('speed wavelength detdist, phases')

calcChopperByStartingWavelength(2.0, 60, 1300, 14122)
calcChopperByStartingWavelength(4.0, 60, 1300, 14122)
calcChopperByStartingWavelength(6.0, 60, 1300, 14122)
calcChopperByStartingWavelength(8.0, 60, 1300, 14122)
calcChopperByStartingWavelength(2.0, 60, 2500, 14122)
calcChopperByStartingWavelength(4.0, 60, 2500, 14122)
calcChopperByStartingWavelength(6.0, 60, 2500, 14122)
calcChopperByStartingWavelength(8.0, 60, 2500, 14122)
calcChopperByStartingWavelength(2.0, 60, 4000, 14122)
calcChopperByStartingWavelength(4.0, 60, 4000, 14122)
calcChopperByStartingWavelength(6.0, 60, 4000, 14122)
calcChopperByStartingWavelength(8.0, 60, 4000, 14122)
calcChopperByStartingWavelength(2.0, 60, 8000, 14122)
calcChopperByStartingWavelength(4.0, 60, 8000, 14122)
calcChopperByStartingWavelength(6.0, 60, 8000, 14122)
calcChopperByStartingWavelength(8.0, 60, 8000, 14122)

calcChopperByStartingWavelength(2.0, 30, 4000, 14122)
calcChopperByStartingWavelength(3.0, 30, 4000, 14122)
calcChopperByStartingWavelength(4.0, 30, 4000, 14122)
calcChopperByStartingWavelength(6.0, 30, 4000, 14122)
calcChopperByStartingWavelength(2.0, 30, 2500, 14122)
calcChopperByStartingWavelength(3.0, 30, 2500, 14122)
calcChopperByStartingWavelength(4.0, 30, 2500, 14122)
calcChopperByStartingWavelength(6.0, 30, 2500, 14122)

calcChopperByStartingWavelength(0.6, 60, 4000, 14122)
