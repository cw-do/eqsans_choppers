
#include <stdio.h>
#include <math.h>

#include <aSubRecord.h>
#include <registryFunction.h>
#include <epicsExport.h>

/*
 * Port of calcBandWidth() function in eqsans_scans.py
 *
 * Inputs:
 * chopper_speed1_value = *prec->a
 * chopper_phases1_value = *prec->b 
 * chopper_phases2_value = *prec->c
 * chopper_phases3_value = *prec->d
 * chopper_phases4_value = *prec->e
 *
 * Outputs:
 * frame_wl_1 on *prec->vala
 * frame_wl_2 on *prec->valb
 * frameskip_wl_1 on *prec->valc
 * frameskip_wl_2 on *prec->vald
 *
 */
static long calc6Wavelengths(aSubRecord *prec) {
   double CHOPPER_PHASE_OFFSET[] = { 9507,9507, 9471,9471, 9829.7,9829.7, 9584.3,9584.3,
                                       19024.3,18820,19714, 19361.4 };
   double CHOPPER_ANGLE[] ={129.605,129.605,179.989,179.989,230.010,230.007 };
   double CHOPPER_LOCATION[] ={5700.0,5700.0,7800.0,7800.0,9497.0,9507.0 };
   double chopper_wl_1[] = {0,0,0,0,0,0};
   double chopper_srcpulse_wl_1[] = {0,0,0,0,0,0};
   double chopper_wl_2[] = {0,0,0,0,0,0};
   double chopper_actual_phase[] = {0,0,0,0,0,0};
   double tof_frame_width = 1e6/60.;
   double tmp_frame_width = tof_frame_width;
   double frame_wl_1=0;
   double frame_wl_2=0;
   double frameskip_wl_1=0;
   double frameskip_wl_2=0;
   double pulse_width=0;	/* micro sec /A */
   double chopper_set_phase[6];
   int chopper_speed_in_Hz;
   int i, m, n;
   double chopper_frameskip_wl_1[]={0,0,0,0,0,0};
   double chopper_frameskip_wl_2[]={0,0,0,0,0,0};
   double chopper_frameskip_srcpulse_wl_1[]={0,0,0,0,0,0};
   int first=1;
   int first_skip=1;
   double x1, x2;
   double frame_srcpulse_wl_1;
   double frameskip_srcpulse_wl_1;

   chopper_set_phase[0] = *(double *)prec->b;
   chopper_set_phase[1] = *(double *)prec->c;
   chopper_set_phase[2] = *(double *)prec->d;
   chopper_set_phase[3] = *(double *)prec->e;
   chopper_set_phase[4] = *(double *)prec->f;
   chopper_set_phase[5] = *(double *)prec->g;

   chopper_speed_in_Hz = *(short *)prec->a;
   if (chopper_speed_in_Hz != 30 && chopper_speed_in_Hz != 60 ) {
      printf("Unsupported speed %d in calc6Wavelengths\n", chopper_speed_in_Hz);
      return -1;
   }
   m = 0;
   if (chopper_speed_in_Hz == 30) {
      m = 1;
      tmp_frame_width *= 2;
   }

   for (i=0; i<4; i++) {
      chopper_actual_phase[i]=chopper_set_phase[i] - 
                              CHOPPER_PHASE_OFFSET[i + m*4];
      while (chopper_actual_phase[i]<0) {
         chopper_actual_phase[i] += tmp_frame_width;
      }
      x1= ( chopper_actual_phase[i]- 
          ( tmp_frame_width * 0.5*CHOPPER_ANGLE[i]/360.0 ) ); /* opening edge */
      x2= ( chopper_actual_phase[i]+ 
          ( tmp_frame_width * 0.5*CHOPPER_ANGLE[i]/360.0 ) ); /* closing edge */
      if (chopper_speed_in_Hz==60)  /* not skipping */ {
         while  (x1<0) {
            x1+=tmp_frame_width;
            x2+=tmp_frame_width;
         }
      }
      if  (x1>0) {
         chopper_wl_1[i]= 3.9560346 * x1 /CHOPPER_LOCATION[i];
         chopper_srcpulse_wl_1[i]= 3.9560346 * 
                ( x1-chopper_wl_1[i]*pulse_width ) /CHOPPER_LOCATION[i];
      } else {
          chopper_wl_1[i]=chopper_srcpulse_wl_1[i]=0.0;
      }
      if  (x2>0) {
         chopper_wl_2[i]= 3.9560346 * x2 /CHOPPER_LOCATION[i];
      } else { 
         chopper_wl_2[i]=0.0;
      }
      if  (first) {
         frame_wl_1=chopper_wl_1[i];
         frame_srcpulse_wl_1=chopper_srcpulse_wl_1[i];
         frame_wl_2=chopper_wl_2[i];
         first=0;
      } else {
         if (chopper_speed_in_Hz==30 && i==2) {	
            /* ignore chopper 1 and 2 forthe shortest wl. */
            frame_wl_1=chopper_wl_1[i];
            frame_srcpulse_wl_1=chopper_srcpulse_wl_1[i];
         }
         if (frame_wl_1<chopper_wl_1[i]) frame_wl_1=chopper_wl_1[i];
         if (frame_wl_2>chopper_wl_2[i]) frame_wl_2=chopper_wl_2[i];
         if (frame_srcpulse_wl_1<chopper_srcpulse_wl_1[i])
            frame_srcpulse_wl_1=chopper_srcpulse_wl_1[i];
      }
      if (chopper_speed_in_Hz==30) {
         if (x1>0) {
            x1 += tof_frame_width;	/* skipped pulse */
            chopper_frameskip_wl_1[i]= 3.9560346 * x1 /CHOPPER_LOCATION[i];
            chopper_frameskip_srcpulse_wl_1[i]= 3.9560346 * 
               ( x1-chopper_wl_1[i]*pulse_width ) /CHOPPER_LOCATION[i];
          } else {  
             chopper_wl_1[i]=chopper_srcpulse_wl_1[i]=0.0;
          }
          if  (x2>0) {
             x2 += tof_frame_width;
             chopper_frameskip_wl_2[i]= 3.9560346 * x2 /CHOPPER_LOCATION[i];
          } else { 
             chopper_wl_2[i]=0.0;
          }
          if  (i<2 && chopper_frameskip_wl_1[i] > chopper_frameskip_wl_2[i]) 
              continue;
          if (first_skip) {
             frameskip_wl_1=chopper_frameskip_wl_1[i];
             frameskip_srcpulse_wl_1=chopper_frameskip_srcpulse_wl_1[i];
             frameskip_wl_2=chopper_frameskip_wl_2[i];
             first_skip=0;
          } else {
             if  (i==2) /* ignore chopper 1 and 2 forthe longest wl. */
                frameskip_wl_2=chopper_frameskip_wl_2[i];
             if  (chopper_frameskip_wl_1[i] < chopper_frameskip_wl_2[i] &&  
                  frameskip_wl_1<chopper_frameskip_wl_1[i]) 
                frameskip_wl_1=chopper_frameskip_wl_1[i];
             if  (chopper_frameskip_wl_1[i] < chopper_frameskip_wl_2[i] &&  
                  frameskip_srcpulse_wl_1<chopper_frameskip_srcpulse_wl_1[i] )
                frameskip_srcpulse_wl_1=chopper_frameskip_srcpulse_wl_1[i];
             if  (frameskip_wl_2>chopper_frameskip_wl_2[i])  
                frameskip_wl_2=chopper_frameskip_wl_2[i];
         }
      }  /* 30 Hz */
   }  /* for */  
   if (frame_wl_1>=frame_wl_2) { /* too many frames later. So figure it out */
      int n_frame[] = {0,0,0,0};
      double c_wl_1[] = {0,0,0,0};
      double c_wl_2[] = {0,0,0,0};
      int passed=0;

      while (!passed && n_frame[0]<99) {
         frame_wl_1=c_wl_1[0] = chopper_wl_1[0] + 3.9560346 * n_frame[0] * 
                                tof_frame_width /CHOPPER_LOCATION[0];
         frame_wl_2=c_wl_2[0] = chopper_wl_2[0] + 3.9560346 * n_frame[0] * 
                                tof_frame_width /CHOPPER_LOCATION[0];
         for (i = 1; i < 4; i++) {
            n_frame[i] = n_frame[i-1] - 1 ;
            passed=0;
            while (n_frame[i] - n_frame[i-1] < 10) {
               n_frame[i] = n_frame[i] + 1;
               c_wl_1[i] = chopper_wl_1[i] + 3.9560346 * n_frame[i] * 
                           tof_frame_width /CHOPPER_LOCATION[i];
               c_wl_2[i] = chopper_wl_2[i] + 3.9560346 * n_frame[i] * 
                           tof_frame_width /CHOPPER_LOCATION[i];
               if (frame_wl_1 < c_wl_2[i] && frame_wl_2> c_wl_1[i]) { 
                  passed=1;
                  break;
               }
               if  (frame_wl_2 < c_wl_1[i])    break;  /* over shot */
            }
            if (!passed) {
               n_frame[0] =n_frame[0] + 1;
               break;
            } else {
               if (frame_wl_1<c_wl_1[i]) frame_wl_1=c_wl_1[i];
               if (frame_wl_2>c_wl_2[i]) frame_wl_2=c_wl_2[i];
            }
         }
      }
      if (frame_wl_2 > frame_wl_1) {
         n=3;
         if (c_wl_1[2] > c_wl_1[3])  n = 2;
         frame_srcpulse_wl_1 = c_wl_1[n] - 3.9560346 * c_wl_1[n] * 
                               pulse_width /CHOPPER_LOCATION[n];
         for (i = 0; i < 4; i++) {
            chopper_wl_1[i] = c_wl_1[i];
            chopper_wl_2[i] = c_wl_2[i];
            if (chopper_speed_in_Hz==30) {
               chopper_frameskip_wl_1[i] = c_wl_1[i] +  3.9560346 * 2.0 * 
                                           tof_frame_width /CHOPPER_LOCATION[i];
               chopper_frameskip_wl_2[i] = c_wl_2[i] +  3.9560346 * 2.0 * 
                                           tof_frame_width /CHOPPER_LOCATION[i];
               if (i==0) {
                  frameskip_wl_1 = chopper_frameskip_wl_1[i];
                  frameskip_wl_2 = chopper_frameskip_wl_2[i];
               } else {
                  if (frameskip_wl_1<chopper_frameskip_wl_1[i])  
                     frameskip_wl_1=chopper_frameskip_wl_1[i];
                  if (frameskip_wl_2>chopper_frameskip_wl_2[i]) 
                     frameskip_wl_2=chopper_frameskip_wl_2[i];
               }
            }
         }
      } else {
         frame_srcpulse_wl_1=0.0;
      }
   }
   *(double *)prec->vala = frame_wl_1;
   *(double *)prec->valb = frame_wl_2;
   *(double *)prec->valc = frameskip_wl_1;
   *(double *)prec->vald = frameskip_wl_2;
   return 0;
}

