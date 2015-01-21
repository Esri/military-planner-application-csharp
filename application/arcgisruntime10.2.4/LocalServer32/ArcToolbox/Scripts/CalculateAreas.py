"""
Tool Name:  Calculate Areas
Source Name: CalculateAreas.py
Version: ArcGIS 10.1
Author: ESRI

This script will add or overwrite a field to the input
feature class and populate that field with feature areas. 
"""

################### Imports ########################
import os as OS
import arcpy as ARCPY
import arcpy.management as DM
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO

################ Output Field Names #################
areaFieldName = "F_AREA"

################### GUI Interface ###################

def setupCalcAreas():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)                    
    outputFC = ARCPY.GetParameterAsText(1)

    calculateAreas(inputFC, outputFC)

def calculateAreas(inputFC, outputFC):
    """Creates a new feature class from the input polygon feature class 
    and adds a field that includes the area of the polygons.

    INPUTS:
    inputFC (str): path to the input feature class
    outputFC (str): path to the output feature class
    """

    #### Validate Output Workspace ####
    ERROR.checkOutputPath(outputFC)
    outPath, outName = OS.path.split(outputFC)

    #### Create SSDataObject ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = outputFC,
                             useChordal = False)

    #### Assure Polygon FC ####
    if ssdo.shapeType.lower() != "polygon":
        ARCPY.AddIDMessage("ERROR", 931)
        raise SystemExit()

    #### Check Number of Observations ####
    cnt = UTILS.getCount(inputFC)
    ERROR.errorNumberOfObs(cnt, minNumObs = 1)

    #### Copy Features ####
    try:
        clearCopy = UTILS.clearExtent(DM.CopyFeatures)
        clearCopy(inputFC, outputFC)
    except:
        ARCPY.AddIDMessage("ERROR", 210, outputFC)
        raise SystemExit()

    #### Add Area Field ####
    areaFieldNameOut = ARCPY.ValidateFieldName(areaFieldName, outPath)
    if not ssdo.allFields.has_key(areaFieldNameOut): 
        UTILS.addEmptyField(outputFC, areaFieldNameOut, "DOUBLE")

    #### Calculate Field ####
    clearCalc = UTILS.clearExtent(DM.CalculateField)
    clearCalc(outputFC, areaFieldNameOut, "!shape.area!", "PYTHON_9.3")

if __name__ == "__main__":
    setupCalcAreas()
