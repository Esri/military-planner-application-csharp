"""
Tool Name:  Central Feature
Source Name: CentralFeature.py
Version: ArcGIS 10.1

This script will identify the most centrally located feature in a point,
line, or polygon feature class (with weighting and grouping optional).
"""

################### Imports ########################
import os as OS
import collections as COLL
import numpy as NUM
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO
import WeightsUtilities as WU
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

def setupCentralFeature():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)
    outputFC = ARCPY.GetParameterAsText(1)
    distanceMethod = ARCPY.GetParameterAsText(2).upper().replace(" ", "_")
    weightField = UTILS.getTextParameter(3, fieldName = True) 
    potentialField = UTILS.getTextParameter(4, fieldName = True)
    caseField = UTILS.getTextParameter(5, fieldName = True)

    distanceMethod = distanceMethod.split("_")[0]
    fieldList = []
    if weightField:
        fieldList.append(weightField)

    if potentialField:
        fieldList.append(potentialField)

    if caseField:
        fieldList.append(caseField)

    #### Create a Spatial Stats Data Object (SSDO) ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = outputFC,
                             useChordal = False)

    #### Populate SSDO with Data ####
    ssdo.obtainData(ssdo.oidName, fieldList, minNumObs = 1, dateStr = True) 

    #### Run Analysis ####
    cf = CentralFeature(ssdo, distanceMethod = distanceMethod,
                        weightField = weightField, 
                        potentialField = potentialField,
                        caseField = caseField)

    #### Create Output ####
    cf.createOutput(outputFC)

class CentralFeature(object):
    """This tool identifies most centrally located feature (may be weighted).
    
    INPUTS: 
    ssdo (obj): instance of SSDataObject
    distanceMethod {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN 
    weightField {str, None}: field name used to weight to mean centers
    potentialField {str, None}: field name used to weight features self 
    caseField {str, None}: field name used to subset mean centers

    METHODS:
    createOutput: creates a feature class with central features
    report: reports results as a printed message or to a file

    ATTRIBUTES:
    cf (dict): [case field value] = ([central feature OIDs], sumDist) (1)
    ssdo (class): instance of SSDataObject
    caseKeys (list): sorted list of all cases for print/output
    
    NOTES:
    (1)  The key for the central feature dict (cf) is "ALL" if no case field is
         provided
    """
    def __init__(self, ssdo, distanceMethod = "EUCLIDEAN",
                 weightField = None, potentialField = None, caseField = None):

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

        #### Verify Potential ####
        if potentialField:
            self.potential = self.ssdo.fields[potentialField].returnDouble()

            #### Report Negative Weights ####
            lessThanZero = NUM.where(self.potential < 0.0)
            if len(lessThanZero[0]):
                self.potential[lessThanZero] = 0.0
                ARCPY.AddIDMessage("Warning", 940)
        else:
            self.potential = NUM.zeros((self.ssdo.numObs,))

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
        cf = COLL.defaultdict(tuple)

        #### Calculate Central Feature ####
        ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84007), 
                            0, self.ssdo.numObs, 1)
        for case in self.uniqueCases:
            cfOIDs = []
            indices = NUM.where(self.caseVals == case)
            potent = self.potential[indices]
            xy = self.xyCoords[indices]
            w = self.weights[indices]
            cfOrder, minSumDist = nsquaredDist(xy, weights = w,
                                               potent = potent,
                                               dType = distanceMethod)
            for cfOrd in cfOrder:
                oid = ssdo.order2Master[indices[0][cfOrd]]
                cfOIDs.append(oid)
            cf[case] = (cfOIDs, minSumDist)

        #### Set Attributes ####
        self.ssdo = ssdo
        self.cf = cf
        self.caseField = caseField
        self.weightField = weightField
        self.potentialField = potentialField

    def report(self, fileName = None):
        """Reports the Central Feature results as a message or to a file.

        INPUTS:
        fileName {str, None}: path to a text file to populate with results.
        """

        header = ARCPY.GetIDMessage(84200)
        columns = [ARCPY.GetIDMessage(84191), ARCPY.GetIDMessage(84201), 
                   ARCPY.GetIDMessage(84202)]
        results = [ columns ]
        for case in self.uniqueCases:
            if not self.caseField:
                strCase = "ALL"
            else:
                strCase = UTILS.caseValue2Print(case, self.caseIsString)
            cfOIDs, minSumDist = self.cf[case]
            cfOIDs = [ str(i) for i in cfOIDs ]
            cfOIDs = ", ".join(cfOIDs)
            rowResult = [ strCase, 
                          cfOIDs,
                          LOCALE.format("%0.6f", minSumDist) ]
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
        tempCFLayer = "tmpCFLayer"

        try:
            DM.MakeFeatureLayer(ssdo.inputFC, tempCFLayer)
            first = True
            for key, value in self.cf.iteritems():
                oids = value[0]
                for oid in oids:
                    sqlString = ssdo.oidName + '=' + str(oid)
                    if first:
                        DM.SelectLayerByAttribute(tempCFLayer, 
                                                  "NEW_SELECTION",
                                                  sqlString)
                        first = False
                    else:
                        DM.SelectLayerByAttribute(tempCFLayer,
                                                  "ADD_TO_SELECTION", 
                                                  sqlString)

            UTILS.clearExtent(DM.CopyFeatures(tempCFLayer, outputFC))
        except:
            ARCPY.AddIDMessage("ERROR", 210, outputFC)
            raise SystemExit()

        #### Set Attribute ####
        self.outputFC = outputFC

######### Stand Alone Distance Method.  Currently ~ O(n**2) #########
######### Effort to Improve Algorithn Underway #########

def nsquaredDist(points, weights = None, potent = None, dType = "EUCLIDEAN"):
    """Method used to calculate the distance between each feature in the
    dataset.  The algorithm is near 0(n**2).  Effort to improve algorithn 
    is currently underway.

    INPUTS:
    points (array, numObs x 2): xy-coordinates for each feature
    weights {array, numObs x 1}: weights for each feature
    potent {array. numObs x 1}: self weights for each feature
    dType {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN (distance)

    OUTPUT:
    final (list): ids with minimum sum distance
    minSumDist (float): minimum sum distance
    """

    n,k = NUM.shape(points)
    maxMinSumDist = 3.402823466E+38

    if weights == None: 
        weights = NUM.ones((n,), float) 

    if potent == None:
        potent = NUM.zeros((n,), float)

    weightedPotential = weights * potent

    res = {}

    #### Calculate Sum of Weighted Distances For Each Feature ####
    weights.shape = n,1
    if dType == "EUCLIDEAN":
        for idx, point in enumerate(points):
            weightedDist = eucDistArray(point, points, weights) 
            res[idx] = weightedDist + (weights[idx] * potent[idx])
            ARCPY.SetProgressorPosition()
    else:
        for idx, point in enumerate(points):
            weightedDist = manDistArray(point, points, weights) 
            res[idx] = weightedDist + weightedPotential[idx]
            ARCPY.SetProgressorPosition()

    #### Minimum Sum of Weighted Distances (Central Feature) ####
    minSumDist = min(res.itervalues())
    final = [ key for key,val in res.iteritems() if val == minSumDist ]
    
    return final, minSumDist

def eucDistArray(point, points, w):
    diff = (point - points)**2.0
    return NUM.dot(NUM.sqrt(diff.sum(1)), w)

def manDistArray(point, points, w):
    diff = abs(point - points)
    return NUM.dot(diff.sum(1), w)

if __name__ == "__main__":
    setupCentralFeature()