epicsRegisterFunction(calc6Wavelengths);

/*
 * Port of calcChopperByStartingWavelength() function in eqsans_scans.py
 *
 * sample_to_moderator_in_m = *prec->b
 * sample_to_detector_in_m = *prec->d
 * start_wavelength = *prec->a
 * speed = *prec->c
 *
 * Arrays are used in several places where numbered scalars were used in the 
 * python. Note that index zero of the arrays is not used to maintain the 
 * original numbering 1-4.
 */
static long calc6Phases(aSubRecord *prec) {
   //printf("in calc6phase\n");
   double detector_location, max_wl;
   double chopper_location[] = { 0, 5700, 7800, 9497, 9507, 5700, 7800 };
   double chopper_opening[] = { 0, 129.605, 179.989, 230.010, 230.007, 129.605, 179.989 };

   /* next two set to zero in code, but left in place just in case */
   double pulse_width = 0;		/* 20* 1e-6 sec per angstrom */
   double beam_crosssection = 0;	/* 40 mm */

   double chopper_disc_diameter = 578.5;
   double bandwidth_at_60Hz;
   double wl[7];
   double phase[7];
   double detector_z_tol = 0.005;
   double frame_width;
   double beam_crosssection_adjust;
   double half_angle_to_sec;
   int chopper_speed_in_Hz;
   int monochromatic_mode;

   chopper_speed_in_Hz = *(int *)prec->c;
   detector_location = *(double *)prec->d + *(double *)prec->b;
   detector_location *= 1000.0;
   bandwidth_at_60Hz = 3.956e6/detector_location/60.0;
   monochromatic_mode = *(int *)prec->e;
   max_wl = *(double *)prec->f;

   wl[1] = *(double *)prec->a;
   if (!monochromatic_mode){
      wl[2] = wl[1] + bandwidth_at_60Hz;
   }
   else if (monochromatic_mode){
      wl[2] = max_wl;
   }
   //printf("in wl2 %f\n", wl[2]);
   frame_width = 1.0e6/ chopper_speed_in_Hz;
   half_angle_to_sec = 1.0 / 360.0 / chopper_speed_in_Hz / 2.0;
   /* delay opening or close earlier by half the beam cross section */
   beam_crosssection_adjust = beam_crosssection / 
                              (chopper_disc_diameter * 3.1415926) / 
                              chopper_speed_in_Hz / 2;
   
   if (chopper_speed_in_Hz == 30) {
      double phase_offset[] = { 0, 19024.3, 18820, 19714, 19361.4, 19024.3, 1882 };

      if (*(double *)prec->b > (5 + detector_z_tol)) {
         printf("Frame skipping operation does not work for SDD > 5m!\n");
         return -1;
      }
      wl[3] = wl[2] + bandwidth_at_60Hz;
      wl[4] = wl[3] + bandwidth_at_60Hz;
      /* chopper 1 opening edge aligned to wl[3], now in sec, from prev pulse.
       */
      phase[1] = chopper_location[1]/3.956e6*wl[3] - 1.0/60.0;
      phase[1] += beam_crosssection_adjust;	/* delay opening half beam */
      phase[1] += chopper_opening[1] * half_angle_to_sec; /* move to center */
      phase[1] = 1.0e6 * phase[1] + phase_offset[1];      
      phase[1] = fmod(phase[1], frame_width);

      phase[5] = chopper_location[5]/3.956e6*wl[3] - 1.0/60.0;
      phase[5] += beam_crosssection_adjust;	/* delay opening half beam */
      phase[5] += chopper_opening[5] * half_angle_to_sec; /* move to center */
      phase[5] = 1.0e6 * phase[5] + phase_offset[5];      
      phase[5] = fmod(phase[5], frame_width);

      /* chopper 2 closing edge aligned to wl[2], now in sec */
      phase[2] = chopper_location[2]/3.956e6*wl[2];
      phase[2] -= beam_crosssection_adjust;	/* advance closing half beam */
      phase[2] -= chopper_opening[2] * half_angle_to_sec; /* move to center */
      phase[2] = 1.0e6 * phase[2] + phase_offset[2];      
      phase[2] = fmod(phase[2], frame_width);
      
      phase[6] = chopper_location[6]/3.956e6*wl[2];
      phase[6] -= beam_crosssection_adjust;	/* advance closing half beam */
      phase[6] -= chopper_opening[6] * half_angle_to_sec; /* move to center */
      phase[6] = 1.0e6 * phase[6] + phase_offset[6];      
      phase[6] = fmod(phase[6], frame_width);

      /* chopper 3 closing edge aligned to wl[4], now in sec */
      phase[3] = chopper_location[3]/3.956e6*wl[4] - 1.0/60.0;
      phase[3] -= beam_crosssection_adjust;	/* advance closing half beam */
      phase[3] -= chopper_opening[3] * half_angle_to_sec; /* move to center */
      phase[3] = 1.0e6 * phase[3] + phase_offset[3];      
      phase[3] = fmod(phase[3], frame_width);

      /* chopper 4 opening edge aligned to wl[1], now in sec */
      phase[4] = chopper_location[4]/3.956e6*wl[1];
      phase[4] += beam_crosssection_adjust;	/* advance closing half beam */
      phase[4] += pulse_width *wl[1] / detector_location * chopper_location[4];
      phase[4] += chopper_opening[4] * half_angle_to_sec; /* move to center */
      phase[4] = 1.0e6 * phase[4] + phase_offset[4];      
      /* phase[4] += frame_width/2.0; */
      phase[4] = fmod(phase[4], frame_width);
   } else if (chopper_speed_in_Hz == 60) {
      double phase_offset[] = { 0, 9507, 9471, 9829.7, 9584.3, 9507, 9471 };
     
      /* we align the chopper differently between wl[1]>13 and wl[1]<=13
       * to stop leaks.  */
      if (wl[1] > 13) { 
         phase[1] = chopper_location[1]/3.956e6 * wl[1];
         phase[1] += chopper_opening[1] * half_angle_to_sec;
         phase[5] = chopper_location[5]/3.956e6 * wl[1];
         phase[5] += chopper_opening[5] * half_angle_to_sec;

         phase[2] = chopper_location[2]/3.956e6 * wl[2];
         phase[2] -= chopper_opening[2] * half_angle_to_sec;
         phase[6] = chopper_location[6]/3.956e6 * wl[2];
         phase[6] -= chopper_opening[6] * half_angle_to_sec;
      } else {
         phase[1] = chopper_location[1]/3.956e6 * wl[2];
         phase[1] -= chopper_opening[1] * half_angle_to_sec;
         phase[5] = chopper_location[5]/3.956e6 * wl[2];
         phase[5] -= chopper_opening[5] * half_angle_to_sec;

         phase[2] = chopper_location[2]/3.956e6 * wl[1];
         phase[2] += chopper_opening[2] * half_angle_to_sec;
         phase[6] = chopper_location[6]/3.956e6 * wl[1];
         phase[6] += chopper_opening[6] * half_angle_to_sec;
      }
      phase[1] = 1.0e6 * phase[1] + phase_offset[1];
      phase[1] = fmod(phase[1], frame_width);
      phase[5] = 1.0e6 * phase[5] + phase_offset[5];
      phase[5] = fmod(phase[5], frame_width);

      phase[2] = 1.0e6 * phase[2] + phase_offset[2];
      phase[2] = fmod(phase[2], frame_width);
      phase[6] = 1.0e6 * phase[6] + phase_offset[6];
      phase[6] = fmod(phase[6], frame_width);

      /* chopper 3 closing edge aligned to wl[2] */
      phase[3] = chopper_location[3]/3.956e6 * wl[2];
      phase[3] -= beam_crosssection_adjust;
      phase[3] -= chopper_opening[3] * half_angle_to_sec;
      phase[3] = 1.0e6 * phase[3] + phase_offset[3];
      phase[3] = fmod(phase[3], frame_width);

      /* chopper 4 opening edge aligned to wl[1] */
      phase[4] = chopper_location[4]/3.956e6 * wl[1];
      phase[4] += beam_crosssection_adjust;
      phase[4] += pulse_width * wl[1];
      phase[4] += chopper_opening[4] * half_angle_to_sec; /* move to center */
      phase[4] = 1.0e6 * phase[4] + phase_offset[4];
      phase[4] = fmod(phase[4], frame_width);

      /* check if T1 is not opened enough */
      if (detector_location < 360/chopper_opening[1] * chopper_location[1]) {
         double x1;

         x1=3.956*(phase[1] - phase_offset[1] - 1.0e6*chopper_opening[1] * 
            half_angle_to_sec)/chopper_location[1];
         x1 -= wl[1];
         if (x1 > 0 && x1 < 0.2) {
            // printf("T1 correction applied\n");
            phase[1] -= x1 *chopper_location[1]/3.956;
         }
      }

            /* check if T1 is not opened enough */
      if (detector_location < 360/chopper_opening[5] * chopper_location[5]) {
         double x1;

         x1=3.956*(phase[5] - phase_offset[5] - 1.0e6*chopper_opening[5] * 
            half_angle_to_sec)/chopper_location[5];
         x1 -= wl[1];
         if (x1 > 0 && x1 < 0.2) {
            // printf("T1 correction applied\n");
            phase[5] -= x1 *chopper_location[5]/3.956;
         }
      }


   } else {
      printf("only 30 Hz and 60 Hz operations are supported\n");
      return -1;
   }

   *(double *)prec->vala = phase[1];
   *(double *)prec->valb = phase[2];
   *(double *)prec->valc = phase[3];
   *(double *)prec->vald = phase[4];
   *(double *)prec->vale = phase[5];
   *(double *)prec->valf = phase[6];
   return 0;
}

epicsRegisterFunction(calc6Phases);
