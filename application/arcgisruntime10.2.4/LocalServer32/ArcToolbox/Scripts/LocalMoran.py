"""
Tool Name:  Cluster/Outlier Analysis (Anselin Local Morans I)
Source Name: LocalMoran.py
Version: ArcGIS 10.1
Author: ESRI

This tool performs the Anselin Local Moran's I spatial autocorrelation
statistic. For more details, see: _The ESRI Guide to GIS Analysis_,
Volume 2, Chapter 4 and/or Anselin, "Local Indicators of Spatial
Association -- LISA", _Geographical Analysis_, v. 27, no. 2 (April 1995).
"""

################### Imports ########################
import sys as SYS
import os as OS
import locale as LOCALE
import numpy as NUM
import numpy.random as RAND
import arcgisscripting as ARC
import arcpy as ARCPY
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO
import Stats as STATS
import WeightsUtilities as WU
import gapy as GAPY

################ Output Field Names #################
liFieldNames = ["LMiIndex", "LMiZScore", "LMiPValue"]
liPseudoFieldName = "LMiPseudoP"
liCOFieldName =  "COType"

liRenderDict = { 0: "LocalIPoints.lyr",
                 1: "LocalIPolylines.lyr",
                 2: "LocalIPolygons.lyr" }

################### GUI Interface ###################
def setupLocalI():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)                    
    varName = ARCPY.GetParameterAsText(1).upper()              
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
        ARCPY.AddIDMessage("Error", 723)
        raise SystemExit()

    #### EUCLIDEAN or MANHATTAN ####
    distanceConcept = ARCPY.GetParameterAsText(4).upper().replace(" ", "_")
    concept = WU.conceptDispatch[distanceConcept]

    #### Row Standardized ####
    rowStandard = ARCPY.GetParameterAsText(5).upper()
    if rowStandard == 'ROW':
        rowStandard = True
    else:
        rowStandard = False

    #### Distance Threshold ####
    threshold = UTILS.getNumericParameter(6)

    #### Spatial Weights File ####
    weightsFile = UTILS.getTextParameter(7)    
    if weightsFile == None and wType == 8:
        ARCPY.AddIDMessage("ERROR", 930)
        raise SystemExit()
    if weightsFile and wType != 8:
        ARCPY.AddIDMessage("WARNING", 925)
        weightsFile = None

    #### FDR ####
    applyFDR = ARCPY.GetParameter(8)

    #### Create a Spatial Stats Data Object (SSDO) ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = outputFC, 
                             useChordal = True)

    #### Set Unique ID Field ####
    masterField = UTILS.setUniqueIDField(ssdo, weightsFile = weightsFile)

    #### Populate SSDO with Data ####
    if WU.gaTypes[spaceConcept]:
        ssdo.obtainDataGA(masterField, [varName], minNumObs = 3, 
                          warnNumObs = 30)
    else:
        ssdo.obtainData(masterField, [varName], minNumObs = 3, 
                        warnNumObs = 30)

    #### Run Cluster-Outlier Analysis ####
    li = LocalI(ssdo, varName, outputFC, wType,
                weightsFile = weightsFile, concept = concept,
                rowStandard = rowStandard, threshold = threshold, 
                exponent = exponent, applyFDR = applyFDR)

    #### Report and Set Parameters ####
    liField, ziField, pvField, coField = li.outputResults()
    try:
        ARCPY.SetParameterAsText(9, liField)
        ARCPY.SetParameterAsText(10, ziField)
        ARCPY.SetParameterAsText(11, pvField)
        ARCPY.SetParameterAsText(12, coField)
        ARCPY.SetParameterAsText(13, li.ssdo.masterField)
    except:
        ARCPY.AddIDMessage("WARNING", 902)

    li.renderResults()

