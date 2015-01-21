"""
Tool Name:     Convert Spatial Weights Matrix to Table 
Source Name:   SWM2Table.py
Version:       ArcGIS 10.0
Author:        Environmental Systems Research Institute Inc.
Description:   Converts a Spatial Weights Matrix File (*.swm) into a
               database table.
"""

################ Imports ####################
import os as OS
import numpy as NUM
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.da as DA
import SSUtilities as UTILS
import ErrorUtils as ERROR
import WeightsUtilities as WU 

################ Output Field Names #################
swm2TabFieldNames = ["NID", "WEIGHT"]

################### GUI Interface ###################

def dispatchConvertSWM2Table():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    swmFile = ARCPY.GetParameterAsText(0)      
    outputTable = ARCPY.GetParameterAsText(1)
    swm2Table(swmFile, outputTable)

def swm2Table(swmFile, outputTable):
    """Places the spatial relationships contained in a given Spatial
    Weight Matrix File (*.swm) into a given output table.

    INPUTS:
    swmFile (str): Path to the input spatial weight matrix file
    outputTable (str): Path to the output database table
    """

    #### Open Spatial Weights and Obtain Characteristics ####
    swm = WU.SWMReader(swmFile)
    masterField = swm.masterField
    N = swm.numObs
    rowStandard = swm.rowStandard

    #### Allow Overwrite Output ####
    ARCPY.env.overwriteOutput = True

    #### Get Output Table Name With Extension if Appropriate ####
    outputTable, dbf = UTILS.returnTableName(outputTable)

    #### Delete Table If Exists ####
    UTILS.passiveDelete(outputTable)

    #### Create Table ####
    outPath, outName = OS.path.split(outputTable)
    try:
        DM.CreateTable(outPath, outName)
    except:
        ARCPY.AddIDMessage("ERROR", 541)
        raise SystemExit()


    #### Create a List of Required Field Names ####
    fn = UTILS.getFieldNames(swm2TabFieldNames, outPath)
    neighFieldName, weightFieldName = fn
    fieldNames = [masterField, neighFieldName, weightFieldName]
    fieldTypes = ["LONG", "LONG", "DOUBLE"]

    for ind, field in enumerate(fieldNames):
        UTILS.addEmptyField(outputTable, field, fieldTypes[ind])

    #### Create Insert Cursor ####
    try:
        insert = DA.InsertCursor(outputTable, fieldNames)
    except:
        ARCPY.AddIDMessage("ERROR", 204)
        raise SystemExit()

    #### Create Progressor ####
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84117), 0, N, 1)

    #### Process Spatial Weights File and Populate Output Table ####
    try:
        for r in xrange(N):
            info = swm.swm.readEntry()
            masterID, nn, nhs, weights, sumUnstandard = info
            if nn != 0:
                for ind, neigh in enumerate(nhs):
                    row = [masterID, neigh, weights[ind]]
                    insert.insertRow(row)

            ARCPY.SetProgressorPosition()
    except:
        swm.close()
        ARCPY.AddIDMessage("ERROR", 919)
        raise SystemExit()

    #### Clean Up ####
    del insert
    swm.close()

    #### Report if Any Features Have No Neighbors ####
    swm.reportNoNeighbors()

    #### Make Table Visable in TOC if *.dbf Had To Be Added ####
    if dbf:
        ARCPY.SetParameterAsText(1, outputTable)

if __name__ == '__main__':
    dispatchConvertSWM2Table()
