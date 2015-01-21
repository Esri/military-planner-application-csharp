"""
Tool Name:  Standard Distance
Source Name: StandardDistance.py
Version: ArcGIS 10.1
Author: ESRI

This tool measures the degree to which features are concentrated or 
dispersed around the mean center in an input feature class.
May be based on an optional weight (to get the
standard distance of businesses weighted by employees, for example) or
may optionally be grouped into cases.  The standard distance is a useful
statistic; it provides a single summary measure of feature distributions
around any given point (similar to the way a standard deviation measures
the distribution of data values around the statistical mean).
"""

################### Imports ########################
import os as OS
import collections as COLL
import numpy as NUM
import math as MATH
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSTimeUtilities as TUTILS
import SSDataObject as SSDO
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

circleDict = {"1_STANDARD_DEVIATION": 1.0, 
              "2_STANDARD_DEVIATIONS": 2.0,
              "3_STANDARD_DEVIATIONS": 3.0}

################ Output Field Names #################
sdFieldNames = ["CenterX", "CenterY", "StdDist"]

################### GUI Interface ###################

def setupStandardDistance():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)
    outputFC = ARCPY.GetParameterAsText(1)
    stdDeviations = ARCPY.GetParameterAsText(2).upper().replace(" ", "_")  
    weightField = UTILS.getTextParameter(3, fieldName = True)
    caseField = UTILS.getTextParameter(4, fieldName = True)           

    fieldList = []
    if weightField:
        fieldList.append(weightField)
    if caseField:
        fieldList.append(caseField)

    stdDeviations = circleDict[stdDeviations]

    #### Create a Spatial Stats Data Object (SSDO) ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = outputFC,
                             useChordal = False)

    #### Populate SSDO with Data ####
    ssdo.obtainData(ssdo.oidName, fieldList, minNumObs = 2, dateStr = True) 

    #### Run Analysis ####
    sd = StandardDistance(ssdo, weightField = weightField,
                          caseField = caseField, 
                          stdDeviations = stdDeviations)
    
    #### Create Output ####
    sd.createOutput(outputFC)

