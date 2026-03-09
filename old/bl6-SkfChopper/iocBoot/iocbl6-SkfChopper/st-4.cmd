#!../../bin/linux-x86_64/bl6-SkfChopper

# Double disk chopper 3b

## You may have to change bl6-SkfChopper to something else
## everywhere it appears in this file

< envPaths

cd ${TOP}

## Register all support components
dbLoadDatabase "dbd/bl6-SkfChopper.dbd"
bl6_SkfChopper_registerRecordDeviceDriver pdbbase

#====================================================================
# modbus support

drvAsynIPPortConfigure("mb1tcp", "10.112.12.56:502", 0, 0, 0)

< ${SKFCHOP}/db/modbus-mem.cmd

#====================================================================

## Load record instances
dbLoadRecords( "db/skf4_ioc_sns.db" )
dbLoadRecords( "db/skf4_saveRst.db" )
dbLoadRecords("$(SKFCHOP)/db/softPvs.db","appVer=1-2-3,s=BL6,ta=Chop,ss=Skf4,ChType=1,devType=Modbus,ChDist=9507.0,OfsTime=19361.4,OfsAngle=0.0,ChopMod=1,ChMult=1.0,ChOfs=0.0,ChExp=0.0,FreqC1=0,FreqC2=0,DistC1=0,PhaseMode=0,MaxPhaseDelay=165000")
dbLoadRecords("$(SKFCHOP)/db/modbusPvs.db","s=BL6,ta=Chop,ss=Skf4,MaxSpeed=60")
dbLoadRecords("$(SKFCHOP)/db/refPeriodSoft.db","s=BL6,ta=Chop,ss=Skf4,port=skf4Port,addr=1")

######################################################################
# save/restore

epicsEnvSet IOCNAME bl6-Chop-Skf4
epicsEnvSet SAVE_DIR /home/controls/var/bl6-Chop-Skf4/saveRestore

save_restoreSet_Debug(0)

### status-PV prefix, so save_restore can find its status PV's.
save_restoreSet_status_prefix("BL6:SavRst:ChopSkf4:")

set_requestfile_path("$(SAVE_DIR)")
set_savefile_path("$(SAVE_DIR)")

save_restoreSet_NumSeqFiles(3)
save_restoreSet_SeqPeriodInSeconds(600)
###set_pass0_restoreFile("$(IOCNAME).sav")
###set_pass0_restoreFile("$(IOCNAME)_pass0.sav")
set_pass1_restoreFile("$(IOCNAME).sav")

######################################################################

#asynSetTraceMask("skf4Port",-1,0x000A)
#asynSetTraceIOMask("skf4Port",-1,0x0002)

## Run this to trace the stages of iocInit
#traceIocInit

# Access Security
asSetFilename("$(TOP)/../bl6-AccessSecurity/db/bl6.acf")
asSetSubstitutions("P=BL6:CS")

cd ${TOP}/iocBoot/${IOC}
iocInit

# to set gains:
#   caput -a BL6:Chop:Skf4:SpeedArray     8   0   6   10  12  15  20  30  60
#   caput -a BL6:Chop:Skf4:KpArray        8 1.25 1.25 5   10  10  10  10  10
#   caput -a BL6:Chop:Skf4:KiArray        8   1   1   5   10  10  10  10  10
#   caput -a BL6:Chop:Skf4:PhaseGainArray 8 0.33 0.33 1.33 2.33 2.33 2.33 2.33 2.33
#   caput -a BL6:Chop:Skf4:VetoArray      8   100 100 60  50  40  30  20  10

######################################################################
# save/restore

# Create request file and start periodic 'save'
makeAutosaveFileFromDbInfo("$(SAVE_DIR)/$(IOCNAME).req", "autosaveFields")
###makeAutosaveFileFromDbInfo("$(SAVE_DIR)/$(IOCNAME)_pass0.req", "autosaveFields_pass0")
create_monitor_set("$(IOCNAME).req",30,"s=BL6,ta=Chop,ss=Skf4")
###create_monitor_set("$(IOCNAME)_pass0.req", 30)

# Display status
# save_restoreShow(10)

######################################################################

## Start any sequence programs
seq skfSnc, "s=BL6,ta=Chop,ss=Skf4"
