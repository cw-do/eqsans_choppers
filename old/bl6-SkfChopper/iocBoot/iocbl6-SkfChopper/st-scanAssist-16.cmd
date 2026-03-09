#!../../bin/linux-x86_64/bl6-SkfChopper

# All four choppers on eqsans 

< envPaths

cd ${TOP}

## Register all support components
dbLoadDatabase "dbd/bl6-SkfChopper.dbd"
bl6_SkfChopper_registerRecordDeviceDriver pdbbase

## Load record instances
dbLoadRecords( "db/hexaDskScanAssist_ioc_sns.db" )
dbLoadRecords( "db/hexaDskScanAssist_saveRst.db" )
dbLoadRecords( "db/hexaDskScanAssist.db", "s=BL6,ta=Chop,hexa=16,dp=BL6:Mot:detZmot.RBV")
dbLoadRecords( "db/chopperStats.template", "S=BL6")

######################################################################
# save/restore

epicsEnvSet IOCNAME bl6-Chop-ScanAssist16
epicsEnvSet SAVE_DIR /home/controls/var/bl6-Chop-SkfCalc16/saveRestore

save_restoreSet_Debug(0)

### status-PV prefix, so save_restore can find its status PV's.
save_restoreSet_status_prefix("BL6:SavRst:ChopSkfCalc16:")

set_requestfile_path("$(SAVE_DIR)")
set_savefile_path("$(SAVE_DIR)")

save_restoreSet_NumSeqFiles(3)
save_restoreSet_SeqPeriodInSeconds(600)
###set_pass0_restoreFile("$(IOCNAME).sav")
###set_pass0_restoreFile("$(IOCNAME)_pass0.sav")
set_pass1_restoreFile("$(IOCNAME).sav")

######################################################################

# Access Security
#asSetFilename("$(TOP)/../bl6-AccessSecurity/db/bl6.acf")
#asSetSubstitutions("P=BL6:CS")

cd ${TOP}/iocBoot/${IOC}
iocInit

######################################################################
# save/restore

# Create request file and start periodic 'save'
makeAutosaveFileFromDbInfo("$(SAVE_DIR)/$(IOCNAME).req", "autosaveFields")
create_monitor_set("$(IOCNAME).req",30,"s=BL6,ta=Chop,hexa=16")

# Display status
# save_restoreShow(10)

######################################################################

seq snglSpeedPutComplete, "cbPv=BL6:Chop:Skf1:SpeedReq, cbPvBusy=BL6:Chop:Skf1:SpeedReqBusy, ctlPv=BL6:Chop:Skf1:SpeedSet, userPv=BL6:Chop:Skf1:SpeedUserReq, mainSeqState=BL6:Chop:Skf1:State"

seq snglSpeedPutComplete, "cbPv=BL6:Chop:Skf2:SpeedReq, cbPvBusy=BL6:Chop:Skf2:SpeedReqBusy, ctlPv=BL6:Chop:Skf2:SpeedSet, userPv=BL6:Chop:Skf2:SpeedUserReq, mainSeqState=BL6:Chop:Skf2:State"

seq snglSpeedPutComplete, "cbPv=BL6:Chop:Skf3:SpeedReq, cbPvBusy=BL6:Chop:Skf3:SpeedReqBusy, ctlPv=BL6:Chop:Skf3:SpeedSet, userPv=BL6:Chop:Skf3:SpeedUserReq, mainSeqState=BL6:Chop:Skf3:State"

seq snglSpeedPutComplete, "cbPv=BL6:Chop:Skf4:SpeedReq, cbPvBusy=BL6:Chop:Skf4:SpeedReqBusy, ctlPv=BL6:Chop:Skf4:SpeedSet, userPv=BL6:Chop:Skf4:SpeedUserReq, mainSeqState=BL6:Chop:Skf4:State"

seq snglSpeedPutComplete, "cbPv=BL6:Chop:Skf5:SpeedReq, cbPvBusy=BL6:Chop:Skf5:SpeedReqBusy, ctlPv=BL6:Chop:Skf5:SpeedSet, userPv=BL6:Chop:Skf5:SpeedUserReq, mainSeqState=BL6:Chop:Skf5:State"

seq snglSpeedPutComplete, "cbPv=BL6:Chop:Skf6:SpeedReq, cbPvBusy=BL6:Chop:Skf6:SpeedReqBusy, ctlPv=BL6:Chop:Skf6:SpeedSet, userPv=BL6:Chop:Skf6:SpeedUserReq, mainSeqState=BL6:Chop:Skf6:State"

