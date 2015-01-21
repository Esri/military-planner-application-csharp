"""
Tool Name:  Directional Trends (Standard Deviational Ellipse)
Source Name: StandardEllipse.py
Version: ArcGIS 10.1
Author: ESRI

This tool measures whether a distribution of features exhibits a
directional trend (that is, whether features are farther from
a specified center point in one direction than in another).  The
user may specify an optional weight field and/or an optional
case field.
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
seFieldNames = ["CenterX", "CenterY", "XStdDist", "YStdDist", "Rotation"]

################### GUI Interface ###################

def setupStandardEllipse():
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
    ssdo.obtainData(ssdo.oidName, fieldList, minNumObs = 3, dateStr = True) 

    #### Run Analysis ####
    se = StandardEllipse(ssdo, weightField = weightField, 
                         caseField = caseField, 
                         stdDeviations = stdDeviations)

    #### Create Output ####
    se.createOutput(outputFC)

class StandardEllipse(object):
    """This tool measures whether a distribution of features exhibits a
    directional trend (that is, whether features are farther from
    a specified center point in one direction than in another).  The
    user may specify an optional weight field and/or an optional
    case field.

    INPUTS: 
    ssdo (obj): instance of SSDataObject
    weightField {str, None}: name of weight field
    caseField {str, None} name of case field
    stdDeviations {float, 1.0}: number of standard devs around center

    ATTRIBUTES:
    meanCenter (dict): [case field value] = mean center (1)
    se (dict): [case field value] = standard distance (1)
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

    def __init__(self,  ssdo, weightField = None, caseField = None, 
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
        se = COLL.defaultdict(float)

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
                meanX, meanY = centers
                meanCenter[case] = centers

                #### Standard Ellipse ####
                devXY = xy - centers
                flatW = w.flatten()
                sigX = (flatW * devXY[:,0]**2.0).sum()  
                sigY = (flatW * devXY[:,1]**2.0).sum()
                sigXY = (flatW * devXY[:,0] * devXY[:,1]).sum()
                denom = 2.0 * sigXY
                diffXY = sigX - sigY
                sum1 = diffXY**2.0 + 4.0 * sigXY**2.0

                if not abs(denom) > 0:
                    arctanVal = 0.0
                else:
                    tempVal = (diffXY + NUM.sqrt(sum1)) / denom
                    arctanVal = NUM.arctan(tempVal)

                if arctanVal < 0.0: 
                    arctanVal += (NUM.pi / 2.0)

                sinVal = NUM.sin(arctanVal)
                cosVal = NUM.cos(arctanVal)
                sqrt2 = NUM.sqrt(2.0)
                sigXYSinCos = 2.0 * sigXY * sinVal * cosVal
                seX = (sqrt2 *
                       NUM.sqrt(((sigX * cosVal**2.0) - sigXYSinCos +
                                 (sigY * sinVal**2.0)) / 
                                  weightSum) * stdDeviations)

                seY = (sqrt2 *
                       NUM.sqrt(((sigX * sinVal**2.0) + sigXYSinCos +
                                 (sigY * cosVal**2.0)) / 
                                  weightSum) * stdDeviations)
                
                #### Counter Clockwise from Noon ####
                degreeRotation = 360.0 - (arctanVal * 57.2957795)  
                
                #### Convert to Radians ####
                radianRotation1 = UTILS.convert2Radians(degreeRotation)

                #### Add Rotation ####
                radianRotation2 = 360.0 - degreeRotation
                if seX > seY:
                    radianRotation2 += 90.0
                    if radianRotation2 > 360.0: 
                        radianRotation2 = radianRotation2 - 180.0

                se[case] = (seX, seY, degreeRotation, 
                            radianRotation1, radianRotation2)
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
        caseKeys = se.keys()
        caseKeys.sort()
        self.caseKeys = caseKeys

        #### Set Attributes ####
        self.meanCenter = meanCenter
        self.se = se
        self.badCases = badCases
        self.caseField = caseField
        self.stdDeviations = stdDeviations
        self.weightField = weightField

    def report(self, fileName = None):
        """Reports the Standard Ellipse results as a message or to a file.

        INPUTS:
        fileName {str, None}: path to a text file to populate with results
        """

        header = ARCPY.GetIDMessage(84210)
        columns = [ARCPY.GetIDMessage(84191), ARCPY.GetIDMessage(84211),
                   ARCPY.GetIDMessage(84212), ARCPY.GetIDMessage(84213), 
                   ARCPY.GetIDMessage(84214), ARCPY.GetIDMessage(84215)]
        results = [ columns ]
        for case in self.uniqueCases:
            if not self.caseField:
                strCase = "ALL"
            else:
                strCase = UTILS.caseValue2Print(case, self.caseIsString)
            meanX, meanY = self.meanCenter[case]
            seX, seY, degreeRotation, radianR1, radianR2 = self.se[case]
            rowResult = [ strCase, LOCALE.format("%0.6f", meanX),
                          LOCALE.format("%0.6f", meanY),
                          LOCALE.format("%0.6f", seX),
                          LOCALE.format("%0.6f", seY),
                          LOCALE.format("%0.6f", radianR2) ]
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
            seValues = self.se.values()
            if len(seValues):
                maxSE = NUM.array([ i[0:2] for i in seValues ]).max()
                largerExtent = UTILS.increaseExtentByConstant(ssdo.extent,
                                                        constant = maxSE)
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
        dataFieldNames = UTILS.getFieldNames(seFieldNames, outPath)
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
            seX, seY, degreeRotation, radianR1, radianR2 = self.se[case]
            seX2 = seX**2.0
            seY2 = seY**2.0

            #### Create Empty Polygon Geomretry ####
            poly = ARCPY.Array()

            #### Check for Valid Radius ####
            seXZero = UTILS.compareFloat(0.0, seX, rTol = .0000001)
            seXNan = NUM.isnan(seX)
            seXBool = seXZero + seXNan
            seYZero = UTILS.compareFloat(0.0, seY, rTol = .0000001)
            seYNan = NUM.isnan(seY)
            seYBool = seYZero + seYNan
            if seXBool or seYBool:
                badRadian = 6
                badCase = UTILS.caseValue2Print(case, self.caseIsString)
                badCaseRadians.append(badCase)
            else:
                badRadian = 0
                cosRadian = NUM.cos(radianR1)
                sinRadian = NUM.sin(radianR1)

                #### Calculate a Point For Each ####
                #### Degree in Ellipse Polygon ####                
                for degree in NUM.arange(0, 360): 
                    try:
                        radians = UTILS.convert2Radians(degree)
                        tanVal2 = NUM.tan(radians)**2.0
                        dX = MATH.sqrt((seX2 * seY2) /
                                      (seY2 + (seX2 * tanVal2)))
                        dY = MATH.sqrt((seY2 * (seX2 - dX**2.0)) /
                                       seX2)

                        #### Adjust for Quadrant ####
                        if 90 <= degree < 180:
                            dX = -dX
                        elif 180 <= degree < 270:
                            dX = -dX
                            dY = -dY
                        elif degree >= 270:
                            dY = -dY

                        #### Rotate X and Y ####
                        dXr = dX * cosRadian - dY * sinRadian
                        dYr = dX * sinRadian + dY * cosRadian

                        #### Create Point Shifted to ####
                        #### Ellipse Centroid ####
                        pntX = dXr + xVal
                        pntY = dYr + yVal
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
                rowResult = [poly, xVal, yVal, seX, seY, radianR2]

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
                ARCPY.AddIDMessage("WARNING", 1011, caseField, badCaseRadians)
            else:
                ARCPY.AddIDMessage("ERROR", 978)
                raise SystemExit()

        #### Return Extent to Normal if not Projected ####
        if ssdo.spatialRefType != "Projected":
            ARCPY.env.XYDomain = ""

        #### Clean Up ####
        del rows

        #### Set Attribute ####
        self.outputFC = outputFC
    
if __name__ == "__main__":
    setupStandardEllipse()

