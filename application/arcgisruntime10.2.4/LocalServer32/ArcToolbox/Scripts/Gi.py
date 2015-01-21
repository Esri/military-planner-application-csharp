"""
Tool Name:  Hot Spot Analysis (Getis-Ord Gi*)
Source Name: Gi.py
Version: ArcGIS 10.1
Author: ESRI

This function performs the 1995 Getis and Ord Gi* statistic. For more
details, see: _The ESRI Guide to GIS Analysis_, Volume 2, Chapter 4 or
Ord, J.K. and Arthur Getis.  1995.  "Local Spatial Autocorrelation
Statistics." _Geographical Analysis_ 27(4): 287-306.
"""

################### Imports ########################
import sys as SYS
import os as OS
import locale as LOCALE
import numpy as NUM
import arcgisscripting as ARC
import arcpy as ARCPY
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO
import Stats as STATS
import WeightsUtilities as WU
import gapy as GAPY
import numpy.random as RAND
import random as PYRAND

################ Output Field Names #################
giFieldNames = ["GiZScore", "GiPValue"]
giPseudoFieldName = "GiPseudoP"
giBinFieldName = "Gi_Bin"

giRenderDict = { 0: "LocalGPoints.lyr",
                 1: "LocalGPolylines.lyr",
                 2: "LocalGPolygons.lyr" }

################### GUI Interface ###################
def setupLocalG():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)
    varName = ARCPY.GetParameterAsText(1).upper()
    varNameList = [varName]
    outputFC = ARCPY.GetParameterAsText(2)

    #### Parse Space Concept ####
    spaceConcept = ARCPY.GetParameterAsText(3).upper().replace(" ", "_")
    if spaceConcept == "INVERSE_DISTANCE_SQUARED":
        exponent = 2.0
    else:
        exponent = 1.0
    try:
        spaceConcept = WU.convertConcept[spaceConcept]
        wType = WU.weightDispatch[spaceConcept]
    except:
        ARCPY.AddIDMessage("ERROR", 723)
        raise SystemExit()

    #### EUCLIDEAN or MANHATTAN ####
    distanceConcept = ARCPY.GetParameterAsText(4).upper().replace(" ", "_")
    concept = WU.conceptDispatch[distanceConcept]

    #### Row Standardized Not Used in Hot Spot Analysis ####
    #### Results Are Identical With or Without ####
    #### Remains in UI for Backwards Compatibility ####
    rowStandard = ARCPY.GetParameterAsText(5).upper()

    #### Distance Threshold ####
    threshold = UTILS.getNumericParameter(6)

    #### Self Potential Field ####
    potentialField = UTILS.getTextParameter(7, fieldName = True)
    if potentialField:
        varNameList.append(potentialField)

    #### Spatial Weights File ####
    weightsFile = UTILS.getTextParameter(8)
    if weightsFile == None and wType == 8:
        ARCPY.AddIDMessage("ERROR", 930)
        raise SystemExit()
    if weightsFile and wType != 8:
        ARCPY.AddIDMessage("WARNING", 925)
        weightsFile = None

    #### FDR ####
    applyFDR = ARCPY.GetParameter(9)

    #### Create a Spatial Stats Data Object (SSDO) ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = outputFC, 
                             useChordal = True)


    #### Set Unique ID Field ####
    masterField = UTILS.setUniqueIDField(ssdo, weightsFile = weightsFile)

    #### Populate SSDO with Data ####
    if WU.gaTypes[spaceConcept]:
        ssdo.obtainDataGA(masterField, varNameList, minNumObs = 3,
                          warnNumObs = 30)
    else:
        ssdo.obtainData(masterField, varNameList, minNumObs = 3,
                        warnNumObs = 30)

    #### Run Hot-Spot Analysis ####
    gi = LocalG(ssdo, varName, outputFC, wType, weightsFile = weightsFile,
                concept = concept, threshold = threshold,
                exponent = exponent, potentialField = potentialField,
                applyFDR = applyFDR)

    #### Report and Set Parameters ####
    giField, pvField = gi.outputResults()
    try:
        ARCPY.SetParameterAsText(10, giField)
        ARCPY.SetParameterAsText(11, pvField)
        ARCPY.SetParameterAsText(12, gi.ssdo.masterField)
    except:
        ARCPY.AddIDMessage("WARNING", 902)

    gi.renderResults()

