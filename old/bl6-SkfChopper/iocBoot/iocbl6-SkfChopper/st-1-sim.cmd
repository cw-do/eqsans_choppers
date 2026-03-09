#!../../bin/linux-x86_64/bl6-SkfChopper

# Fermi chopper 300 hz 

## You may have to change bl6-SkfChopper to something else
## everywhere it appears in this file

< envPaths

cd ${TOP}

## Register all support components
dbLoadDatabase "dbd/bl6-SkfChopper.dbd"
bl6_SkfChopper_registerRecordDeviceDriver pdbbase


# ==============================
# port name, data port, ctl port, timeout,  delay per char sent, break duration, send break flag
#moxaIpAsynPortDriverConfigure( "skf1Port", "10.112.18.30:4001", "10.112.18.30:966", 250, 1.1, 20, 1 )
#asynWaitConnect("skf1Port",10)

## Load record instances
dbLoadRecords( "db/skf1_ioc_sns.db" )
dbLoadRecords( "db/skf1_saveRst.db" )


dbLoadRecords("$(SKFCHOP)/db/softPvs.db","appVer=1-2-3,s=BL6,ta=Chop,ss=Skf1,ChType=1,devType=Serial,ChDist=5702.0,OfsTime=19024.3,OfsAngle=0.0,ChopMod=1,ChMult=1.0,ChOfs=0.0,ChExp=0.0,FreqC1=0,FreqC2=0,DistC1=0,PhaseMode=1,MaxPhaseDelay=165000")
dbLoadRecords("$(SKFCHOP)/db/simDevicePvs.db","s=BL6,ta=Chop,ss=Skf1,port=skf1Port,addr=1,MaxSpeed=60")
#dbLoadRecords("$(SKFCHOP)/db/devicePvs.db","s=BL6,ta=Chop,ss=Skf1,port=skf1Port,addr=1,MaxSpeed=60")
dbLoadRecords("$(SKFCHOP)/db/refPeriodSoft.db","s=BL6,ta=Chop,ss=Skf1")

######################################################################
# save/restore

epicsEnvSet IOCNAME bl6-Chop-Skf1
epicsEnvSet SAVE_DIR /home/controls/var/bl6-Chop-Skf1/saveRestore

save_restoreSet_Debug(0)

### status-PV prefix, so save_restore can find its status PV's.
save_restoreSet_status_prefix("BL6:SavRst:ChopSkf1:")

set_requestfile_path("$(SAVE_DIR)")
set_savefile_path("$(SAVE_DIR)")

save_restoreSet_NumSeqFiles(3)
save_restoreSet_SeqPeriodInSeconds(600)
###set_pass0_restoreFile("$(IOCNAME).sav")
###set_pass0_restoreFile("$(IOCNAME)_pass0.sav")
set_pass1_restoreFile("$(IOCNAME).sav")

######################################################################

#asynSetTraceMask("skf1Port",-1,0x000A)
#asynSetTraceIOMask("skf1Port",-1,0x0002)

## Run this to trace the stages of iocInit
#traceIocInit

# Access Security
#asSetFilename("$(TOP)/../bl6-AccessSecurity/db/bl6.acf")
#asSetSubstitutions("P=BL6:CS")

cd ${TOP}/iocBoot/${IOC}
iocInit

# to set gains:
#   caput -a BL6:Chop:Skf1:SpeedArray     8   0   6   10  12  15  20  30  60
#   caput -a BL6:Chop:Skf1:KpArray        8   5   5   8   10  10  10  10  20
#   caput -a BL6:Chop:Skf1:KiArray        8   5   5   10  10  10  10  10  10
#   caput -a BL6:Chop:Skf1:PhaseGainArray 8   0.5 0.5 3   3 2.33 2.33 2.33 2.33
#   caput -a BL6:Chop:Skf1:VetoArray      8   100 100 60  50  40  30  20  10
 


######################################################################
# save/restore

# Create request file and start periodic 'save'
makeAutosaveFileFromDbInfo("$(SAVE_DIR)/$(IOCNAME).req", "autosaveFields")
###makeAutosaveFileFromDbInfo("$(SAVE_DIR)/$(IOCNAME)_pass0.req", "autosaveFields_pass0")
create_monitor_set("$(IOCNAME).req",30,"s=BL6,ta=Chop,ss=Skf1")
###create_monitor_set("$(IOCNAME)_pass0.req", 30)

# Display status
# save_restoreShow(10)

######################################################################

# Start any sequence programs
seq skfSnc, "s=BL6,ta=Chop,ss=Skf1"
 
# for testing
seq rampWithFixedRate, "SetPointPv=BL6:Chop:Skf1:SpeedSet,ReadBackPv=BL6:Chop:Skf1:MotorSpeedSim,Rate=10,TimeInc=1"
seq rampWithFixedRate, "SetPointPv=BL6:Chop:Skf1:PhaseTimeDelaySet,ReadBackPv=BL6:Chop:Skf1:PhaseAccuracySim,Rate=100,TimeInc=1"
seq copy, "FromPv=BL6:Chop:Skf1:SpeedSet,ToPv=BL6:Chop:Skf1:RunSpeedSetpointSim,Delay=1"
seq copy, "FromPv=BL6:Chop:Skf1:PhaseTimeDelaySet,ToPv=BL6:Chop:Skf1:PhaseTimeDelaySim,Delay=1"

