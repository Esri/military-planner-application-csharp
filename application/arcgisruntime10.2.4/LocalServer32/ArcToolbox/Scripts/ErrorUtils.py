"""
Source Name:   ErrorUtils.py
Version:       ArcGIS 10.1
Author:        Environmental Systems Research Institute Inc.
Description:   Error Handling Functions for ESRI Script Tools.
"""

################### Imports ########################

import arcpy as ARCPY
import os as OS

########## Error Dictionary Structures ###############

data2Type = { 'SmallInteger': 0, 'Integer': 1,
              'Single': 2, 'Double': 3,
              'String': 4, 'OID': 5,
              'Date': 6, 'Geometry': 7}

type2Data = { 0: 'SmallInteger', 1: 'Integer',
              2: 'Single', 3: 'Double',
              4: 'String', 5: 'OID',
              6: 'Date', 7: 'Geometry'}

################## Classes ##########################

class ScriptError(Exception):
    """Send an error message to the application history window.  
    Inherits from the Python Exception Class.  
    See: www.python.org/doc/current/tut/node10.html for more
    information about custom exceptions.

    INPUTS:
    value {str, None}: error message to be delivered

    METHODS:
    __str__: returns error message for printing
    """

    def __init__(self, value = None):
        if value == None:
            value = ARCPY.GetIDMessage(84004)
        self.value = value

    def __str__(self):
        return self.value
        
################# Methods ########################

def reportBadRecords(numObs, numBadObs, badIDs, label = "OID", 
                     allowNULLs = False, explicitBadRecordID = None):
    """Formats a string that notifies the user of the records it had
    trouble reading.  It only reports the first 30 bad records. 

    INPUTS: 
    numObs (int): total number of records
    numBadObs (int): number of bad records
    badIDs (list): list of all bad record IDs
    label {str, OID}: the master field that corresponds to badIds
    allowNULLs {bool, False}: allow NULL values in analysis?
    """

    ARCPY.AddIDMessage("WARNING", 642, numBadObs, numObs)
    if len(badIDs) > 30:
        badIDs = badIDs[0:30]
    badIDs = ", ".join(badIDs)
    if allowNULLs:
        ARCPY.AddIDMessage("WARNING", 1158, label, badIDs)
    else:
        if explicitBadRecordID != None:
            ARCPY.AddIDMessage("WARNING", explicitBadRecordID, 
                               label, badIDs)
        else:
            ARCPY.AddIDMessage("WARNING", 848, label, badIDs)

def reportBadCases(numCases, numBadCases, badCases, label = "CASE"):
    """Formats a string that notifies the user of the cases with not
    enough observations to be included.  It only reports the first 
    30 bad cases. 

    INPUTS: 
    numCases (int): total number of cases
    numBadCases (int): number of bad cases
    badCases (list): list of all bad cases
    label {str, CASE}: the case field that corresponds to badCases
    """

    #### Fail If No Valid Cases ####
    if numCases == numBadCases:
        ARCPY.AddIDMessage("ERROR", 978)
        raise SystemExit()

    ARCPY.AddIDMessage("WARNING", 910, numBadCases, numCases)

    if len(badCases) > 30:
        badCases = badCases[0:30]
    badCases = ", ".join(badCases)
    ARCPY.AddIDMessage("WARNING", 947, label, badCases)

def reportBadLengths(numObs, numBadObs, badLengths, label = "OID"):
    """Formats a string that notifies the user of the line records with
    the same start and end points.  It only reports the first 30 bad records. 

    INPUTS: 
    numObs (int): total number of records
    numBadObs (int): number of line records with no length
    badLengths (list): list of all line record IDs with no length
    label {str, OID}: the master field that corresponds to badLengths
    """

    ARCPY.AddIDMessage("WARNING", 911, numBadObs, numObs)
    if len(badLengths) > 30:
        badLengths = badLengths[0:30]
    badLengths = ", ".join(badLengths)
    ARCPY.AddIDMessage("WARNING", 912, label, badLengths)

def errorNumberOfObs(numObs, minNumObs = 3):
    """Returns an error if the number of observations is less than a specified
    integer.

    INPUTS: 
    numObs (int): number of observations
    minNumObs {int, 3}: minimum number of observations
    """

    if numObs < minNumObs:
        ARCPY.AddIDMessage("ERROR", 641, minNumObs)
        raise SystemExit()