class LocalI(object):
    """Calculates 1995 Anselin Local Moran's I statistic:
    
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

    ATTRIBUTES:
    numObs (int): number of features in analysis
    y (array, numObs x 1): vector of field values
    yDev (array, numObs x 1): vector of field deviation from mean
    li (array, numObs x 1): Local I values
    ei (array, numObs x 1): Expected I values
    vi (array, numObs x 1): Variance I values
    zi (array, numObs x 1): z-values
    pVals (array, numObs x 1): probability values (two-tailed)
    moranBins ((array, numObs): significant cluster-outliers (2)

    NOTES:
    (1) See the wTypeDispatch dictionary in WeightsUtilities.py for a 
        complete list of spatial conceptualizations and their corresponding
        integer values.
    (2) The possible values for moranBins is in [HH, LH, LL, HL, ""]
        HH = High-High Value, LH = Low-High Value, 
        LL = Low-Low Value, HL = High-Low Value
        "" = Insignificant Cluster-Outlier value
    """

    def __init__(self, ssdo, varName, outputFC, wType,
                 weightsFile = None, concept = "EUCLIDEAN",
                 rowStandard = True, threshold = None,
                 exponent = 1.0, permutations = None, 
                 applyFDR = False):

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
        rowStandard = self.rowStandard
        weightsFile = self.weightsFile
        swmFileBool = self.swmFileBool
        masterField = ssdo.masterField

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
                    ARCPY.AddIDMessage("Warning", 717)

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
        rowStandard = self.rowStandard
        numObs = self.numObs
        master2Order = self.master2Order
        masterField = ssdo.masterField
        weightsFile = self.weightsFile

        #### Assure that Variance is Larger than Zero ####
        yVar = NUM.var(self.y)
        if NUM.isnan(yVar) or yVar <= 0.0:
            ARCPY.AddIDMessage("Error", 906)
            raise SystemExit()

        #### Create Deviation Variables ####
        self.yBar = NUM.mean(self.y)
        self.yDev = self.y - self.yBar
        self.nm1 = numObs - 1.
        self.nm2 = numObs - 2.
        self.nm12 = self.nm1 * self.nm2
        yDev2 = self.yDev**2.0
        yDev2Norm = yDev2 / self.nm1
        self.yDev2NormSum = sum(yDev2Norm)
        yDev4 = self.yDev**4.0
        yDev4Norm = yDev4 / self.nm1
        yDev4NormSum = sum(yDev4Norm)
        self.b2i = yDev4NormSum / (self.yDev2NormSum**2.0)

        #### Create Base Data Structures/Variables #### 
        self.li = NUM.zeros(numObs)
        self.ei = NUM.zeros(numObs)
        self.vi = NUM.zeros(numObs)
        self.zi = NUM.zeros(numObs)
        self.pVals = NUM.ones(numObs)
        if self.permutations:
            self.pseudoPVals = NUM.ones(numObs)
        self.moranInfo = {}

        #### Keep Track of Features with No Neighbors ####
        self.idsNoNeighs = []

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
                    ARCPY.AddIDMessage("Error", 842, numObs, N)
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
                gaSearch.init_nearest(threshold, 0, gaConcept)
            iterVals = range(numObs)
            N = numObs
            neighWeights = ARC._ss.NeighborWeights(gaTable, gaSearch,
                                                 weight_type = wType,
                                                 exponent = exponent,
                                          row_standard = rowStandard)

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
                                                     self.yDev, 
                                                     rowStandard = rowStandard,
                                                     isSubSet = isSubSet)
                    includeIt = True
                else:
                    includeIt = False

            elif self.weightsFile and not self.swmFileBool:
                #### Text Weights ####
                masterID = i
                includeIt = True
                rowInfo = WU.getWeightsValuesText(masterID, master2Order,
                                                  weightDict, self.yDev)

            elif wType in [4, 5]:
                #### Polygon Contiguity ####
                masterID = i
                includeIt = True
                rowInfo = WU.getWeightsValuesCont(masterID, master2Order,
                                                  contDict, self.yDev, 
                                                  rowStandard = rowStandard)

            else:
                #### Distance Based ####
                masterID = gaTable[i][0]
                includeIt = True
                rowInfo = WU.getWeightsValuesOTF(neighWeights, i, self.yDev)

            #### Subset Boolean for SWM File ####
            if includeIt:
                #### Parse Row Info ####
                orderID, yiDev, nhIDs, nhVals, weights = rowInfo

                #### Assure Neighbors Exist After Selection ####
                nn, nhIDs, nhVals, weights = ni.processInfo(masterID, nhIDs, 
                                                            nhVals, weights)

                if nn:
                    #### Calculate Local I ####
                    self.calculateLI(orderID, yiDev, 
                                    nhVals, weights)
                
            ARCPY.SetProgressorPosition()

        #### Clean Up ####
        if self.swmFileBool:
            swm.close()

        #### Report on Features with No Neighbors ####
        ni.reportNoNeighbors()
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

        #### Calculate FDR and Moran Bins ####
        toolMSG = ARCPY.GetIDMessage(84474)
        if self.applyFDR:
            #### Set Bins Using FDR ####
            msg = ARCPY.GetIDMessage(84472).format(toolMSG)
            ARCPY.SetProgressor("default", msg)
            fdrBins = STATS.fdrTransform(pv, self.li)
            self.moranBins = STATS.moranBinFromPVals(pv, self.moranInfo, 
                                                     fdrBins = fdrBins)
        else:
            msg = ARCPY.GetIDMessage(84473).format(toolMSG)
            ARCPY.SetProgressor("default", msg)
            self.moranBins = STATS.moranBinFromPVals(pv, self.moranInfo)

    def calculateLI(self, orderID, yiDev, nhVals, weights):
        """Calculates Local I for a given feature.
        
        INPUTS:
        orderID (int): order in corresponding numpy value arrays
        yiDev (float): value for given feature
        nhVals (array, nn): values for neighboring features (1)
        weights (array, nn): weight values for neighboring features (1)

        NOTES:
        (1)  nn is equal to the number of neighboring features        
        """

        sumW = weights.sum()
        sumWSquared = sumW**2.0
        sumW2 = (weights**2.0).sum()
        totalVal = yiDev / self.yDev2NormSum
        lagVal = (nhVals * weights).sum()
        liVal = totalVal * lagVal 
        eiVal = -1. * (sumW / self.nm1)
        eiVal2 = eiVal**2

        #### Variance, Randomization ####
        v1 = (sumW2 * (self.numObs - self.b2i)) / self.nm1
        v2 = sumWSquared / (self.nm1**2.)
        v3 = (sumWSquared - sumW2) * ((2. * self.b2i) - self.numObs)
        viVal = v1 + v3 / self.nm12 - v2
        ziVal = (liVal - eiVal) / (viVal**.5)
        pVal = STATS.zProb(ziVal, type = 2)

        #### Assign To Result Vectors ####
        self.li[orderID] = liVal
        self.ei[orderID] = eiVal
        self.vi[orderID] = viVal
        self.zi[orderID] = ziVal
        self.pVals[orderID] = pVal

        #### Store Info For Binning ####
        clusterBool = ziVal > 0
        localGlobalBool = lagVal >= 0
        featureGlobalBool = yiDev >= 0
        self.moranInfo[orderID] = (clusterBool, 
                                   localGlobalBool, 
                                   featureGlobalBool)

        #### Do Permutations ####
        if self.permutations:
            numNHS = len(nhVals)
            randomInts = RAND.random_integers(0, self.numObs-1,
                                              (self.permutations, numNHS))
            nhValsPerm = self.yDev[randomInts]
            lagValsPerm = (nhValsPerm * weights).sum(1)
            liValsPerm = totalVal * lagValsPerm
            pseudoP = STATS.pseudoPValue(liVal, liValsPerm)
            self.pseudoPVals[orderID] = pseudoP

    #def calculateBin(self, orderID, ziVal, yiVal, nhVals, weights):
    #    """Assigns a feature to Local Moran's I Cluster-Outlier Bins.
    #    
    #    INPUTS:
    #    orderID (int): order in corresponding numpy value arrays
    #    ziVal (float): z-value for given feature
    #    yiVal (float): value for given feature\
    #    nhVals (array, nn): values for neighboring features (1)
    #    weights (array, nn): weight values for neighboring features (1)

    #    NOTES:
    #    (1)  nn is equal to the number of neighboring features        
    #    """

    #    sumW = weights.sum()
    #    localSum = NUM.sum(nhVals * weights)
    #    localMean =  localSum / (sumW * 1.0)
    #    mBin = UTILS.returnMoranBin(ziVal, yiVal, 
    #                                self.yBar, localMean)
    #    self.moranBins[orderID] = mBin

    def setNullValues(self, idsNoNeighs):
        """Set no neighbor data for a given feature (1).
        
        INPUTS:
        idsNoNeighs (list): unique ID values that have no neighbors
        
        NOTES:
        (1)   The no neighbor result differs for shapefiles as it has no NULL
              value capabilities.  
        """

        for id in idsNoNeighs:
            orderID = self.ssdo.master2Order[id]
            if self.outShapeFileBool:
                self.li[orderID] = 0.0
                self.ei[orderID] = 0.0
                self.vi[orderID] = 0.0
                self.zi[orderID] = 0.0
                self.pVals[orderID] = 1.0
                if self.permutations:
                    self.pseudoPVals[orderID] = 1.0
            else:
                self.li[orderID] = NUM.nan
                self.ei[orderID] = NUM.nan
                self.vi[orderID] = NUM.nan
                self.zi[orderID] = NUM.nan
                self.pVals[orderID] = NUM.nan
                if self.permutations:
                    self.pseudoPVals[orderID] = NUM.nan

    def outputResults(self):
        """Creates output feature class for Local I."""

        #### Prepare Derived Variables for Output Feature Class ####
        outPath, outName = OS.path.split(self.outputFC)
        fieldOrder = UTILS.getFieldNames(liFieldNames, outPath)
        fieldData = [self.li, self.zi, self.pVals]

        #### Add Pseudo-P Field ####
        if self.permutations:
            fieldOrder.append(liPseudoFieldName)
            fieldData.append(self.pseudoPVals)

        #### Add CO Type Field ####
        fieldOrder.append(liCOFieldName)
        whereNull = NUM.where(self.pVals == NUM.nan)[0]
        if len(whereNull):
            outBins = list(self.moranBins)
            for ind in whereNull:
                outBins[ind] = NUM.nan
            fieldData.append(outBins)
        else:
            fieldData.append(self.moranBins)

        #### Create Alias Field Names ####
        if self.wType == 8:
            addString = OS.path.basename(self.weightsFile)
            rowStandard = False
        elif self.wType in [0, 1, 7]:
            if self.maxSet:
                addString = "0"
            else:
                addString = str(int(self.threshold))
            rowStandard = self.rowStandard
        else:
            addString = None
            rowStandard = self.rowStandard

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
            if fieldName == liCOFieldName:
                fType = "TEXT"
                length = 2
            else:
                fType = "DOUBLE"
                length = None
            candidateField = SSDO.CandidateField(fieldName, fType, 
                                                 fieldData[fieldInd],
                                                 alias = aliasList[fieldInd],
                                                 length = length)
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

        outFieldSet = fieldOrder[0:3] + [fieldOrder[-1]]
        return outFieldSet

    def renderResults(self):
        #### Set the Default Symbology ####
        params = ARCPY.gp.GetParameterInfo()
        try:
            renderType = UTILS.renderType[self.ssdo.shapeType.upper()]
            renderLayerFile = liRenderDict[renderType]
            templateDir = OS.path.dirname(OS.path.dirname(SYS.argv[0]))
            fullRLF = OS.path.join(templateDir, "Templates", 
                                   "Layers", renderLayerFile)
            params[2].Symbology = fullRLF 
        except:
            ARCPY.AddIDMessage("WARNING", 973)

if __name__ == "__main__":
    setupLocalI()
