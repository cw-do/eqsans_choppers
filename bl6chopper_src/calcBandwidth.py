def calcBandWidth(chopper__speed1__value,chopper__phases1__value,chopper__phases2__value,chopper__phases3__value,chopper__phases4__value):

        print(chopper__speed1__value,chopper__phases1__value,chopper__phases2__value,chopper__phases3__value,chopper__phases4__value)

	CHOPPER_PHASE_OFFSET=[9507,9471,9829.7,9584.3,19024.3,18820,19714,19361.4]

	CHOPPER_ANGLE=[129.605,179.989,230.010,230.007]

	CHOPPER_LOCATION=[5700.,7800.,9497.,9507.]

	chopper_wl_1= [0,0,0,0]

	chopper_srcpulse_wl_1= [0,0,0,0]

	chopper_wl_2= [0,0,0,0]

	#chopper_set_phase = [0,0,0,0]

	chopper_actual_phase= [0,0,0,0]

	tof_frame_width = 1e6/60.

	tmp_frame_width = tof_frame_width

	frame_wl_1=0

	frame_wl_2=0

	frameskip_wl_1=0

	frameskip_wl_2=0

	pulse_width=0	# micro sec /A

	

	#chopper__speed1__value=30

	#chopper__phases1__value = 15388.81443

	#chopper__phases2__value = 16264.9408

	#chopper__phases3__value = 1183.659938

	#chopper__phases4__value = 3048.239515

	

	chopper_set_phase = [chopper__phases1__value,chopper__phases2__value,chopper__phases3__value,chopper__phases4__value]



	chopper_speed_in_Hz=int(chopper__speed1__value+0.5)

	if  not( chopper_speed_in_Hz == 30 or  chopper_speed_in_Hz == 60) :

		return (0,0,0,0)

	

	m=0

	if chopper_speed_in_Hz==30 :

		m=1

		tmp_frame_width = tmp_frame_width *2

	chopper_frameskip_wl_1=[0,0,0,0]

	chopper_frameskip_wl_2=[0,0,0,0]

	chopper_frameskip_srcpulse_wl_1=[0,0,0,0]	

	chopper_frameskip_srcpulse_wl_2=[0,0,0,0]

	first=1

	first_skip=1

	for i in [0,1,2,3] :

		chopper_actual_phase[i]=chopper_set_phase[i] - CHOPPER_PHASE_OFFSET[i + m*4]



		while chopper_actual_phase[i]<0 :

			chopper_actual_phase[i] += tmp_frame_width

		

		x1= ( chopper_actual_phase[i]- ( tmp_frame_width * 0.5*CHOPPER_ANGLE[i]/360. ) ) #opening edge

		x2= ( chopper_actual_phase[i]+ ( tmp_frame_width * 0.5*CHOPPER_ANGLE[i]/360. ) ) #closing edge

                if i==0:
			print('x1: ', x1, 'x2: ', x2)
		

		if chopper_speed_in_Hz==60 : # not skipping

			while  x1<0  :

				x1+=tmp_frame_width

				x2+=tmp_frame_width

		if  x1>0 :

			chopper_wl_1[i]= 3.9560346 * x1 /CHOPPER_LOCATION[i]
			if i==0:
				print('chopper_wl_1: ', chopper_wl_1[i])

			chopper_srcpulse_wl_1[i]= 3.9560346 * ( x1-chopper_wl_1[i]*pulse_width ) /CHOPPER_LOCATION[i]

		else :

			chopper_wl_1[i]=chopper_srcpulse_wl_1[i]=0.

		if  x2>0 : chopper_wl_2[i]= 3.9560346 * x2 /CHOPPER_LOCATION[i]

		else : chopper_wl_2[i]=0.



		if  first :

			frame_wl_1=chopper_wl_1[i]

			frame_srcpulse_wl_1=chopper_srcpulse_wl_1[i]

			frame_wl_2=chopper_wl_2[i]

			first=0

		else :

			if  chopper_speed_in_Hz==30  and  i==2 :	# ignore chopper 1 and 2 forthe shortest wl.

				frame_wl_1=chopper_wl_1[i]

				frame_srcpulse_wl_1=chopper_srcpulse_wl_1[i]

			if  frame_wl_1<chopper_wl_1[i] : frame_wl_1=chopper_wl_1[i]

			if  frame_wl_2>chopper_wl_2[i] : frame_wl_2=chopper_wl_2[i]

			if  frame_srcpulse_wl_1<chopper_srcpulse_wl_1[i] : frame_srcpulse_wl_1=chopper_srcpulse_wl_1[i]

		

		if  chopper_speed_in_Hz==30 :

			if  x1>0 :

				x1 += tof_frame_width	# skipped pulse

				chopper_frameskip_wl_1[i]= 3.9560346 * x1 /CHOPPER_LOCATION[i]

				chopper_frameskip_srcpulse_wl_1[i]= 3.9560346 * ( x1-chopper_wl_1[i]*pulse_width ) /CHOPPER_LOCATION[i]

			else :  chopper_wl_1[i]=chopper_srcpulse_wl_1[i]=0.	



			if  x2>0 :

				x2 += tof_frame_width

				chopper_frameskip_wl_2[i]= 3.9560346 * x2 /CHOPPER_LOCATION[i]

			else : chopper_wl_2[i]=0.

			if  i<2  and  chopper_frameskip_wl_1[i] > chopper_frameskip_wl_2[i] : continue

			if  first_skip :

				frameskip_wl_1=chopper_frameskip_wl_1[i]

				frameskip_srcpulse_wl_1=chopper_frameskip_srcpulse_wl_1[i]

				frameskip_wl_2=chopper_frameskip_wl_2[i]

				first_skip=0

			else :

				if  i==2 :	# ignore chopper 1 and 2 forthe longest wl.

					frameskip_wl_2=chopper_frameskip_wl_2[i]

				if  chopper_frameskip_wl_1[i] < chopper_frameskip_wl_2[i] and  frameskip_wl_1<chopper_frameskip_wl_1[i] :

					frameskip_wl_1=chopper_frameskip_wl_1[i]

				if  chopper_frameskip_wl_1[i] < chopper_frameskip_wl_2[i]and  frameskip_srcpulse_wl_1<chopper_frameskip_srcpulse_wl_1[i]:

					frameskip_srcpulse_wl_1=chopper_frameskip_srcpulse_wl_1[i]

				if  frameskip_wl_2>chopper_frameskip_wl_2[i] : frameskip_wl_2=chopper_frameskip_wl_2[i]



	

	if frame_wl_1>=frame_wl_2:	# too many frames later. So figure it out

		print('frame_wl_1 > frame_wl_2', frame_wl_1, frame_wl_2)
		n_frame=[0,0,0,0]

		c_wl_1=[0,0,0,0]

		c_wl_2=[0,0,0,0]

		passed=0

		while (not passed)  and  n_frame[0]<99:

			frame_wl_1=c_wl_1[0] = chopper_wl_1[0] + 3.9560346 * n_frame[0] * tof_frame_width /CHOPPER_LOCATION[0]

			frame_wl_2=c_wl_2[0] = chopper_wl_2[0] + 3.9560346 * n_frame[0] * tof_frame_width /CHOPPER_LOCATION[0]

			print('frame_wl_1 and frame_wl_2', frame_wl_1, frame_wl_2)


			for i in [1,2,3] :

				n_frame[i] = n_frame[i-1] - 1 

				passed=0

				while n_frame[i] - n_frame[i-1] < 10 :

					n_frame[i] = n_frame[i] + 1

					c_wl_1[i] = chopper_wl_1[i] + 3.9560346 * n_frame[i] * tof_frame_width /CHOPPER_LOCATION[i]

					c_wl_2[i] = chopper_wl_2[i] + 3.9560346 * n_frame[i] * tof_frame_width /CHOPPER_LOCATION[i]

					if frame_wl_1 < c_wl_2[i]  and  frame_wl_2> c_wl_1[i] :

						passed=1

						break

					if  frame_wl_2 < c_wl_1[i] :  break #over shot

				if not passed:

				 	n_frame[0] =n_frame[0] + 1

					break

				else :

					if  frame_wl_1<c_wl_1[i] : frame_wl_1=c_wl_1[i]

					if  frame_wl_2>c_wl_2[i] : frame_wl_2=c_wl_2[i]

	

		if frame_wl_2 > frame_wl_1:

			print('frame_wl_2 > frame_wl_1', frame_wl_2, frame_wl_1)
			n=3

			if c_wl_1[2] > c_wl_1[3]:  n =2 

			frame_srcpulse_wl_1=c_wl_1[n] - 3.9560346 * c_wl_1[n] * pulse_width /CHOPPER_LOCATION[n]



			for i in [0,1,2,3] :

				chopper_wl_1[i] = c_wl_1[i]

				chopper_wl_2[i] = c_wl_2[i]

				if  chopper_speed_in_Hz==30 :

					chopper_frameskip_wl_1[i] = c_wl_1[i] +  3.9560346 * 2.* tof_frame_width /CHOPPER_LOCATION[i]

					chopper_frameskip_wl_2[i] = c_wl_2[i] +  3.9560346 * 2.* tof_frame_width /CHOPPER_LOCATION[i]

					if i==0:

						frameskip_wl_1 = chopper_frameskip_wl_1[i]

						frameskip_wl_2 = chopper_frameskip_wl_2[i]

					else :

						if  frameskip_wl_1<chopper_frameskip_wl_1[i] : frameskip_wl_1=chopper_frameskip_wl_1[i]

						if  frameskip_wl_2>chopper_frameskip_wl_2[i] : frameskip_wl_2=chopper_frameskip_wl_2[i]

		else :

			frame_srcpulse_wl_1=0.



	

	#if chopper_speed_in_Hz==60 : print "Wavelength band \t: (%g -> %g) A" % (frame_wl_1,frame_wl_2)

	#if chopper_speed_in_Hz==30 : print "Wavelength band \t: (%g -> %g) + (%g -> %g) A" % (frame_wl_1,frame_wl_2,frameskip_wl_1,frameskip_wl_2)

	#return frame_wl_1


        print(frame_wl_1,frame_wl_2,frameskip_wl_1,frameskip_wl_2)



calcBandWidth(60, 845.862, 4857.5, 6175.676, 7854.61)
calcBandWidth(30, 24605.756, 25547.531, 28204.309, 6289.279)
calcBandWidth(60, 12613.641, 14820.425, 14680.109, 16350.447 )
