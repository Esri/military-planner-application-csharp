"""
Tool Name:  Collect Events
Source Name: CollectEvents.py
Version: ArcGIS 10.1
Author: ESRI

This utility converts event data into weighted point data.
"""

################### Imports ########################

import os as OS
import sys as SYS
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO 
import gapy as GAPY
import WeightsUtilities as WU

################ Output Field Names #################
countFieldName = "ICOUNT"

################### GUI Interface ###################

def setupCollectEvents():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)
    outputFC = ARCPY.GetParameterAsText(1)

    #### Create SSDataObject ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = outputFC)

    countFieldNameOut, maxCount, N, numUnique = collectEvents(ssdo, outputFC)
    setDerivedOutput(countFieldNameOut, maxCount)
    renderResults()

def setDerivedOutput(countFieldNameOut, maxCount):
    #### Set Derived Output ####
    try:
        ARCPY.SetParameterAsText(2, countFieldNameOut)
        maxCount = maxCount * 1.0
        ARCPY.SetParameterAsText(3, maxCount)
    except:
        ARCPY.AddIDMessage("WARNING", 902)

def renderResults():
    #### Set the Default Symbology ####
    params = ARCPY.gp.GetParameterInfo()
    renderLayerFile = "\\templates\\layers\\CollectEventsRenderer.lyr"
    templateDir = OS.path.dirname(OS.path.dirname(SYS.argv[0]))
    params[1].Symbology = templateDir + renderLayerFile

def collectEvents(ssdo, outputFC):
    """This utility converts event data into weighted point data by
    dissolving all coincident points into unique points with a new count
    field that contains the number of original features at that
    location.

    INPUTS: 
    inputFC (str): path to the input feature class
    outputFC (str): path to the input feature class
    """

    #### Set Default Progressor for Neigborhood Structure ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84143))

    #### Validate Output Workspace ####
    ERROR.checkOutputPath(outputFC)

    #### True Centroid Warning For Non-Point FCs ####
    if ssdo.shapeType.upper() != "POINT":
        ARCPY.AddIDMessage("WARNING", 1021)

    #### Create GA Data Structure ####
    gaTable, gaInfo = WU.gaTable(ssdo.inputFC, spatRef = ssdo.spatialRefString)

    #### Assure Enough Observations ####
    cnt = UTILS.getCount(ssdo.inputFC)
    ERROR.errorNumberOfObs(cnt, minNumObs = 4)
    N = gaInfo[0]
    ERROR.errorNumberOfObs(N, minNumObs = 4)

    #### Process Any Bad Records Encountered ####
    numBadRecs = cnt - N
    if numBadRecs:
        badRecs = WU.parseGAWarnings(gaTable.warnings)
        if not ssdo.silentWarnings:
            ERROR.reportBadRecords(cnt, numBadRecs, badRecs,
                                   label = ssdo.oidName)

    #### Create k-Nearest Neighbor Search Type ####
    gaSearch = GAPY.ga_nsearch(gaTable)
    gaSearch.init_nearest(0.0, 0, "euclidean")

    #### Create Output Feature Class ####
    outPath, outName = OS.path.split(outputFC)
    try:
        DM.CreateFeatureclass(outPath, outName, "POINT", "", ssdo.mFlag, 
                              ssdo.zFlag, ssdo.spatialRefString)
    except:
        ARCPY.AddIDMessage("ERROR", 210, outputFC)
        raise SystemExit()

    #### Add Count Field ####
    countFieldNameOut = ARCPY.ValidateFieldName(countFieldName, outPath)
    UTILS.addEmptyField(outputFC, countFieldNameOut, "LONG")
    fieldList = ["SHAPE@", countFieldNameOut]

    #### Set Insert Cursor ####
    rowsOut = DA.InsertCursor(outputFC, fieldList)

    #### Set Progressor for Calculation ####
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84007), 0, N, 1)

    #### ID List to Search ####
    rowsIN = range(N)
    maxCount = 0
    numUnique = 0

    for row in rowsIN:
        #### Get Row Coords ####
        rowInfo = gaTable[row]
        x0, y0 = rowInfo[1]
        count = 1

        #### Search For Exact Coord Match ####
        gaSearch.search_by_idx(row)
        for nh in gaSearch:
            count += 1
            rowsIN.remove(nh.idx)
            ARCPY.SetProgressorPosition()

        #### Keep Track of Max Count ####
        maxCount = max([count, maxCount])
        
        #### Create Output Point ####
        pnt = (x0, y0, ssdo.defaultZ)

        #### Create and Populate New Feature ####
        rowResult = [pnt, count]
        rowsOut.insertRow(rowResult)
        numUnique += 1
        ARCPY.SetProgressorPosition()
    
    #### Clean Up ####
    del rowsOut, gaTable

    return countFieldNameOut, maxCount, N, numUnique
        
if __name__ == "__main__":
    setupCollectEvents()