def checkNumberOfObs(numObs, minNumObs = 3, warnNumObs = 30, 
                     silentWarnings = False):
    """Returns a error/warning if the number of observations is less than a 
    specified integer.

    INPUTS: 
    numObs (int): number of observations
    minNumObs {int, 3}: minimum number of observations for error
    warnNumObs {int, 30}: minimum number of observations for warning
    """

    errorNumberOfObs(numObs, minNumObs = minNumObs)
    if numObs < warnNumObs and not silentWarnings:
        ARCPY.AddIDMessage("WARNING", 845, warnNumObs)

def warningNoNeighbors(numObs, numObsNoNeighs, idsNoNeighs, 
                       masterField, forceNeighbor = False,
                       contiguity = False):
    """Returns warning messages for observations with no neighbors.

    INPUTS:
    numObs (int): total number of observations
    numObsNoNeighs (int): number of observations with no neighbors
    idsNoNeighs (list): ids with no neighbors
    masterField (str): name of the unique ID field
    forceNeighbor {boolean, False}: method used assured at least one neighbor?
    contiguity {boolean, False}: input feature class comprised of polygons?
    """

    idsNoNeighs = [ str(i) for i in idsNoNeighs ]
    idsNoNeighs = ", ".join(idsNoNeighs)
    if forceNeighbor:
        if contiguity:
            ARCPY.AddIDMessage("Warning", 718, numObsNoNeighs)
        else:
            ARCPY.AddIDMessage("Warning", 715, numObsNoNeighs)
        ARCPY.AddIDMessage("Warning", 716, masterField, idsNoNeighs)
    else:
        ARCPY.AddIDMessage("Warning", 846, numObsNoNeighs)
        ARCPY.AddIDMessage("Warning", 847, masterField, idsNoNeighs)

def returnFieldTypes(fieldTypes):
    """Returns a string of field types to be printed in an error statement.

    INPUTS: 
    fieldTypes (list): list of integers which are keys in type2Data

    OUTPUT:
    stringTypes (str): string of data types to be printed in error
    """

    stringTypes = [ type2Data[i] for i in fieldTypes ]
    stringTypes = ", ".join(stringTypes)
    stringTypes = "{" + stringTypes + "}"
    return stringTypes 

def checkFC(inputFC):
    """Assesses whether a feature class exists and returns an appropriate
    error message if it does not.

    INPUTS:
    inputFC (str): catalogue path to the input feature class.
    """

    if not ARCPY.Exists(inputFC):
        ARCPY.AddIDMessage("ERROR", 110, inputFC)
        raise SystemExit()

def checkOutputPath(fullOutputPath):
    """Assesses whether a workspace exists for the given path and returns 
    an appropriate error message if it does not.

    INPUTS:
    fullOutputPath (str): catalogue path to the output data element.
    """

    outPath, outName = OS.path.split(fullOutputPath)
    if not ARCPY.Exists(outPath):
        ARCPY.AddIDMessage("ERROR", 210, fullOutputPath)
        raise SystemExit()
        
def checkField(allFields, fieldName, types = []):
    """Checks whether a field exists and whether it conforms to the specified
    type(s).

    INPUTS:
    allFields (dict): field name = field type
    fieldName (str): name of the field to check
    types {list, []}: list of allowed data types for the field in question.
    """
    
    #### Upper Case the FieldName ####
    fieldNameUp = fieldName.upper()

    #### Make Sure Field Exists ####
    try:
        type = allFields[fieldNameUp].type
    except:
        ARCPY.AddIDMessage("ERROR", 728, fieldName)
        raise SystemExit()

    #### Make Sure Data Type Exists ####
    try:
        dataType = data2Type[type]
    except:
        ARCPY.AddIDMessage("Error", 724)
        raise SystemExit()

    #### Make Sure Data Type is Appropriate ####
    if dataType not in types:
        typeString = returnFieldTypes(types)
        ARCPY.AddIDMessage("ERROR", 640, fieldName, typeString)
        raise SystemExit()

    return type


