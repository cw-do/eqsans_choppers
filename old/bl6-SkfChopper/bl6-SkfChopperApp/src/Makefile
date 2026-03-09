TOP=../..

include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE
#=============================

#USR_CXXFLAGS += -fpermissive
#USR_CFLAGS += -O0
#USR_LDFLAGS += -g

#=============================
# Build the IOC application

PROD_IOC = bl6-SkfChopper
# bl6-SkfChopper.dbd will be created and installed
DBD += bl6-SkfChopper.dbd

# bl6-SkfChopper.dbd will be made up from these files:
bl6-SkfChopper_DBD += base.dbd
bl6-SkfChopper_DBD += asSupport.dbd
bl6-SkfChopper_DBD += busyRecord.dbd
bl6-SkfChopper_DBD += busySupport.dbd
bl6-SkfChopper_DBD += calcSupport.dbd
bl6-SkfChopper_DBD += menuScan.dbd
bl6-SkfChopper_DBD += initTrace.dbd
bl6-SkfChopper_DBD += skfChop.dbd
bl6-SkfChopper_DBD += devIocStats.dbd

bl6-SkfChopper_DBD += hexaPhase.dbd

bl6-SkfChopper_DBD += modbusSupport.dbd
bl6-SkfChopper_DBD += asyn.dbd
bl6-SkfChopper_DBD += drvAsynIPPort.dbd

# bl6-SkfChopper_registerRecordDeviceDriver.cpp derives from bl6-SkfChopper.dbd
bl6-SkfChopper_SRCS += bl6-SkfChopper_registerRecordDeviceDriver.cpp
bl6-SkfChopper_SRCS += initTrace.c
bl6-SkfChopper_SRCS += hexaSub.c
bl6-SkfChopper_SRCS += hexaPhasePutComplete.stt

# Build the main IOC entry point on workstation OSs.
bl6-SkfChopper_SRCS_DEFAULT += bl6-SkfChopperMain.cpp
bl6-SkfChopper_SRCS_vxWorks += -nil-

# Add support from base/src/vxWorks if needed
#bl6-SkfChopper_OBJS_vxWorks += $(EPICS_BASE_BIN)/vxComLibrary

# NOTE: To build SNL programs, SNCSEQ must be defined
# in the <top>/configure/RELEASE file


# Build sequencers into bl6-SkfChopper

bl6-SkfChopper_DBD += skfSnc.dbd
bl6-SkfChopper_DBD += snglSpeedPutComplete.dbd
bl6-SkfChopper_DBD += dblSpeedPutComplete.dbd
bl6-SkfChopper_DBD += snglPhasePutComplete.dbd
bl6-SkfChopper_DBD += dblPhasePutComplete.dbd
bl6-SkfChopper_DBD += rampWithFixedRate.dbd
bl6-SkfChopper_DBD += copy.dbd
bl6-SkfChopper_DBD += changeBit.dbd

bl6-SkfChopper_LIBS += skfChop
bl6-SkfChopper_LIBS += seq pv



# Finally link to the EPICS Base libraries
bl6-SkfChopper_LIBS += asyn
bl6-SkfChopper_LIBS += autosave
bl6-SkfChopper_LIBS += $(EPICS_BASE_IOC_LIBS)
bl6-SkfChopper_LIBS += busy
bl6-SkfChopper_LIBS += calc
bl6-SkfChopper_LIBS += devIocStats
bl6-SkfChopper_LIBS += modbus

#===========================

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE
