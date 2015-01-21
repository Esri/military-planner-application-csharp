"""****************************************************************************
ConversionUtils.py
Version: ArcGIS 10.1

Description: This module provides functions and the geoprocessor which is used
by both the FeatureclassConversion.py and TableConversion.py modules.

Author: ESRI, Redlands
****************************************************************************"""

#Importing standard library modules
import arcgisscripting
import os
import string
import re

#Create the geoprocessing objectf
gp = arcgisscripting.create(9.3)

#Define message constants so they may be translated easily
msgErrorGenOutput = gp.GetIDMessage(86123)#"Problem generating Output Name"
msgErrorGenOutputRaster = gp.GetIDMessage(86124)#"Problem generating Output Raster Name"
msgErrorSplittingInput = gp.GetIDMessage(86125)#"Problem encountered parse input list"
msgErrorValidateInputRaster = gp.GetIDMessage(86126)#"Problem encountered validate input raster"

################## Classes ##########################
class GPError(Exception):
    """
    INPUTS:
    value (str): error message to be delivered.

    METHODS:
    __str__: returns error message for printing.
    """
    def __init__(self, value="Error occurred. Exiting ..."):
        self.value = value

    def __str__(self):
        return self.value

################## Methods ##########################

def ExceptionMessages(msgWarning, msgStr, ErrDesc):
    if msgStr != "":
        msgWarning = msgWarning + ". " + msgStr
    elif str(ErrDesc) != "":
        msgWarning = msgWarning + ". " + str(ErrDesc)
    return msgWarning

#Generates a valid output feature class or table name based on the input and destination
def GenerateOutputName(inName, outWorkspace, beforeVSafter="before"):
    try:
        #Describe the FeatureClass to determine it's type (shp, cov fc, gdb fc, etc...)
        dsc = gp.Describe(inName)

        #Extract the basename for the input fc from the path (ie. the input feature class or table name)
        #Get the path to the input feature class (basically the fc container). This could be a dataset, coverage, geodatabase, etc...
        if hasattr(dsc, "namestring"):
            outName = dsc.namestring
            inContainer = os.path.dirname(inName)
        else:
            outName = dsc.name
            inContainer = dsc.path

        if inContainer:
            #Extract the basename for the fc container (ie. the geodatabase name, or feature dataset name)
            #This will be used in certain cases to generate the output name
            inContainerName = os.path.basename(inContainer)   #Full path excluding the featureclass. D:\Data\redlands.mdb\city

            #Describe the type of the Feature class container (cov, gdb, vpf, etc...)
            dscInContainer = gp.Describe(inContainer)

            #If the input fc is a feature dataset (Coverage, CAD or VPF), then set the output name to be a
            # combination of the input feature dataset and feature class name. For example if the input
            # is "c:\gdb.mdb\fds\fc" the name for the output feature class would be "fds_fc"
            if dsc.DataType == "CoverageFeatureClass" or \
                dscInContainer.DataType in ["VPFCoverage", "CadDrawingDataset", "RasterDataset"]:
                outName = inContainerName + "_" + outName

            #If the input is a shapefile, txt or dbf, do not include the extention (".shp", ".dbf", ".txt") as part of the output name
            # Do this everytime since the output could may or may not be a geodatabase feature class or table
            elif dsc.DataType in ["DbaseTable", "ShapeFile", "TextFile"]:
                outName = os.path.splitext(outName)[0]

        #The next 3 steps (get rid of invalid chars, add extention (if the output will have one), and generate a unique name)

        # If output workspace is a folder, the output is either a shp file or a dbase table, so determine
        # if the output name need to add .shp or .dbf extention to the output
        desOutWorkspace = gp.Describe(outWorkspace)

        #Check for ArcSDE and remove database and username
        if re.findall('.sde|.sqlite', inName):
            if outName.find(":") > -1:
                outNameTemp = outName.split(":")
                outName = outNameTemp[len(outNameTemp) - 1]

            outNameTemp = outName.split(".")
            outName = outNameTemp[len(outNameTemp) - 1]

        if desOutWorkspace.DataType == "Folder":
            if (dsc.DatasetType == "FeatureClass") and (not outName.lower().endswith(".shp")):
                outName = outName.replace(":","_").replace(".","_") + ".shp"
            elif (dsc.DatasetType == "Table") and (not outName.lower().endswith(".dbf")):
                outName = outName.replace(":","_").replace(".","_") + ".dbf"
            #pass
        # If the output location is a Geodatabase (SDE or Personal) we can use gp.ValidateTableName to generate
        # a valid name for the output table or feature class.

        elif desOutWorkspace.DataType == "Workspace" :
            try:
                outName = gp.ValidateTableName(outName, outWorkspace)
            except:
                pass

        elif desOutWorkspace.DataType == "FeatureDataset":
            try:
                outName = gp.ValidateTableName(outName, os.path.dirname(outWorkspace))
            except:
                pass

        # Check if the name which has been generated so far already exist, if yes, create a unique one
        # ValidateTableName will return something unique for that workspace (not yet though) so
        # this (eventully) should move into the >if desOutWorkspace.DataType == "Folder"< block
        outName = GenerateUniqueName(outName, outWorkspace)

        #Return the name full path to the name which was generated

        return outWorkspace + os.sep + outName

    except Exception, ErrorDesc:
        ErrorDesc0 = ErrorDesc
        ErrorDesc = ""
        for sErr in ErrorDesc0:
            ErrorDesc = ErrorDesc + sErr
        raise Exception, "%s (%s)" % (msgErrorGenOutput, ErrorDesc) ##str(ErrorDesc))

#Generate a valid output raster dataset name with extension
def GenerateRasterName(inName, outWorkspace, ext):
    try:
        #Extract the basename for the input raster dataset
        outName = os.path.basename(inName)

        #Get the path to the input dataset. This could be a raster catalog or workspace.
        inContainer = os.path.dirname(inName)   #Full path excluding the raster dataset
        des=gp.Describe(inContainer)
        if (des.DataType == "RasterCatalog"): #rastercatalog
            outName=os.path.basename(inContainer) #use raster catalog name as basename
        elif (des.WorkspaceType =="FileSystem"): #file with extension
            ids = outName.find(".")
            if (ids > -1):
                outName = outName[:ids]

        # for ArcSDE
        outName.replace(":",".")
        ids = outName.rfind(".")
        if (ids > -1):
            outName = outName[(ids+1):]

        desOutWorkspace = gp.Describe(outWorkspace) #workspace
        if (desOutWorkspace.DataType == "RasterCatalog"):
            return outWorkspace

        # If the output location is a Geodatabase (SDE or Personal) we can use gp.ValidateTableName to generate
        # a valid name for the output table or feature class.
        if desOutWorkspace.DataType == "Workspace":
            try:
                outName = gp.ValidateTableName(outName, outWorkspace)
            except:
                pass

        if (desOutWorkspace.WorkspaceType == "FileSystem"): #filesystem
            outName = outName + ext
            if (ext == ""): #Grid format, make sure the filename is 8.3 standard
                grdlen = len(outName)
                if (grdlen > 12):
                    outName = outName[:8]
        else:
            outName = gp.QualifyTableName(outName,outWorkspace)

        outName = GenerateUniqueName(outName, outWorkspace)

        return outWorkspace + os.sep + outName

    except Exception, ErrorDesc:
        ErrorDesc0 = ErrorDesc
        ErrorDesc = ""
        for sErr in ErrorDesc0:
            ErrorDesc = ErrorDesc + sErr
        raise Exception, "%s (%s)" % (msgErrorGenOutputRaster, ErrorDesc) ##str(ErrorDesc))

def Exists(workspace, name):
    """Check if the data exists and if in a FeatureDataset check the workspace
    below"""
    exists = gp.Exists(os.path.join(workspace, name))
    if not exists and gp.Describe(workspace).datatype == 'FeatureDataset':
        exists = gp.Exists(os.path.join(os.path.dirname(workspace), name))

    return exists

def GenerateUniqueName(name, workspace):
    """Generates a unique name. If the name already exists, adds "_1" at
    the end, if that exists, adds "_2", and so on..."""

    # Watch for sllite and prefix it with 'main.' if necessary
    if os.path.splitext(workspace)[1] == '.sqlite':
        if not name.startswith('main'):
            name = u'main.{}'.format(name)

    if Exists(workspace, name):
        extension = ''
        if os.path.splitext(name)[1] in ('.shp', '.dbf', '.img', '.tif'):
            name, extension = os.path.splitext(name)

        i = 1
        while Exists(workspace, u'{}_{}{}'.format(name, i, extension)):
            i += 1
        return u'{}_{}{}'.format(name, i, extension)
    else:
        return name

#Split the semi-colon (;) delimited input string (tables or feature classes) into a list
def SplitMultiInputs(multiInputs):
    try:
        # Remove the single quotes and parenthesis around each input featureclass
        # Changed at June 2007, instead of replace "(" and ")" with "", just strip them if they're first or last character in multiInputs
        multiInputs = multiInputs.replace("'","")
        if multiInputs.startswith("("):
            multiInputs = multiInputs[1:]
        if multiInputs.endswith(")"):
            multiInputs = multiInputs[:-1]

        #split input tables by semicolon ";"
        return multiInputs.split(";")
    except:
        raise Exception, msgErrorSplittingInput

#Copy the contents (features) of the input feature class to the output feature class
def CopyFeatures(inFeatures, outFeatureClass):
    try:
        gp.CopyFeatures_management(inFeatures, outFeatureClass)
    except:
        raise Exception, gp.GetMessages(2).replace("\n"," ")

#Copy the contents (rasters) of the input raster dataset to the output raster dataset
def CopyRasters(inRasters, outRasters, keyword):
    try:
        gp.CopyRaster_management(inRasters, outRasters, keyword)
    except:
        raise Exception, gp.GetMessages(2).replace("\n"," ")

#Copy the contents (rows) of the input table to the output table
def CopyRows(inTable, outTable):
    try:
        gp.CopyRows_management(inTable, outTable)
    except:
        raise Exception, gp.GetMessages(2).replace("\n"," ")

def ValidateInputRaster(inName):
    try:
        if inName.startswith("'") and inName.endswith("'"):
            inName = inName[1:-1]
        return inName

    except:
        raise Exception, msgErrorValidateInputRaster
