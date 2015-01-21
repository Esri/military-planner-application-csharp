"""
Tool Name:  Export XYv
Source Name: ExportXYv.py
Version: ArcGIS 10.0
Author: ESRI

This script will create a space, comma, or semi-colon delimited X Y V ascii 
text file, where V is some attribute value(s) in the specified feature class 
table.
"""

################ Imports ####################
import sys as SYS
import os as OS
import arcpy as ARCPY
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

delimDict = {"SPACE": " ", "COMMA": ",", "SEMI-COLON": ";"}

################ Output Field Names #################
exyvFieldNames = ["XCoord", "YCoord"]

################### GUI Interface ###################
def setupXYV():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    #### Get User Provided Inputs ####
    inputFC = ARCPY.GetParameterAsText(0)      
    outFields = ARCPY.GetParameterAsText(1).upper()                       
    fieldList = outFields.split(";")
    delimiter = ARCPY.GetParameterAsText(2).upper().replace(" ", "_")                     
    outFile = ARCPY.GetParameterAsText(3)     
    outFieldNames = ARCPY.GetParameter(4)

    #### Set Delimiter ####
    try:
        delimiter = delimDict[delimiter]
    except:
        delimiter = " "

    #### Execute Function ####
    exportXYV(inputFC, fieldList, delimiter, outFile, 
              outFieldNames = outFieldNames)

def exportXYV(inputFC, fieldList, delimiter, outFile, outFieldNames = False):
    """Exports the X,Y Coords and Set of Field Values for a Given
    Feature Class.

    INPUTS:
    inputFC (str): path to the input feature class
    fieldList (list): list of field names to export
    delimiter (str): token to delimit output file with
    outFile (str): path to the output text file
    outFieldNames (bool): return field names in first row of text file?

    OUTPUT:
    outFile (file): output text file
    """

    #### Get Feature Class Properties ####
    ssdo = SSDO.SSDataObject(inputFC, useChordal = False)
    inputFields = [ssdo.oidName, "SHAPE@XY"] + fieldList 

    #### Create Progressor Bar ####
    cnt = UTILS.getCount(inputFC)
    ARCPY.AddMessage(ARCPY.GetIDMessage(84012))
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84012), 0, cnt, 1)

    #### Keep track of Invalid Fields ####
    badIDs = []
    badRecord = 0

    #### Process Field Values ####
    try:
        rows = DA.SearchCursor(ssdo.inputFC, inputFields, "", 
                               ssdo.spatialRefString)
    except:
        ARCPY.AddIDMessage("ERROR", 204)
        raise SystemExit()

    #### Get Field Types and Set LOCALE Dictionary ####
    floatTypes = ["Single", "Double"]
    localeDict = {}
    for field in fieldList:
        fieldType = ssdo.allFields[field].type
        if fieldType in floatTypes:
            formatToken = "%f"
        else:
            formatToken = "%s"
        localeDict[field] = formatToken

    #### Create Output File ####
    fo = UTILS.openFile(outFile, 'w')

    #### Write Field Names to File ####
    if outFieldNames:
        outPath, outName = OS.path.split(outFile)
        allFieldNames = UTILS.getFieldNames(exyvFieldNames, outPath)
        allFieldNames += fieldList
        outRow = delimiter.join(allFieldNames)
        fo.write("%s\n" % outRow.encode('utf-8'))

    for row in rows:
        OID = row[0]
        badValues = row.count(None)
        badXY = row[1].count(None)
        badRow = badValues or badXY
        if not badXY:
            xCoord, yCoord = row[1]
            x = LOCALE.format("%0.8f", xCoord)
            y = LOCALE.format("%0.8f", yCoord)
        else:
            x = "NULL"
            y = "NULL"

        #### Check to see whether field values are OK ####
        rowValues = [x, y]
        for ind, field in enumerate(fieldList):
            value = row[ind + 2]
            if value == "" or value == None:
                rowValues.append("NULL")
            else:
                formatValue = LOCALE.format(localeDict[field], value)
                rowValues.append(formatValue)

        #### Keep TRack of Bad Records ####
        if badRow:
            badIDs.append(OID)

        #### Continue Based on Whether a Bad Row ####
        outRow = delimiter.join(rowValues)
        fo.write("%s\n" % outRow.encode('utf-8'))

        ARCPY.SetProgressorPosition()

    #### Clean Up ####
    del rows
    fo.close()
    ARCPY.AddMessage(outFile)

    #### Get Set of Bad IDs ####
    badIDs = list(set(badIDs))
    badIDs.sort()
    badIDs = [ str(i) for i in badIDs ]
    
    #### Process any bad records encountered ####
    bn = len(badIDs)
    if bn:
        err = ERROR.reportBadRecords(cnt, bn, badIDs, label=ssdo.oidName,
                                     allowNULLs = True)

if __name__ == '__main__':
    export = setupXYV()
