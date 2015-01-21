#--------------------------------------------------------------------------
# Tool Name:  CompressFileGeodatabaseData
# Source Name: CompressFileGeodatabaseData.py
# Version: ArcGIS 9.2
# Author: ESRI
#
# This tool performs the default method of compressing a feature class.
# This approach involves running the following tools, with all parameters 
# set to default, on the input dataset:
# (1) BlockByProximity
# (2) CompressFileGeodatabaseDataAdvanced
#--------------------------------------------------------------------------

# Import system modules
import sys, os, string, arcgisscripting

# Create the Geoprocessor object and set the environment...
gp = arcgisscripting.create()
gp.OverWriteOutput = 1


# Error message text vars...
msgNotFileGDB = "Only FileGDB data can be compressed..."
msgCompressingFileGDBFeatureClass = "Compressing the FeatureClass: "
msgCompressingWorksace = "Compressing the Workspace: "
msgCompressingFeatureDataset = "Compressing the FeatureDataset: "
msgNotSupported = "Datatype not Supported"

# Local variables...
# if the scratch workspace environment is not set, then set it to the "TEMP" system environment
if not gp.ScratchWorkspace:
    gp.ScratchWorkspace = gp.GetSystemEnvironment("TEMP")

temp_blk = gp.ScratchWorkspace + "/temp"
n = 0

# Script arguments...
MyWorkspace = gp.GetParameterAsText(0)
FeatureData = gp.GetParameterAsText(1)

def CompressFileGDB_FC (FeatureClass):
    try:
        if (gp.Describe(FeatureClass).DatasetType) == "FeatureClass":
            global n
            gp.AddMessage (msgCompressingFileGDBFeatureClass + "%s" % (FeatureClass))
            # Process: Block By Proximity...
            while gp.exists(temp_blk + str(n) + ".blk"):
                n = n + 1
            gp.BlockByProximity_management(FeatureClass, temp_blk + str(n) + ".blk", "", "")
            # Process: Compress Dataset...
            gp.CompressFileGeodatabaseDataAdvanced_management(FeatureClass, temp_blk + str(n) + ".blk", "")
            n = n + 1
            
    except Exception, ErrDesc:
        #Add error messages to Geoprocessing window
        gp.AddError(str(ErrDesc))
    
#--------------------------------------------------------------------------

#--------------------------------------------------------------------------
#MAIN
try:
    if ((len(MyWorkspace) > 0) and (len(FeatureData) == 0)):
        
        if (string.find (MyWorkspace,".gdb")) <= 0:
            raise Exception, msgNotFileGDB

        ## Compress the stand alone FeatureClasses
        gp.AddMessage (msgCompressingWorksace)
        gp.Workspace = MyWorkspace
        fcs = gp.ListFeatureClasses()
        fc = fcs.Next()
        while fc:
            CompressFileGDB_FC (fc)
            fc = fcs.Next()
        ## Compress the FeatureDatasets
        fds = gp.ListDatasets()
        fd = fds.Next()
        while fd:
            #gp.AddMessage (msgCompressingFeatureDataset + "%s" % (fd))
            gp.Workspace = MyWorkspace + "/" + fd
            fcs = gp.ListFeatureClasses()
            gp.Workspace = " "
            myFC = fcs.Next()
            while myFC:
                CompressFileGDB_FC (myFC)
                myFC = fcs.Next()
            fd = fds.Next()   
    else:
        if (string.find (FeatureData,".gdb")) <= 0:
            raise Exception, msgNotFileGDB
        desc = gp.describe(FeatureData)
        if desc.DatasetType == "FeatureClass":
            CompressFileGDB_FC (FeatureData)
        elif desc.DatasetType == "FeatureDataset":
            gp.AddMessage (msgCompressingFeatureDataset)
            gp.Workspace = FeatureData
            fcs = gp.ListFeatureClasses()
            fc = fcs.Next()
            while fc:
                print FeatureData + "/" + fc
                CompressFileGDB_FC (FeatureData + "/" + fc)
                fc = fcs.Next()
        else:
            gp.AddMessage (msgNotSupported)
except Exception, ErrDesc:
    #Add error messages to Geoprocessing window
    gp.AddError(str(ErrDesc))

gp = None
#--------------------------------------------------------------------------
