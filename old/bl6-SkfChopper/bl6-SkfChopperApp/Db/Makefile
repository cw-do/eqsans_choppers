TOP=../..
include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE

#----------------------------------------------------
#  Optimization of db files using dbst (DEFAULT: NO)
#DB_OPT = YES

#----------------------------------------------------
# Create and install (or just install) into <top>/db
# databases, templates, substitutions like this
#DB +=save_restoreStatus.db

DB += skf1_ioc_sns.db
DB += skf2_ioc_sns.db
DB += skf3_ioc_sns.db
DB += skf4_ioc_sns.db
DB += skf5_ioc_sns.db
DB += skf6_ioc_sns.db

DB += skf1_saveRst.db
DB += skf2_saveRst.db
DB += skf3_saveRst.db
DB += skf4_saveRst.db
DB += skf5_saveRst.db
DB += skf6_saveRst.db

DB += hexaDskScanAssist_ioc_sns.db
DB += hexaDskScanAssist_saveRst.db
DB += hexaDskScanAssist.db
DB += chopperStats.template

#----------------------------------------------------
# If <anyname>.db template is not named <anyname>*.template add
# <anyname>_template = <templatename>

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE

