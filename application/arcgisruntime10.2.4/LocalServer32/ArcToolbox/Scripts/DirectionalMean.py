"""
Tool Name:  Linear Directional Trend 
Source Name: DirectionalMean.py
Version: ArcGIS 10.1
Author: ESRI

This tool identifies the general (mean) direction for a set of vectors.
"""

################### Imports ########################
import os as OS
import sys as SYS
import numpy as NUM
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSTimeUtilities as TUTILS
import SSDataObject as SSDO
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

################ Output Field Names #################
lmFieldNames = ["CompassA", "DirMean", "CirVar", "AveX", "AveY", "AveLen"]

################### GUI Interface ###################

def setupDirectionalMean():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)
    outputFC = ARCPY.GetParameterAsText(1)
    orientationOnly = ARCPY.GetParameter(2)   
    caseField = UTILS.getTextParameter(3, fieldName = True)     
    
    dm = DirectionalMean(inputFC, outputFC = outputFC, caseField = caseField, 
                         orientationOnly = orientationOnly)

    dm.createOutput(outputFC)

class DirectionalMean(object):
    """This tool identifies the general (mean) direction for a set of vectors.

    INPUTS: 
    inputFC (str): path to the input feature class
    outputFC {str, None}: path to the output feature class
    caseField {str, None}: field name used to subset mean centers
    orientationOnly {bool, False}: Should direction be used in calculation?  
                    
    METHODS:
    createOutput: creates a feature class with linear means.
    report: reports results as a printed message or to a file.

    ATTRIBUTES:
    meanCenter (dict): [case field value] = mean center (1)
    dm (dict): [case field value] = directional mean (1)
    badCases (list): list of cases that were unsuccessful.
    ssdo (class): instance of SSDataObject
    caseKeys (list): sorted list of all cases for print/output

    NOTES:
    (1)  The keys for the mean center (meanCenter) and directional mean (dm)
         dicts are equal to "ALL" if no case field is provided
    """

    def __init__(self, inputFC, outputFC = None, caseField = None, 
                 orientationOnly = False):

        #### Create SSDataObject ####
        ssdo = SSDO.SSDataObject(inputFC, templateFC = outputFC,
                                 useChordal = False)
        cnt = UTILS.getCount(inputFC)
        ERROR.errorNumberOfObs(cnt, minNumObs = 1)
        fieldList = [ssdo.oidName, "SHAPE@"]
        caseIsString = False
        if caseField:
            fieldList.append(caseField)
            caseType = ssdo.allFields[caseField].type.upper()
            caseIsString = caseType == "STRING"

        #### Initialize Accounting Structures ####
        xyLenVals = {}
        sinCosVals = {}

        #### Open Search Cursor ####
        try:
            rows = DA.SearchCursor(inputFC, fieldList, "", 
                                   ssdo.spatialRefString)
        except:
            ARCPY.AddIDMessage("ERROR", 204)
            raise SystemExit()

        #### Keep track of Invalid Fields ####
        badIDs = []
        badLengths = []
        badRecord = False
        negativeWeights = False

        #### Create Progressor ####
        ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84001), 0, cnt, 1)

        for row in rows:
            OID = row[0]
            shapeInfo = row[1]
            badRow = row.count(None) 
            try:
                centroidInfo = shapeInfo.trueCentroid
                xVal = centroidInfo.X
                yVal = centroidInfo.Y
                length = float(shapeInfo.length)
                firstPoint = shapeInfo.firstPoint
                lastPoint = shapeInfo.lastPoint
                if firstPoint == lastPoint:
                    badLengths.append(OID)
                    badRow = True
                else:
                    firstX = float(firstPoint.X)
                    firstY = float(firstPoint.Y)
                    lastX = float(lastPoint.X)
                    lastY = float(lastPoint.Y)
            except:
                badRow = True

            #### Process Good Records ####
            if not badRow:
                #### Case Field ####
                caseVal = "ALL"
                if caseField:
                    caseVal = UTILS.caseValue2Print(row[2], caseIsString)

                #### Get Angle ####
                numer = lastX - firstX
                denom = lastY - firstY
                angle = UTILS.getAngle(numer, denom) 

                #### Adjust for Orientation Only ####
                if orientationOnly:
                    angle2Degree = UTILS.convert2Degree(angle)
                    if angle2Degree < 180:
                        numer = firstX - lastX
                        denom = firstY - lastY
                        angle = UTILS.getAngle(numer, denom) 

                sinVal = NUM.sin(angle)
                cosVal = NUM.cos(angle)
                
                xyLenVal = (xVal, yVal, length)
                sinCosVal = (sinVal, cosVal)

                try:
                    xyLenVals[caseVal].append(xyLenVal)
                    sinCosVals[caseVal].append(sinCosVal)
                except:
                    xyLenVals[caseVal] = [ xyLenVal ]
                    sinCosVals[caseVal] = [ sinCosVal ]

            else:
                #### Bad Record ####
                badRecord = True
                badIDs.append(OID)

            ARCPY.SetProgressorPosition()

        del rows

        #### Get Set of Bad IDs ####
        badIDs = list(set(badIDs))
        badIDs.sort()
        badIDs = [ str(i) for i in badIDs ]
        
        #### Process any bad records encountered ####
        bn = len(badIDs)
        if badRecord:
            err = ERROR.reportBadRecords(cnt, bn, badIDs, label = ssdo.oidName)

        #### Error For Not Enough Observations ####
        goodRecs = cnt - bn
        ERROR.errorNumberOfObs(goodRecs, minNumObs = 1)

        #### Report Features With No Length ####
        badLengths = list(set(badLengths))
        badLengths.sort()
        badLengths = [ str(i) for i in badLengths ]
        numBadLengths = len(badLengths)
        if numBadLengths > 0:
            ERROR.reportBadLengths(cnt, numBadLengths, badLengths, 
                                   label = ssdo.oidName)

        #### Set up for Bad Cases ####
        badCases = []
        cases = xyLenVals.keys()
        meanCenter = {}
        dm = {}

        #### Calculate Mean Center and Standard Distance ####
        for case in cases:
            xyLens = xyLenVals[case]
            numFeatures = len(xyLens)
            if numFeatures > 0:
                #### Mean Centers and Lengths ####
                xyLens = NUM.array(xyLens)
                meanX, meanY, meanL = NUM.mean(xyLens, 0)

                #### Sum Sin and Cos ####
                scVals = NUM.array(sinCosVals[case])
                sumSin, sumCos = NUM.sum(scVals, 0)

                #### Calculate Angle ####
                radianAngle = UTILS.getAngle(sumSin, sumCos)
                degreeAngle = UTILS.convert2Degree(radianAngle)

                #### Get Start and End Points ####
                halfMeanLen = meanL / 2.0
                endX = (halfMeanLen * NUM.sin(radianAngle)) + meanX
                startX = (2.0 * meanX) - endX
                endY = (halfMeanLen * NUM.cos(radianAngle)) + meanY
                startY = (2.0 * meanY) - endY
                unstandardized = NUM.sqrt(sumSin**2.0 + sumCos**2.0)
                circVar = 1.0 - (unstandardized / (numFeatures * 1.0))

                #### Re-adjust Angle Back towards North ####
                if orientationOnly:
                    degreeAngle = degreeAngle - 180.0
                    radianAngle = UTILS.convert2Radians(degreeAngle)

                #### Populate Results Structure ####
                meanCenter[case] = (meanX, meanY)
                dm[case] = [ (startX, startY), (endX, endY), meanL, 
                              radianAngle, degreeAngle, circVar ] 

        #### Sorted Case List ####
        caseKeys = dm.keys()
        caseKeys.sort()
        self.caseKeys = caseKeys

        #### Set Attributes ####
        self.ssdo = ssdo
        self.meanCenter = meanCenter
        self.dm = dm
        self.badCases = badCases
        self.inputFC = inputFC
        self.outputFC = outputFC
        self.caseField = caseField
        self.orientationOnly = orientationOnly
        self.caseIsString = caseIsString

    def report(self, fileName = None):
        """Reports the Directional Mean results as a message or to a file.

        INPUTS:
        fileName {str, None}: path to a text file to populate with results.
        """

        header = ARCPY.GetIDMessage(84203)
        columns = [ARCPY.GetIDMessage(84191), ARCPY.GetIDMessage(84204), 
                   ARCPY.GetIDMessage(84205), ARCPY.GetIDMessage(84206),
                   ARCPY.GetIDMessage(84207), ARCPY.GetIDMessage(84208),
                   ARCPY.GetIDMessage(84209)]
        results = [ columns ]
        for case in self.caseKeys:
            if not self.caseField:
                strCase = "ALL"
            else:
                strCase = UTILS.caseValue2Print(case, self.caseIsString)
            meanX, meanY = self.meanCenter[case]
            start, end, length, rAngle, dAngle, circVar = self.dm[case]
            dirMean = 360. - dAngle + 90.
            if not dirMean < 360:
                dirMean = dirMean - 360.
            rowResult = [ strCase, 
                          LOCALE.format("%0.6f", dAngle),
                          LOCALE.format("%0.6f", dirMean),
                          LOCALE.format("%0.6f", circVar), 
                          LOCALE.format("%0.6f", meanX),
                          LOCALE.format("%0.6f", meanY),
                          LOCALE.format("%0.6f", length) ]
            results.append(rowResult)

        outputTable = UTILS.outputTextTable(results, header = header)
        if fileName:
            f = UTILS.openFile(fileName, "w")
            f.write(outputTable)
            f.close()
        else:
            ARCPY.AddMessage(outputTable)

    def createOutput(self, outputFC):
        """Creates an Output Feature Class with the Directional Mean
        Results.

        INPUTS:
        outputFC (str): path to the output feature class
        """

        #### Validate Output Workspace ####
        ERROR.checkOutputPath(outputFC)

        #### Shorthand Attributes ####
        ssdo = self.ssdo
        caseField = self.caseField

        #### Create Output Feature Class ####
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84003))
        outPath, outName = OS.path.split(outputFC)

        try:
            DM.CreateFeatureclass(outPath, outName, "POLYLINE",
                                  "", ssdo.mFlag, ssdo.zFlag, 
                                  ssdo.spatialRefString)
        except:
            ARCPY.AddIDMessage("ERROR", 210, outputFC)
            raise SystemExit()

        #### Add Fields to Output FC ####
        dataFieldNames = UTILS.getFieldNames(lmFieldNames, outPath)
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

        #### Populate Output Feature Class ####
        allFieldNames = shapeFieldNames + dataFieldNames
        rows = DA.InsertCursor(outputFC, allFieldNames)
        for case in self.caseKeys:
            #### Get Results ####
            start, end, length, rAngle, dAngle, circVar = self.dm[case]
            meanX, meanY = self.meanCenter[case]
            dirMean = 360. - dAngle + 90.
            if not dirMean < 360:
                dirMean = dirMean - 360.

            #### Create Start and End Points ####
            x0, y0 = start
            startPoint = ARCPY.Point(x0, y0, ssdo.defaultZ)
            x1, y1 = end
            endPoint = ARCPY.Point(x1, y1, ssdo.defaultZ)

            #### Create And Populate Line Array ####
            line = ARCPY.Array()
            line.add(startPoint)
            line.add(endPoint)
            line = ARCPY.Polyline(line, None, True)

            #### Create and Populate New Line Feature ####
            rowResult = [line, dAngle, dirMean, circVar, 
                         meanX, meanY, length]

            if caseField:
                caseValue = case
                if caseIsDate:
                    caseValue = TUTILS.iso2DateTime(caseValue)
                rowResult.append(caseValue)
            rows.insertRow(rowResult)

        #### Clean Up ####
        del rows

        #### Set Attribute ####
        self.outputFC = outputFC

        #### Set the Default Symbology ####
        params = ARCPY.gp.GetParameterInfo()
        if self.orientationOnly:
            renderLayerFile = "LinearMeanTwoWay.lyr"
        else:
            renderLayerFile = "LinearMeanOneWay.lyr"
        templateDir = OS.path.dirname(OS.path.dirname(SYS.argv[0]))
        fullRLF = OS.path.join(templateDir, "Templates", 
                               "Layers", renderLayerFile)
        params[1].Symbology = fullRLF

if __name__ == "__main__":
    setupDirectionalMean()