class StandardDistance(object):
    """This tool identifies the geographic center (or the center of
    concentration) for a set of features and calculates a circle with a
    based on the given standard deviations. 

    INPUTS: 
    ssdo (obj): instance of SSDataObject
    weightField {str, None}: name of weight field
    caseField {str, None} name of case field
    stdDeviations {float, 1.0}: number of standard devs around center

    ATTRIBUTES:
    meanCenter (dict): [case field value] = mean center (1)
    sd (dict): [case field value] = standard distance (1)
    badCases (list): list of cases that were unsuccessful.
    ssdo (class): instance of SSDataObject
    caseKeys (list): sorted list of all cases for print/output

    METHODS:
    createOutput: creates a feature class with standard distances.
    report: reports results as a printed message or to a file

    NOTES:
    (1)  The key for the mean center dicts is "ALL" if no case field is
         provided
    """

    def __init__(self, ssdo, weightField = None, caseField = None, 
                 stdDeviations = 1.0):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())

        #### Set Data ####
        self.xyCoords = self.ssdo.xyCoords

        #### Verify Weights ####
        if weightField:
            self.weights = self.ssdo.fields[weightField].returnDouble()

            #### Report Negative Weights ####
            lessThanZero = NUM.where(self.weights < 0.0)
            if len(lessThanZero[0]):
                self.weights[lessThanZero] = 0.0
                ARCPY.AddIDMessage("Warning", 941)

            #### Verify Weight Sum ####
            self.weightSum = self.weights.sum()
            if not self.weightSum > 0.0: 
                ARCPY.AddIDMessage("ERROR", 898)
                raise SystemExit()
        else:
            self.weights = NUM.ones((self.ssdo.numObs,))

        #### Set Case Field ####
        if caseField:
            caseType = ssdo.allFields[caseField].type.upper()
            self.caseIsString = caseType == "STRING"
            self.caseVals = self.ssdo.fields[caseField].data
            cases = NUM.unique(self.caseVals)
            if self.caseIsString:
                self.uniqueCases = cases[NUM.where(cases != "")]
            else:
                self.uniqueCases = cases
        else:
            self.caseIsString = False
            self.caseVals = NUM.ones((self.ssdo.numObs, ), int)
            self.uniqueCases = [1]

        #### Set Result Dict ####
        meanCenter = COLL.defaultdict(NUM.array)
        sd = COLL.defaultdict(float)

        #### Keep Track of Bad Cases ####
        badCases = []

        #### Calculate Mean Center and Standard Distance ####
        for case in self.uniqueCases:
            indices = NUM.where(self.caseVals == case)
            numFeatures = len(indices[0])
            xy = self.xyCoords[indices]
            w = self.weights[indices]
            w.shape = numFeatures, 1
            weightSum = w.sum()
            if (weightSum != 0.0) and (numFeatures > 2):
                xyWeighted = w * xy

                #### Mean Center ####
                centers = xyWeighted.sum(0) / weightSum
                meanCenter[case] = centers

                #### Standard Distance ####
                devXY = xy - centers
                sigXY = (w * devXY**2.0).sum(0)/weightSum 
                sdVal = (MATH.sqrt(sigXY.sum())) * stdDeviations
                sd[case] = sdVal
            else:
                badCases.append(case)
                
        #### Report Bad Cases ####
        nCases = len(self.uniqueCases)
        nBadCases = len(badCases) 
        badCases.sort()
        if nBadCases:
            cBool = self.caseIsString
            if not self.caseIsString:
                badCases = [UTILS.caseValue2Print(i, cBool) for i in badCases]
            ERROR.reportBadCases(nCases, nBadCases, badCases, 
                                 label = caseField)   
        
        #### Sorted Case List ####
        caseKeys = sd.keys()
        caseKeys.sort()
        self.caseKeys = caseKeys

        #### Set Attributes ####
        self.meanCenter = meanCenter
        self.sd = sd
        self.badCases = badCases
        self.caseField = caseField
        self.stdDeviations = stdDeviations
        self.weightField = weightField

    def report(self, fileName = None):
        """Reports the Standard Distance results as a message or to a file.

        INPUTS:
        fileName {str, None}: path to a text file to populate with results
        """

        header = ARCPY.GetIDMessage(84224)
        columns = [ARCPY.GetIDMessage(84191), ARCPY.GetIDMessage(84211),
                   ARCPY.GetIDMessage(84212), ARCPY.GetIDMessage(84225),
                   ARCPY.GetIDMessage(84226)]
        results = [columns]
        for case in self.uniqueCases:
            if not self.caseField:
                strCase = "ALL"
            else:
                strCase = UTILS.caseValue2Print(case, self.caseIsString)
            meanX, meanY = self.meanCenter[case]
            rowResult = [ strCase, LOCALE.format("%0.6f", meanX),
                          LOCALE.format("%0.6f", meanY),
                          LOCALE.format("%0.6f", self.sd[case]),
                          LOCALE.format("%0.1f", self.stdDeviations) ]
            results.append(rowResult)

        outputTable = UTILS.outputTextTable(results, header = header)
        if fileName:
            f = UTILS.openFile(fileName, "w")
            f.write(outputTable)
            f.close()
        else:
            ARCPY.AddMessage(outputTable)

    def createOutput(self, outputFC):
        """Creates an Output Feature Class with the Standard Distances.

        INPUTS:
        outputFC (str): path to the output feature class
        """

        #### Validate Output Workspace ####
        ERROR.checkOutputPath(outputFC)

        #### Shorthand Attributes ####
        ssdo = self.ssdo
        caseField = self.caseField

        #### Increase Extent if not Projected ####
        if ssdo.spatialRefType != "Projected":
            sdValues = self.sd.values()
            if len(sdValues):
                maxRadius = max(sdValues)
                largerExtent = UTILS.increaseExtentByConstant(ssdo.extent, 
                                                    constant = maxRadius)
                largerExtent = [ LOCALE.str(i) for i in largerExtent ]
                ARCPY.env.XYDomain = " ".join(largerExtent)

        #### Create Output Feature Class ####
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84003))
        outPath, outName = OS.path.split(outputFC)

        try:
            DM.CreateFeatureclass(outPath, outName, "POLYGON", 
                                  "", ssdo.mFlag, ssdo.zFlag, 
                                  ssdo.spatialRefString)
        except:
            ARCPY.AddIDMessage("ERROR", 210, outputFC)
            raise SystemExit()

        #### Add Fields to Output FC ####
        dataFieldNames = UTILS.getFieldNames(sdFieldNames, outPath)
        shapeFieldNames = ["SHAPE@"]
        for fieldName in dataFieldNames:
            UTILS.addEmptyField(outputFC, fieldName, "DOUBLE")

        caseIsDate = False
        if caseField:
            fcCaseField = ssdo.allFields[caseField]
            validCaseName = UTILS.validQFieldName(fcCaseField, outPath)
            caseType = UTILS.convertType[fcCaseField.type]
            UTILS.addEmptyField(outputFC, validCaseName, caseType)
            dataFieldNames.append(validCaseName)
            if caseType.upper() == "DATE":
                caseIsDate = True

        #### Write Output ####
        badCaseRadians = []
        allFieldNames = shapeFieldNames + dataFieldNames
        rows = DA.InsertCursor(outputFC, allFieldNames)
        for case in self.caseKeys:

            #### Get Results ####
            xVal, yVal = self.meanCenter[case]
            radius = self.sd[case]

            #### Create Empty Polygon Geomretry ####
            poly = ARCPY.Array()

            #### Check for Valid Radius ####
            radiusZero = UTILS.compareFloat(0.0, radius, rTol = .0000001)
            radiusNan = NUM.isnan(radius)
            radiusBool = radiusZero + radiusNan
            if radiusBool:
                badRadian = 6
                badCase = UTILS.caseValue2Print(case, self.caseIsString)
                badCaseRadians.append(badCase)
            else:
                badRadian = 0

                #### Calculate a Point For Each ####
                #### Degree in Circle Polygon ####
                for degree in NUM.arange(0, 360):  
                    try:
                        radians = NUM.pi / 180.0 * degree
                        pntX = xVal + (radius * NUM.cos(radians))
                        pntY = yVal + (radius * NUM.sin(radians))
                        pnt = ARCPY.Point(pntX, pntY, ssdo.defaultZ)
                        poly.add(pnt)
                    except:
                        badRadian += 1
                        if badRadian == 6:
                            badCase = UTILS.caseValue2Print(case, 
                                               self.caseIsString)
                            badCaseRadians.append(badCase)
                            break

            if badRadian < 6:
                #### Create and Populate New Feature ####
                poly = ARCPY.Polygon(poly, None, True)
                rowResult = [poly, xVal, yVal, radius]

                if caseField:
                    caseValue = case.item()
                    if caseIsDate:
                        caseValue = TUTILS.iso2DateTime(caseValue)
                    rowResult.append(caseValue)
                rows.insertRow(rowResult)

        #### Report Bad Cases Due to Geometry (coincident pts) ####
        nBadRadians = len(badCaseRadians)
        if nBadRadians:
            if caseField:
                badCaseRadians = " ".join(badCaseRadians)
                ARCPY.AddIDMessage("WARNING", 1011, caseField,
                                badCaseRadians)
            else:
                ARCPY.AddIDMessage("ERROR", 978)
                raise SystemExit()

        #### Return Extent to Normal if not Projected ####
        if ssdo.spatialRefType != "Projected":
            ARCPY.env.XYDomain = None

        #### Clean Up ####
        del rows

        #### Set Attribute ####
        self.outputFC = outputFC
            
if __name__ == "__main__":
    setupStandardDistance()