class LocalG(object):
    """Calculates 1995 Getis and Ord Gi* statistic:

    INPUTS:
    ssdo (obj): instance of SSDataObject
    varName (str): name of analysis field
    outputFC (str): path to output feature class
    wType (int): spatial conceptualization (1)
    weightsFile {str, None}: path to a spatial weights matrix file
    concept: {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN
    rowStandard {bool, True}: row standardize weights?
    threshold {float, None}: distance threshold
    exponent {float, 1.0}: distance decay
    potentialField {str, None}: name of self potential field

    ATTRIBUTES:
    numObs (int): number of features in analysis
    y (array, numObs x 1): vector of field values
    potVals (array, numObs x 1): vector of self potential values
    gi (array, numObs x 1): Local Gi* values
    pVals (array, numObs x 1): probability values (two-tailed)

    NOTES:
    (1) See the wTypeDispatch dictionary in WeightsUtilities.py for a
        complete list of spatial conceptualizations and their corresponding
        integer values.
    """

    def __init__(self, ssdo, varName, outputFC, wType,
                 weightsFile = None, concept = "EUCLIDEAN",
                 threshold = None, numNeighs = 0, exponent = 1.0,
                 potentialField = None, permutations = None,
                 applyFDR = False, pType = "BOOT"):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())

        #### Assess Whether SWM File Being Used ####
        self.swmFileBool = False
        if weightsFile:
            weightSuffix = weightsFile.split(".")[-1].lower()
            self.swmFileBool = (weightSuffix == "swm")

        #### Warn Inverse Distance if Geographic Coord System ####
        #if wType in [0, 7]:
        #    WU.checkGeographicCoord(self.ssdo.spatialRefType,
        #                            WU.wTypeDispatch[wType])

        #### Create Shape File Boolean for NULL Values ####
        self.outShapeFileBool = UTILS.isShapeFile(outputFC)

        #### Initialize Data ####
        self.initialize()

        #### Construct Based on SWM File or On The Fly ####
        self.construct()

    def initialize(self):
        """Populates the instance of the Spatial Statistics Data
        Object (SSDataObject) and resolves a default distance threshold
        if none given.
        """

        #### Shorthand Attributes ####
        ssdo = self.ssdo
        varName = self.varName
        concept = self.concept
        threshold = self.threshold
        exponent = self.exponent
        wType = self.wType
        weightsFile = self.weightsFile
        swmFileBool = self.swmFileBool
        masterField = ssdo.masterField
        potentialField = self.potentialField

        #### Get Data Array ####
        field = ssdo.fields[varName]
        self.y = field.returnDouble()
        self.numObs = ssdo.numObs
        maxSet = False
        self.fieldNames = [varName]

        #### Distance Threshold ####
        if wType in [0, 1, 7]:
            if threshold == None:
                threshold, avgDist = WU.createThresholdDist(ssdo, 
                                                concept = concept)


            #### Assures that the Threshold is Appropriate ####
            gaExtent = UTILS.get92Extent(ssdo.extent)
            fixed = (wType == 1)
            threshold, maxSet = WU.checkDistanceThreshold(ssdo, threshold,
                                                          weightType = wType)

            #### If the Threshold is Set to the Max ####
            #### Set to Zero for Script Logic ####
            if maxSet:
                #### All Locations are Related ####
                if self.numObs > 500:
                    ARCPY.AddIDMessage("WARNING", 717)

        #### Resolve Self Potential Field (Default to 1.0) ####
        if potentialField:
            potField = ssdo.fields[potentialField]
            self.potVals = potField.returnDouble()
            self.fieldNames.append(potentialField)

            #### Warn if Negative Self Weights ####
            sumNeg = NUM.sum(self.potVals < 0.0)
            if sumNeg:
                ARCPY.AddIDMessage("WARNING", 940)
                #### Set Negative Weights to Zero ####
                self.potVals = NUM.where(self.potVals < 0.0, 0.0,
                                         self.potVals)

        else:
            if weightsFile and not swmFileBool:
                self.potVals = None
            else:
                self.potVals = NUM.ones(self.numObs)

        #### Set Attributes ####
        self.maxSet = maxSet
        self.threshold = threshold
        self.master2Order = ssdo.master2Order
        self.swmFileBool = swmFileBool

    def construct(self):
        """Constructs the neighborhood structure for each feature and
        dispatches the appropriate values for the calculation of the
        statistic."""

        #### Shorthand Attributes ####
        ssdo = self.ssdo
        varName = self.varName
        concept = self.concept
        gaConcept = concept.lower()
        threshold = self.threshold
        exponent = self.exponent
        wType = self.wType
        numObs = self.numObs
        master2Order = self.master2Order
        masterField = ssdo.masterField
        weightsFile = self.weightsFile
        potentialField = self.potentialField

        #### Assure that Variance is Larger than Zero ####
        yVar = NUM.var(self.y)
        if NUM.isnan(yVar) or yVar <= 0.0:
            ARCPY.AddIDMessage("ERROR", 906)
            raise SystemExit()

        #### Create Summed Variables ####
        self.intRange = NUM.arange(numObs)
        self.floatN = self.numObs * 1.0
        ySum = self.y.sum()
        ySum2 = (self.y**2.0).sum()
        self.yBar = ySum / self.floatN
        self.S = NUM.sqrt( (ySum2 / self.floatN) - self.yBar**2.0 )
        self.nm1 = self.floatN - 1.0

        #### Create Base Data Structures/Variables ####
        self.gi = NUM.zeros(numObs)
        self.pVals = NUM.ones(numObs)
        if self.permutations:
            self.pseudoPVals = NUM.ones(numObs)

        #### Set Neighborhood Structure Type ####
        if self.weightsFile:
            if self.swmFileBool:
                #### Open Spatial Weights and Obtain Chars ####
                swm = WU.SWMReader(weightsFile)
                N = swm.numObs
                rowStandard = swm.rowStandard
                self.swm = swm

                #### Check to Assure Complete Set of Weights ####
                if numObs > N:
                    ARCPY.AddIDMessage("ERROR", 842, numObs, N)
                    raise SystemExit()

                #### Check if Selection Set ####
                isSubSet = False
                if numObs < N:
                    isSubSet = True
                iterVals = xrange(N)
            else:
                #### Warning for GWT with Bad Records/Selection ####
                if ssdo.selectionSet or ssdo.badRecords:
                    ARCPY.AddIDMessage("WARNING", 1029)

                #### Build Weights Dictionary ####
                weightDict = WU.buildTextWeightDict(weightsFile, master2Order)
                iterVals = master2Order.keys()
                N = numObs

        elif wType in [4, 5]:
            #### Polygon Contiguity ####
            if wType == 4:
                contiguityType = "ROOK"
            else:
                contiguityType = "QUEEN"
            contDict = WU.polygonNeighborDict(ssdo.inputFC, ssdo.oidName,
                                         contiguityType = contiguityType)
            iterVals = master2Order.keys()
            N = numObs

        else:
            gaTable = ssdo.gaTable
            gaSearch = GAPY.ga_nsearch(gaTable)
            if wType == 7:
                #### Zone of Indiff, All Related to All ####
                gaSearch.init_nearest(threshold, numObs, gaConcept)
            else:
                #### Inverse and Fixed Distances ####
                gaSearch.init_nearest(threshold, self.numNeighs, gaConcept)
            iterVals = range(numObs)
            N = numObs
            neighWeights = ARC._ss.NeighborWeights(gaTable, gaSearch,
                                                 weight_type = wType,
                                                 exponent = exponent,
                                                row_standard = False,
                                                 include_self = True)

        #### Create Progressor ####
        msg = ARCPY.GetIDMessage(84007)
        if self.permutations:
            msg += ": Using Permutations = %i" % self.permutations
        ARCPY.SetProgressor("step", msg , 0, N, 1)

        #### Create Neighbor Info Class ####
        ni = WU.NeighborInfo(masterField)

        #### Calculation For Each Feature ####
        for i in iterVals:
            if self.swmFileBool:
                #### Using SWM File ####
                info = swm.swm.readEntry()
                masterID = info[0]
                if master2Order.has_key(masterID):
                    rowInfo = WU.getWeightsValuesSWM(info, master2Order,
                                                     self.y,
                                                     rowStandard = rowStandard,
                                                     potVals = self.potVals)
                    includeIt = True
                else:
                    includeIt = False

            elif self.weightsFile and not self.swmFileBool:
                #### Text Weights ####
                masterID = i
                includeIt = True
                rowInfo = WU.getWeightsValuesText(masterID, master2Order,
                                                  weightDict, self.y,
                                                  potVals = self.potVals,
                                                  allowSelf = True)

            elif wType in [4, 5]:
                #### Polygon Contiguity ####
                masterID = i
                includeIt = True
                rowInfo = WU.getWeightsValuesCont(masterID, master2Order,
                                                  contDict, self.y,
                                                  rowStandard = False,
                                                  potVals = self.potVals)

            else:
                #### Distance Based ####
                masterID = gaTable[i][0]
                includeIt = True
                rowInfo = WU.getWeightsValuesOTF_Potent(neighWeights, i, 
                                                        self.y,
                                                        self.potVals)

            #### Subset Boolean for SWM File ####
            if includeIt:
                #### Parse Row Info ####
                orderID, yiVal, nhIDs, nhVals, weights = rowInfo

                #### Assure Neighbors Exist After Selection ####
                nn, nhIDs, nhVals, weights = ni.processInfo(masterID, nhIDs,
                                                            nhVals, weights)

                if nn:
                    #### Calculate Local G ####
                    self.calculateGI(orderID, yiVal, nhVals, weights)

            ARCPY.SetProgressorPosition()

        #### Clean Up ####
        if self.swmFileBool:
            swm.close()

        #### Report on Features with No Neighbors ####
        ni.reportNoNeighbors(failAllNoNeighs = False)
        self.setNullValues(ni.idsNoNeighs)

        #### Report on Features with Large Number of Neighbors ####
        ni.reportWarnings()
        ni.reportMaximums()
        self.neighInfo = ni

        #### Set p-values for Gi Bins ####
        if self.permutations:
            #### Use Pseudo p-values ####
            pv = self.pseudoPVals
        else:
            #### Use Traditional p-values ####
            pv = self.pVals

        toolMSG = ARCPY.GetIDMessage(84466)
        if self.applyFDR:
            #### Set Bins Using FDR ####
            msg = ARCPY.GetIDMessage(84472).format(toolMSG)
            ARCPY.SetProgressor("default", msg)
            self.giBins = STATS.fdrTransform(pv, self.gi)
        else:
            msg = ARCPY.GetIDMessage(84473).format(toolMSG)
            ARCPY.SetProgressor("default", msg)
            self.giBins = STATS.pValueBins(pv, self.gi)

    def calculateGI(self, orderID, yiVal, nhVals, weights):
        """Calculates Local Gi* for a given feature.

        INPUTS:
        orderID (int): order in corresponding numpy value arrays
        yiVal (float): value for given feature
        nhVals (array, nn): values for neighboring features (1)
        weights (array, nn): weight values for neighboring features (1)

        NOTES:
        (1)  nn is equal to the number of neighboring features
        """

        sumW = weights.sum()
        sumW2 = (weights**2.0).sum()
        lagVal = (nhVals * weights).sum()
        ei = (sumW * self.yBar)
        dev = lagVal - ei
        denomNum = (self.floatN * sumW2) - sumW**2.0
        denomG = self.S * NUM.sqrt(denomNum/self.nm1)
        giVal = dev / denomG
        pVal = STATS.zProb(giVal, type = 2)

        #### Assign To Result Vectors ####
        self.gi[orderID] = giVal
        self.pVals[orderID] = pVal

        #### Do Permutations ####
        if self.permutations:
            numNHS = len(nhVals)
            if self.pType == "BOOT":
                randomInts = RAND.random_integers(0, self.numObs-1,
                                                  (self.permutations, numNHS))
            else:
                randomInts = NUM.zeros((self.permutations, numNHS), int)
                for perm in xrange(self.permutations):
                    randomInts[perm] = PYRAND.sample(self.intRange, numNHS)
            nhValsPerm = self.y[randomInts]
            lagValsPerm = (nhValsPerm * weights).sum(1)
            devs = lagValsPerm - ei
            giValsPerm = devs / denomG
            pseudoP = STATS.pseudoPValue(giVal, giValsPerm)
            self.pseudoPVals[orderID] = pseudoP

    def setNullValues(self, idsNoNeighs):
        """Set no neighbor data for a given features (1).

        INPUTS:
        idsNoNeighs (list): unique ID values that have no neighbors

        NOTES:
        (1)   The no neighbor result differs for shapefiles as it has no NULL
              value capabilities.
        """

        for id in idsNoNeighs:
            orderID = self.ssdo.master2Order[id]
            if self.outShapeFileBool:
                self.gi[orderID] = 0.0
                self.pVals[orderID] = 1.0
                if self.permutations:
                    self.pseudoPVals[orderID] = 1.0
            else:
                self.gi[orderID] = NUM.nan
                self.pVals[orderID] = NUM.nan
                if self.permutations:
                    self.pseudoPVals[orderID] = NUM.nan

    def outputResults(self):
        """Creates output feature class Local Gi*."""

        #### Prepare Derived Variables for Output Feature Class ####
        outPath, outName = OS.path.split(self.outputFC)
        fieldOrder = UTILS.getFieldNames(giFieldNames, outPath)
        fieldData = [self.gi, self.pVals]
        fieldTypes = ["DOUBLE", "DOUBLE"]

        #### Add Pseudo-P Field ####
        if self.permutations:
            fieldOrder.append(giPseudoFieldName)
            fieldData.append(self.pseudoPVals)
            fieldTypes.append("DOUBLE")

        #### Add Gi Bin Field ####
        fieldOrder.append(giBinFieldName)
        fieldData.append(self.giBins)
        fieldTypes.append("LONG")

        #### Create Alias Field Names ####
        rowStandard = False
        if self.wType == 8:
            addString = OS.path.basename(self.weightsFile)
        elif self.wType in [0, 1, 7]:
            if self.maxSet:
                addString = "0"
            else:
                addString = str(int(self.threshold))
        else:
            addString = None

        aliasList = WU.createSpatialFieldAliases(fieldOrder,
                                                 addString = addString,
                                                 wType = self.wType,
                                                 exponent = self.exponent,
                                                 rowStandard = rowStandard)
        if self.applyFDR:
            aliasList[-1] += "_FDR"

        #### Create/Populate Dictionary of Candidate Fields ####
        candidateFields = {}
        for fieldInd, fieldName in enumerate(fieldOrder):
            fieldType = fieldTypes[fieldInd]
            candidateField = SSDO.CandidateField(fieldName, fieldType,
                                                 fieldData[fieldInd],
                                                 alias = aliasList[fieldInd])
            candidateFields[fieldName] = candidateField

        #### Input Fields to Copy to Output FC ####
        appendFields = [i for i in self.fieldNames]

        #### Add Date-Time Field If Applicable ####
        if self.swmFileBool:
            if self.swm.wType == 9:
                if self.ssdo.allFields.has_key(self.swm.timeField.upper()):
                    appendFields.insert(0, self.swm.timeField.upper())

        #### Write Data to Output Feature Class ####
        self.ssdo.output2NewFC(self.outputFC, candidateFields,
                               appendFields = appendFields,
                               fieldOrder = fieldOrder)

        return fieldOrder[0], fieldOrder[1]


    def renderResults(self):
        #### Set the Default Symbology ####
        params = ARCPY.gp.GetParameterInfo()
        try:
            renderType = UTILS.renderType[self.ssdo.shapeType.upper()]
            renderLayerFile = giRenderDict[renderType]
            templateDir = OS.path.dirname(OS.path.dirname(SYS.argv[0]))
            fullRLF = OS.path.join(templateDir, "Templates",
                                   "Layers", renderLayerFile)
            params[2].Symbology = fullRLF
        except:
            ARCPY.AddIDMessage("WARNING", 973)

if __name__ == "__main__":
    setupLocalG()