seq snglPhasePutComplete, "cbPv=BL6:Chop:Skf1:TotalDelayReq, cbPvBusy=BL6:Chop:Skf1:TotalDelayReqBusy, ctlPv=BL6:Chop:Skf1:TotalDelaySet, userPv=BL6:Chop:Skf1:TotalDelayUserReq, mainSeqState=BL6:Chop:Skf1:State"

seq snglPhasePutComplete, "cbPv=BL6:Chop:Skf2:TotalDelayReq, cbPvBusy=BL6:Chop:Skf2:TotalDelayReqBusy, ctlPv=BL6:Chop:Skf2:TotalDelaySet, userPv=BL6:Chop:Skf2:TotalDelayUserReq, mainSeqState=BL6:Chop:Skf2:State"

seq snglPhasePutComplete, "cbPv=BL6:Chop:Skf3:TotalDelayReq, cbPvBusy=BL6:Chop:Skf3:TotalDelayReqBusy, ctlPv=BL6:Chop:Skf3:TotalDelaySet, userPv=BL6:Chop:Skf3:TotalDelayUserReq, mainSeqState=BL6:Chop:Skf3:State"

seq snglPhasePutComplete, "cbPv=BL6:Chop:Skf4:TotalDelayReq, cbPvBusy=BL6:Chop:Skf4:TotalDelayReqBusy, ctlPv=BL6:Chop:Skf4:TotalDelaySet, userPv=BL6:Chop:Skf4:TotalDelayUserReq, mainSeqState=BL6:Chop:Skf4:State"

seq snglPhasePutComplete, "cbPv=BL6:Chop:Skf5:TotalDelayReq, cbPvBusy=BL6:Chop:Skf5:TotalDelayReqBusy, ctlPv=BL6:Chop:Skf5:TotalDelaySet, userPv=BL6:Chop:Skf5:TotalDelayUserReq, mainSeqState=BL6:Chop:Skf5:State"

seq snglPhasePutComplete, "cbPv=BL6:Chop:Skf6:TotalDelayReq, cbPvBusy=BL6:Chop:Skf6:TotalDelayReqBusy, ctlPv=BL6:Chop:Skf6:TotalDelaySet, userPv=BL6:Chop:Skf6:TotalDelayUserReq, mainSeqState=BL6:Chop:Skf6:State"

# Process the request PV (ProcDistReq) to cause a new detector distance to be 
# read from the Z motor PV (dp parameter to hexaDskScanAssist.db) and chopper 
# phase settings adjusted for it.
seq hexaPhasePutComplete, "cbPv=BL6:Chop:Skf16:ProcDistReq, cbPvBusy=BL6:Chop:Skf16:ProcDistReqBusy, ctlPv=BL6:Chop:Skf16:ProcDistSet.PROC, mainSeqState1=BL6:Chop:Skf1:State, mainSeqState2=BL6:Chop:Skf2:State, mainSeqState3=BL6:Chop:Skf3:State, mainSeqState4=BL6:Chop:Skf4:State, mainSeqState5=BL6:Chop:Skf5:State, mainSeqState6=BL6:Chop:Skf6:State"

seq hexaPhasePutComplete, "cbPv=BL6:Chop:Skf16:InitWvlenReq, cbPvBusy=BL6:Chop:Skf16:InitWvlenReqBusy, ctlPv=BL6:Chop:Skf16:InitWvlenSet, mainSeqState1=BL6:Chop:Skf1:State, mainSeqState2=BL6:Chop:Skf2:State, mainSeqState3=BL6:Chop:Skf3:State, mainSeqState4=BL6:Chop:Skf4:State, mainSeqState5=BL6:Chop:Skf5:State, mainSeqState6=BL6:Chop:Skf6:State"

seq hexaPhasePutComplete, "cbPv=BL6:Chop:Skf16:MCMaxWvlenReq, cbPvBusy=BL6:Chop:Skf16:InitWvlenReqBusy, ctlPv=BL6:Chop:Skf16:MCMaxWvlenSet, mainSeqState1=BL6:Chop:Skf1:State, mainSeqState2=BL6:Chop:Skf2:State, mainSeqState3=BL6:Chop:Skf3:State, mainSeqState4=BL6:Chop:Skf4:State, mainSeqState5=BL6:Chop:Skf5:State, mainSeqState6=BL6:Chop:Skf6:State"
