"""
Tool Name:  Median Center
Source Name: MedianCenter.py
Version: ArcGIS 10.1
Author: ESRI

This tool identifies the median center (minimizes the Euclidean Distance) 
for a set of features.  This median center is a point
constructed from X and Y values for all feature centroids in a dataset.
Features may optionally be grouped, if a CASE field is provided.  When
a weight field is specified, the result is weigted mean centers.

Algorithm Citation:  Adapted from Burt and Barber (1996) 
                     ``Elementary Statistics for Geographers''
                     The Guilford Press, New York, NY

Algorithm Notes:  A re-weighting iterative procedure. While it is a bit
slower than the methods based on the gradient (more iterations, however
each iteration is quicker), it is robust to candidate locations that
coincide with the features being analyzed.  
"""

################### Imports ########################
import os as OS
import collections as COLL
import numpy as NUM
import arcgisscripting as ARC
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSTimeUtilities as TUTILS
import SSDataObject as SSDO
import WeightsUtilities as WU
import Stats as STATS
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

################ Output Field Names #################
mdcFieldNames = ["XCoord", "YCoord"]

################### GUI Interface ###################

def setupMedianCenter():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)
    outputFC = ARCPY.GetParameterAsText(1)
    weightField = UTILS.getTextParameter(2, fieldName = True)
    caseField = UTILS.getTextParameter(3, fieldName = True)        
    attFields = UTILS.getTextParameter(4, fieldName = True)   

    fieldList = []
    if weightField:
        fieldList.append(weightField)
    if caseField:
        fieldList.append(caseField)
    if attFields:
        attFields = attFields.split(";")
        fieldList = fieldList + attFields

    #### Populate SSDO with Data ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = outputFC,
                             useChordal = False)

    #### Populate SSDO with Data ####
    ssdo.obtainData(ssdo.oidName, fieldList, minNumObs = 1, dateStr = True) 

    #### Run Analysis ####
    mc = MedianCenter(ssdo, weightField = weightField,
                      caseField = caseField, attFields = attFields)

    #### Create Output ####
    mc.createOutput(outputFC)

class MedianCenter(object):
    """This tool identifies the weighted median center (minimizes the 
    Euclidean distance) for a set of features. 

    INPUTS: 
    ssdo (obj): instance of SSDataObject
    weightField {str, None}: name of weight field
    caseField {str, None} name of case field
    attFields {list, []}: numeric field(s) for optional weigthed median

    ATTRIBUTES:
    medianCenter (dict): [case field value] = median center (1)
    attCenter  (dict): [case field value] = att field center(s) (1)
    badCases (list): list of cases that were unsuccessful.
    ssdo (class): instance of SSDataObject
    caseKeys (list): sorted list of all cases for print/output

    METHODS:
    createOutput: creates a feature class with standard distances.
    report: creates and prints the output in tabular text format.

    NOTES:
    (1)  The key for the mean center dicts is "ALL" if no case field is
         provided
    """

    def __init__ (self, ssdo, weightField = None, caseField = None, 
                  attFields = None):

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
        medianCenter = COLL.defaultdict(NUM.array)

        if attFields:
            attCenter = COLL.defaultdict(NUM.array)

        #### Keep Track of Bad Cases ####
        badCases = []

        #### Calculate Results ####
        for case in self.uniqueCases:
            indices = NUM.where(self.caseVals == case)
            numFeatures = len(indices[0])
            xy = self.xyCoords[indices]
            w = self.weights[indices]
            weightSum = w.sum()
            if (weightSum != 0.0) and (numFeatures > 0):

                #### Calculate Median Center ####
                medX, medY, iters = calcMedianCenter(xy, w)
                medianCenter[case] = (medX, medY)
                if attFields:
                    attMeds = []
                    for attField in attFields:
                        attCaseVals = ssdo.fields[attField].returnDouble()
                        attCaseVals = attCaseVals[indices] 
                        attMed = STATS.median(attCaseVals, weights = w)
                        attMeds.append(attMed)
                    attMeds = NUM.array(attMeds)
                    attCenter[case] = attMeds
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
        caseKeys = medianCenter.keys()
        caseKeys.sort()
        self.caseKeys = caseKeys

        #### Set Attributes ####
        self.medianCenter = medianCenter
        self.badCases = badCases
        self.caseField = caseField
        self.attFields = attFields
        self.weightField = weightField
        if attFields:
            self.attCenter = attCenter

    def report(self, fileName = None):
        """Reports the Median Center results as a message or to a file.

        INPUTS:
        fileName {str, None}: path to a text file to populate with results
        """

        header = ARCPY.GetIDMessage(84190)
        columns = [ARCPY.GetIDMessage(84191), ARCPY.GetIDMessage(84192), 
                   ARCPY.GetIDMessage(84193)]
        if self.attFields:
            for attField in self.attFields:
                columns.append(ARCPY.GetIDMessage(84194).format(attField))
        results = [ columns ]
        for case in self.uniqueCases:
            if not self.caseField:
                strCase = "ALL"
            else:
                strCase = UTILS.caseValue2Print(case, self.caseIsString)
            medX, medY = self.medianCenter[case]
            rowResult = [ strCase, LOCALE.format("%0.6f", medX),
                          LOCALE.format("%0.6f", medY) ]
            if self.attFields:
                for attInd, attField in enumerate(self.attFields):
                    medAtt = self.attCenter[case][attInd]
                    rowResult.append(LOCALE.format("%0.6f", medAtt))
            results.append(rowResult)

        outputTable = UTILS.outputTextTable(results, header = header)
        if fileName:
            f = open(fileName, "w")
            f.write(outputTable)
            f.close()
        else:
            ARCPY.AddMessage(outputTable)

    def createOutput(self, outputFC):
        """Creates an Output Feature Class with the Median Centers.

        INPUTS:
        outputFC (str): path to the output feature class
        """

        #### Validate Output Workspace ####
        ERROR.checkOutputPath(outputFC)

        #### Shorthand Attributes ####
        ssdo = self.ssdo
        caseField = self.caseField
        attFields = self.attFields

        #### Create Output Feature Class ####
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84003))
        outPath, outName = OS.path.split(outputFC)

        try:
            DM.CreateFeatureclass(outPath, outName, "POINT", "", ssdo.mFlag, 
                                  ssdo.zFlag, ssdo.spatialRefString)
        except:
            ARCPY.AddIDMessage("ERROR", 210, outputFC)
            raise SystemExit()

        #### Add Field Names ####
        dataFieldNames = UTILS.getFieldNames(mdcFieldNames, outPath)
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

        if attFields:
            for attField in attFields:
                fcAttField = ssdo.allFields[attField]
                validAttName = UTILS.validQFieldName(fcAttField, outPath)
                if caseField:
                    if validCaseName == validAttName:
                        validAttName = ARCPY.GetIDMessage(84195)
                UTILS.addEmptyField(outputFC, validAttName, "DOUBLE") 
                dataFieldNames.append(validAttName)

        outShapeFileBool = UTILS.isShapeFile(outputFC)
            
        #### Add Median X, Y, Dim ####
        allFieldNames = shapeFieldNames + dataFieldNames
        rows = DA.InsertCursor(outputFC, allFieldNames)
        for case in self.caseKeys:

            #### Median Centers ####
            medX, medY = self.medianCenter[case]
            pnt = (medX, medY, ssdo.defaultZ)
            rowResult = [pnt, medX, medY]

            #### Set Attribute Fields ####
            if caseField:
                caseValue = case.item()
                if caseIsDate:
                    caseValue = TUTILS.iso2DateTime(caseValue)
                rowResult.append(caseValue)

            #### Set Attribute Fields ####
            if attFields:
                for attInd, attField in enumerate(self.attFields):
                    medAtt = self.attCenter[case][attInd]
                    rowResult.append(medAtt)

            rows.insertRow(rowResult)
        
        #### Clean Up ####
        del rows

        #### Set Attribute ####
        self.outputFC = outputFC

def calcMedianCenter(coords, weights):
    """Calculates the weighted median center (minimizes the Euclidean
    distance) for a set of xy-coordinates. (1, A)

    INPUTS:
    coords (array, nx2): x,y coordinates in numpy array
    weights (array, n): weights for coordinates

    OUTPUT:
    estimateX, estimateY, c (list): [median X, median Y, iterations]

    NOTES:
    (1) A re-weighting iterative procedure. While it is a bit
        slower than the methods based on the gradient (more iterations, 
        however each iteration is quicker), it is robust to candidate 
        locations that coincide with the features being analyzed.  

    REFERENCES:  
    (A) Adapted from Burt and Barber (1996) 
        ``Elementary Statistics for Geographers''
        The Guilford Press, New York, NY
    """
    
    #### Assess Shape and Return if Single Feature or Coincident Points ####
    n, k = NUM.shape(coords)
    coordVariance = coords.var(0)
    if n == 1 or not coordVariance.any():
        estimateX, estimateY = coords[0]
        return estimateX, estimateY, 1
    else:
        return ARC._ss.median_center(coords, weights)

if __name__ == "__main__":
    mc = setupMedianCenter()

