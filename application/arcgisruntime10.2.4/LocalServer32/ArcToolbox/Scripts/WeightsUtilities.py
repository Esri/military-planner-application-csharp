"""
Source Name:   WeightsUtilities.py
Version:       ArcGIS 10.1
Author:        Environmental Systems Research Institute Inc.
Description:   Utilities for creating, managing and utilizing 
               spatial weights matrix files.
"""

################### Imports ########################
import os as OS
import collections as COLL
import numpy as NUM
import arcgisscripting as ARC
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.analysis as ANA
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO
import gapy as GAPY
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

################## Dispatch ########################

weightDispatch = {'INVERSE_DISTANCE': 0, 
                  'FIXED_DISTANCE': 1, 
                  'K_NEAREST_NEIGHBORS': 2, 
                  'DELAUNAY_TRIANGULATION': 3,
                  'CONTIGUITY_EDGES_ONLY': 4,
                  'CONTIGUITY_EDGES_CORNERS': 5, 
                  'CONVERT_TABLE': 6,
                  'ZONE_OF_INDIFFERENCE': 7,
                  'GET_SPATIAL_WEIGHTS_FROM_FILE': 8,
                  'SPACE_TIME_WINDOW': 9,
                  'NETWORK': 10,
                  'UNKNOWN': -1}

wTypeDispatch = {0: 'INVERSE_DISTANCE', 
                 1: 'FIXED_DISTANCE', 
                 2: 'K_NEAREST_NEIGHBORS', 
                 3: 'DELAUNAY_TRIANGULATION',
                 4: 'CONTIGUITY_EDGES_ONLY',
                 5: 'CONTIGUITY_EDGES_CORNERS',
                 6: 'CONVERT_TABLE',
                 7: 'ZONE_OF_INDIFFERENCE',
                 8: 'GET_SPATIAL_WEIGHTS_FROM_FILE',
                 9: 'SPACE_TIME_WINDOW',
                 10: 'NETWORK',
                 -1: 'UNKNOWN'}

conceptDispatch = {'EUCLIDEAN': 'EUCLIDEAN',
                   'MANHATTAN': 'MANHATTAN',
                   "EUCLIDEAN_DISTANCE": "EUCLIDEAN",
                   "MANHATTAN_DISTANCE": "MANHATTAN"}

convertConcept = {
"INVERSE_DISTANCE": 'INVERSE_DISTANCE',
"INVERSE_DISTANCE_SQUARED": 'INVERSE_DISTANCE',
"FIXED_DISTANCE_BAND": "FIXED_DISTANCE",
"ZONE_OF_INDIFFERENCE": "ZONE_OF_INDIFFERENCE",
"POLYGON_CONTIGUITY_(FIRST_ORDER)": "CONTIGUITY_EDGES_ONLY",
"CONTIGUITY_EDGES_ONLY": "CONTIGUITY_EDGES_ONLY",
"CONTIGUITY_EDGES_CORNERS": "CONTIGUITY_EDGES_CORNERS",
"GET_SPATIAL_WEIGHTS_FROM_FILE": "GET_SPATIAL_WEIGHTS_FROM_FILE"
}

gaTypes = { 'INVERSE_DISTANCE': True,
            'FIXED_DISTANCE': True,
            'ZONE_OF_INDIFFERENCE': True,
            'K_NEAREST_NEIGHBORS': True,
            'DELAUNAY_TRIANGULATION': True,
            'SPACE_TIME_WINDOW': True,
            'CONTIGUITY_EDGES_ONLY': False,
            'CONTIGUITY_EDGES_CORNERS': False,
            'CONVERT_TABLE': False,
            'GET_SPATIAL_WEIGHTS_FROM_FILE': False }

concept2Alias = {0: "IDW", 1: "Fixed", 4: "Contiguity", 7: "ZOI"}

warnNumberOfNeighbors = 1000
maxNumberOfNeighbors = None
maxDefaultNumNeighs = 500

############### Spatial Weights Classes and Functions ################

def reportNoNeighborsGeneral(numObs, noNeighs, masterField, 
                             failAllNoNeighs = True):
    """Report if Any Features Have No Neighbors."""

    #### All Features Have No Neighbors ####
    if len(noNeighs) == numObs:
        if failAllNoNeighs:
            ARCPY.AddIDMessage("Error", 908)
            raise SystemExit()
        else:
            #### Technically Allowed for Hot-Spot Analysis ####
            ARCPY.AddIDMessage("Warning", 908)

    #### Report First With No Neighbors ####
    countNoNeighs = len(noNeighs)
    if countNoNeighs:
        noNeighs.sort()
        if countNoNeighs > 30:
            noNeighs = noNeighs[0:30]
        
        ERROR.warningNoNeighbors(numObs, countNoNeighs, noNeighs, masterField)

class NeighborInfo(object):

    def __init__(self, masterField, silent = False):
        self.masterField = masterField
        self.silent = silent
        self.warnNeighsExceeded = False
        self.maxNeighsExceeded = False
        self.idsWarn = []
        self.idsMax = []
        self.idsNoNeighs = []
        self.numObs = 0

    def processInfo(self, masterID, nhIDs, nhVals, weights):
        self.numObs += 1
        nn = len(nhIDs)
        if nn:
            #### Warn Number of Neighs ####
            if nn > warnNumberOfNeighbors:
                self.idsWarn.append(masterID)
                if not self.warnNeighsExceeded:
                    self.warnNeighsExceeded = True
                    if not self.silent:
                        ARCPY.AddIDMessage("WARNING", 1420, 
                                     warnNumberOfNeighbors)

            #### Truncate to Max Number of Neighs ####
            if maxNumberOfNeighbors and nn > maxNumberOfNeighbors: 
                self.idsMax.append(masterID)
                if not self.maxNeighsExceeded:
                    self.maxNeighsExceeded = True
                    if not self.silent:
                        ARCPY.AddIDMessage("WARNING", 1421, 
                                      maxNumberOfNeighbors)

                nhIDs = nhIDs[0:maxNumberOfNeighbors]
                nhVals = nhVals[0:maxNumberOfNeighbors]
                weights = weights[0:maxNumberOfNeighbors]
                nn = maxNumberOfNeighbors
        else:
            #### No Neighbors ####
            self.idsNoNeighs.append(masterID)

        return nn, nhIDs, nhVals, weights

    def reportWarnings(self, numFeatures = 30):
        if len(self.idsWarn):
            self.idsWarn.sort()
            idsOut = [ str(i) for i in self.idsWarn[0:numFeatures] ]
            idsOut = ", ".join(idsOut)
            ARCPY.AddIDMessage("WARNING", 1422, self.masterField, idsOut)

    def reportMaximums(self, numFeatures = 30):
        if len(self.idsMax):
            self.idsMax.sort()
            idsOut = [ str(i) for i in self.idsMax[0:numFeatures] ]
            idsOut = ", ".join(idsOut)
            ARCPY.AddIDMessage("WARNING", 1423, self.masterField, idsOut)

    def reportNoNeighbors(self, failAllNoNeighs = True):
        """Report if Any Features Have No Neighbors."""

        #### All Features Have No Neighbors ####
        if len(self.idsNoNeighs) == self.numObs:
            if failAllNoNeighs:
                ARCPY.AddIDMessage("Error", 908)
                raise SystemExit()
            else:
                #### Technically Allowed for Hot-Spot Analysis ####
                ARCPY.AddIDMessage("Warning", 908)

        #### Report First With No Neighbors ####
        countNoNeighs = len(self.idsNoNeighs)
        if countNoNeighs:
            self.idsNoNeighs.sort()
            noNeighs = self.idsNoNeighs[0:30]
            ERROR.warningNoNeighbors(self.numObs, countNoNeighs, 
                                     noNeighs, self.masterField)

class SWMWriter(object):

    def __init__(self, swmFile, masterField, spatialRefName, numObs, 
                 rowStandard, inputFC = "#", wType = -1, 
                 distanceMethod = "#", exponent = "#", 
                 threshold = "#", numNeighs = "#",
                 inputTable = "#", timeField = "#", 
                 timeType = "#", timeValue = "#",
                 inputNet = "#", impedanceField = "#",
                 barrierFC = "#", uturnPolicy = "#",
                 restrictions = "#", useHierarchy = "#",
                 searchTolerance = "#", addConcept = "#",
                 forceFixed = False):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())
        self.setHeader()

        #### Set SWM Writing Class ####
        if self.fixedWeights:
            self.swm = FixedSWMWriter(self.fo, masterField, 
                                 rowStandard = rowStandard)
        else:
            self.swm = VariableSWMWriter(self.fo, masterField,
                                    rowStandard = rowStandard)

    def setHeader(self):

        #### Create File Writing Object ####
        self.fo = UTILS.openFile(self.swmFile, "wb")

        #### Assign Fixed/Variable Weighting Type ####
        if self.wType in [1, 2, 3, 4, 5, 9]:
            self.fixedWeights = True
        else:
            if self.forceFixed:
                self.fixedWeights = True
            else:
                self.fixedWeights = False

        #### Key Word Arguements ####
        if self.exponent != "#":
            if not (self.exponent % 1):
                self.exponent = "%i" % self.exponent
            else:
                self.exponent = UTILS.formatValue(self.exponent, "%0.4f")
        if self.threshold != "#":
            self.threshold = UTILS.formatValue(self.threshold)
        if self.numNeighs != "#":
            self.numNeighs = "%i" % self.numNeighs
        if self.timeValue != "#":
            self.timeValue = "%i" % self.timeValue
        if self.useHierarchy != "#":
            self.useHierarchy = str(self.useHierarchy)

        #### Create Header ####
        header = ["VERSION@" + "10.1", 
                  "UNIQUEID@" + self.masterField.upper(), 
                  "SPATIALREFNAME@" + self.spatialRefName,
                  "INPUTFC@" + self.inputFC, "WTYPE@" + "%i" % self.wType,
                  "DISTANCEMETHOD@" + self.distanceMethod, 
                  "EXPONENT@" + self.exponent, "THRESHOLD@" + self.threshold,
                  "NUMNEIGHS@" + self.numNeighs, "INPUTTABLE@" + self.inputTable, 
                  "TIMEFIELD@" + self.timeField.upper(), "TIMETYPE@" + self.timeType,
                  "TIMEVALUE@" + self.timeValue, "INPUTNET@" + self.inputNet, 
                  "IMPEDANCEFIELD@" + self.impedanceField.upper(), 
                  "BARRIERFC@" + self.barrierFC, "UTURNPOLICY@" + self.uturnPolicy,
                  "RESTRICTIONS@" + self.restrictions, 
                  "USEHIERARCHY@" + self.useHierarchy,
                  "SEARCHTOLERANCE@" + self.searchTolerance,
                  "ADDCONCEPT@" + self.addConcept,
                  "FIXEDWEIGHTS@" + str(self.fixedWeights)]

        header = ";".join(header) + "\n"
        header = NUM.array([header], '<c')
        header.tofile(self.fo)
        weightsInfo = NUM.empty((2,), '<l')
        weightsInfo[0] = self.numObs
        weightsInfo[1] = self.rowStandard
        weightsInfo.tofile(self.fo)
        self.header = header

    def close(self):
        """Closes SWM Output File Pointer."""
        self.fo.close()

    def report(self, show = True, additionalInfo = []):
        """Report Spatial Weights Matrix Characteristics."""

        #### Get Info ####
        numObs = self.numObs
        numNonZero = self.swm.numNonZero
        minNumNeighs = self.swm.minNumNeighs
        maxNumNeighs = self.swm.maxNumNeighs

        #### Create Extra Result Values ####
        percNonZero = (numNonZero / ((numObs * 1.0)**2)) * 100  
        avgNumNeighs = numNonZero / (numObs * 1.0)

        #### Create Output Table ####
        header =  ARCPY.GetIDMessage(84137)
        row1 = [  ARCPY.GetIDMessage(84138), numObs ]
        row2 = [  ARCPY.GetIDMessage(84139), LOCALE.format("%0.2f", percNonZero) ]
        row3 = [  ARCPY.GetIDMessage(84140), LOCALE.format("%0.2f", avgNumNeighs) ]
        row4 = [  ARCPY.GetIDMessage(84141), minNumNeighs ]
        row5 = [  ARCPY.GetIDMessage(84142), maxNumNeighs ]
        total = [row1,row2,row3,row4,row5]
        self.info = UTILS.outputTextTable(total, header = header, pad = 1)

        #### Additional Footnotes ####
        if len(additionalInfo):
            self.info += "\n"
            addLines = "\n".join(additionalInfo)
            self.info += addLines + "\n"

        if show:
            ARCPY.AddMessage(self.info)

    def reportNoNeighbors(self):
        """Report if Any Features Have No Neighbors."""

        self.swm.ni.reportNoNeighbors()

    def reportLargeSWM(self):
        """Returns a warning id the number of non-zero links > 20 million."""

        if self.swm.numNonZero >= 20000000:
            ARCPY.AddIDMessage("WARNING", 1014)

    def reportNeighInfo(self):
        """Reports results from Neighbor Info Class."""
    
        self.swm.ni.reportNoNeighbors()
        self.swm.ni.reportWarnings()
        self.swm.ni.reportMaximums()

class VariableSWMWriter(object):
    """File Reading Class for Spatial Weights Matrices with variable weight
    values; e.g. Inverse Distance.  This is also how all SWM files were
    stored/read prior to the 10.1 release.
    """

    def __init__(self, fo, masterField, rowStandard = True):
        self.fo = fo
        self.rowStandard = rowStandard
        self.numNonZero = 0 
        self.minNumNeighs = 99999999
        self.maxNumNeighs = 0

        #### Set Neighbor Info Class ####
        self.ni = NeighborInfo(masterField)

    def writeEntry(self, masterID, neighs, weights):
        #### Warn/Truncate to Warn/Max Number of Neighs ####
        nn, neighs, nhVals, weights = self.ni.processInfo(masterID, neighs, 
                                                          [], weights)

        #### Write Master ID and Number Of Neighbors ####
        rowInfo = NUM.empty((2,), '<l')
        rowInfo[0] = masterID
        rowInfo[1] = nn
        rowInfo.tofile(self.fo)
        if nn != 0:
            #### Write Neighbor IDs ####
            neighs = NUM.array(neighs, '<l')
            neighs.tofile(self.fo)

            #### Write Spatial Weights ####
            weights = NUM.array(weights, '<d')
            sumUnstandard = weights.sum() * 1.0
            if self.rowStandard:
                weights = weights / sumUnstandard
            weights.tofile(self.fo)
            
            #### Write Sum of Unstandardized Weights ####
            sumUnstandard = NUM.array(sumUnstandard, '<d')
            sumUnstandard.tofile(self.fo)

        #### Update Weight Chars ####
        self.numNonZero += nn
        if nn < self.minNumNeighs:
            self.minNumNeighs = nn
        if nn > self.maxNumNeighs:
            self.maxNumNeighs = nn

        return nn

class FixedSWMWriter(object):
    """File Reading Class for Spatial Weights Matrices with variable weight
    values; e.g. Inverse Distance.  This is also how all SWM files were
    stored/read prior to the 10.1 release.
    """

    def __init__(self, fo, masterField, rowStandard = True):
        self.fo = fo
        self.rowStandard = rowStandard
        self.numNonZero = 0 
        self.minNumNeighs = 99999999
        self.maxNumNeighs = 0

        #### Set Neighbor Info Class ####
        self.ni = NeighborInfo(masterField)

    def writeEntry(self, masterID, neighs, weights):
        #### Warn/Truncate to Warn/Max Number of Neighs ####
        nn, neighs, nhVals, weights = self.ni.processInfo(masterID, neighs, 
                                                          [], weights)

        #### Write Master ID and Number Of Neighbors ####
        rowInfo = NUM.empty((2,), '<l')
        rowInfo[0] = masterID
        rowInfo[1] = nn
        rowInfo.tofile(self.fo)
        if nn != 0:
            #### Write Neighbor IDs ####
            neighs = NUM.array(neighs, '<l')
            neighs.tofile(self.fo)

            #### Write Spatial Weights ####
            weights = NUM.array(weights, '<d')
            sumUnstandard = weights.sum() * 1.0
            if self.rowStandard:
                weights = weights / sumUnstandard

            #### Fixed Weights - Only Write Single Value ####
            weights = weights[0]
            weights.tofile(self.fo)
            
            #### Write Sum of Unstandardized Weights ####
            sumUnstandard = NUM.array(sumUnstandard, '<d')
            sumUnstandard.tofile(self.fo)

        #### Update Weight Chars ####
        self.numNonZero += nn
        if nn < self.minNumNeighs:
            self.minNumNeighs = nn
        if nn > self.maxNumNeighs:
            self.maxNumNeighs = nn

        return nn

class SWMReader(object):
    """Calculates Global Morans I, Incremental Distance Version:

    INPUTS:
    inputFC (str): path to the input feature class
    varName (str): name of analysis field
    nIncrements {int, 10}: number of distance bands
    begDist {float, None}: starting distance for analysis
    dIncrement {float, None}: increase in distance per increment
    concept: {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN 
    rowStandard {bool, True}: row standardize weights?

    ATTRIBUTES:
    numObs (int): number of features in analysis
    y (array, numObs x 1): vector of field values

    METHODS:
    report: reports results as a printed message or to a file
    createOutput: creates an output table for Moran's I results
    """

    def __init__(self, swmFile):

        self.swmFile = swmFile
        self.fo = UTILS.openFile(swmFile, "rb")
        self.header = self.fo.readline().strip().split(";")
        if self.header[0][0:8] == "VERSION@":
            #### New Header Format ####
            self.readNewFormat()
        else:
            #### < 10.1 Format ####
            self.readOldFormat()

        #### Set Read Entry Class ####
        if self.fixedWeights:
            self.swm = FixedSWMReader(self.fo)
        else:
            self.swm = VariableSWMReader(self.fo)

    def close(self):
        self.fo.close()

    def scanRest(self):
        self.numObs, self.rowStandard = NUM.fromfile(self.fo, '<l', count = 2)
        self.rowBoolStr = str(self.rowStandard == True)

    def readOldFormat(self):
        self.masterField, self.spatialRefName = self.header
        self.version = "< 10.1"
        self.inputFC = "#"
        self.wType = -1
        self.distanceMethod = "#"
        self.exponent = "#"
        self.threshold = "#"
        self.numNeighs = "#"
        self.inputTable = "#"
        self.timeField = "#"
        self.timeType = "#"
        self.timeValue = "#"
        self.inputNet = "#"
        self.impedanceField = "#"
        self.barrierFC = "#"
        self.uturnPolicy = "#"
        self.restrictions = "#"
        self.useHierarchy = "#"
        self.searchTolerance = "#"
        self.addConcept = "#"
        self.fixedWeights = False
        self.scanRest()

    def readNewFormat(self):
        headerDict = {}
        for headerInfo in self.header: 
            headerKey, headerVal = headerInfo.split("@")
            headerDict[headerKey] = headerVal

        self.version = headerDict["VERSION"]
        self.masterField = headerDict["UNIQUEID"]
        self.spatialRefName = headerDict["SPATIALREFNAME"]
        self.inputFC = headerDict["INPUTFC"]
        self.wType = int(headerDict["WTYPE"])
        self.distanceMethod = headerDict["DISTANCEMETHOD"]
        self.exponent = headerDict["EXPONENT"]
        self.threshold = headerDict["THRESHOLD"]
        self.numNeighs = headerDict["NUMNEIGHS"]
        self.inputTable = headerDict["INPUTTABLE"]
        self.timeField = headerDict["TIMEFIELD"]
        self.timeType = headerDict["TIMETYPE"]
        self.timeValue = headerDict["TIMEVALUE"]
        self.inputNet = headerDict["INPUTNET"]
        self.impedanceField = headerDict["IMPEDANCEFIELD"]
        self.barrierFC = headerDict["BARRIERFC"]
        self.uturnPolicy = headerDict["UTURNPOLICY"]
        self.restrictions = headerDict["RESTRICTIONS"]
        self.useHierarchy = headerDict["USEHIERARCHY"]
        self.searchTolerance = headerDict["SEARCHTOLERANCE"]
        self.addConcept = headerDict["ADDCONCEPT"]
        if headerDict.has_key("FIXEDWEIGHTS"):
            self.fixedWeights = headerDict["FIXEDWEIGHTS"].upper() == 'TRUE' 
        else:
            self.fixedWeights = False
        self.scanRest()

    def description(self, show = True):
        header = ARCPY.GetIDMessage(84378)
        strConcept = wTypeDispatch[self.wType]

        #### Values Across All SWM Files ####
        labels = [84382, 84233, 84359, 84381,
                  84379, 84057, 84236,
                  84234, 84406]

        values = [self.version, self.inputFC, self.masterField, self.swmFile,
                  self.spatialRefName, self.numObs, self.rowStandard,
                  strConcept, str(self.fixedWeights)]

        if self.wType == 0:
            #### Inverse Distance ####
            labels += [84235, 84383, 84237]
            values += [self.distanceMethod, self.exponent, self.threshold]
        elif self.wType == 1:
            #### Fixed Distance ####
            labels += [84235, 84237]
            values += [self.distanceMethod, self.threshold]
        elif self.wType in [2, 4, 5]:
            #### KNN or Polygon Contiguity ####
            labels += [84235, 84362]
            values += [self.distanceMethod, self.numNeighs]
        elif self.wType in [6, 8]:
            #### Convert from Table ####
            labels += [84384]
            values += [self.inputTable]
        elif self.wType == 9:
            #### Space-Time ####
            labels += [84235, 84237, 84385, 84386, 84387]
            values += [self.distanceMethod, self.threshold, self.timeField,
                       self.timeType, self.timeValue]
        elif self.wType == 10:
            labels += [84388, 84389, 84390, 84391, 84392, 84393,
                       84394, 84395, 84396, 84397, 84383]
            values += [self.inputNet, self.impedanceField, self.threshold,
                       self.numNeighs, self.barrierFC, self.uturnPolicy,
                       self.restrictions, self.useHierarchy, 
                       self.searchTolerance, self.addConcept,
                       self.exponent]
        else:
            #### Delaunay and Unknown ####
            pass

        #### Finalize Table ####
        total = []
        for ind, lab in enumerate(labels):
            labPlus = UTILS.addColon(ARCPY.GetIDMessage(lab))
            val = values[ind]
            total.append([labPlus, val])
        descTable = UTILS.outputTextTable(total, header = header, pad = 1)

        #### Print Results ####
        if show:
            ARCPY.AddMessage(descTable)

        return descTable

    def reportNoNeighbors(self):
        """Report if Any Features Have No Neighbors."""

        reportNoNeighborsGeneral(self.numObs, self.swm.noNeighs,
                                 self.masterField)


class VariableSWMReader(object):
    """File Reading Class for Spatial Weights Matrices with variable weight
    values; e.g. Inverse Distance.  This is also how all SWM files were
    stored/read prior to the 10.1 release.
    """

    def __init__(self, fo):
        self.fo = fo
        self.noNeighs = []

    def readEntry(self):
        try:
            masterID, nn = NUM.fromfile(self.fo, '<l', count = 2)
            if nn != 0:
                nhs = NUM.fromfile(self.fo, '<l', count = nn)
                weights = NUM.fromfile(self.fo, '<d', count = nn)
                sumUnstandard = NUM.fromfile(self.fo, '<d', count = 1)
            else:
                nhs = None
                weights = None
                sumUnstandard = None
                self.noNeighs.append(masterID)
        except:
            #### Invalid Format, Close File Pointer and Throw Error ####
            self.fo.close()

            ARCPY.AddIDMessage("Error", 919)
            raise SystemExit()

        return masterID, nn, nhs, weights, sumUnstandard

class FixedSWMReader(object):
    """File Reading Class for Spatial Weights Matrices with variable weight
    values; e.g. Inverse Distance.  This is also how all SWM files were
    stored/read prior to the 10.1 release.
    """

    def __init__(self, fo):
        self.fo = fo
        self.noNeighs = []

    def readEntry(self):
        try:
            masterID, nn = NUM.fromfile(self.fo, '<l', count = 2)
            if nn != 0:
                nhs = NUM.fromfile(self.fo, '<l', count = nn)
                weight = NUM.fromfile(self.fo, '<d', count = 1)
                weights = NUM.ones(nn) * weight
                sumUnstandard = NUM.fromfile(self.fo, '<d', count = 1)
            else:
                nhs = None
                weights = None
                sumUnstandard = None
                self.noNeighs.append(masterID)
        except:
            #### Invalid Format, Close File Pointer and Throw Error ####
            self.fo.close()

            ARCPY.AddIDMessage("Error", 919)
            raise SystemExit()

        return masterID, nn, nhs, weights, sumUnstandard

############### General Functions ###############

def gaTable(inputFC, fieldNames = None, spatRef = None, warnings = 30):
    """Creates a GA Data Structure for Neighborhood Searching.

    inputFC (str): path to the input feature class
    fieldNames (list): names of fields to include in table
    spatRef {str, None}: spatial reference string
    warnings {int, 30}: number of errors to return
    """
    
    #### Change Layer Files to Feature Layer ####
    tempName, extension = OS.path.splitext(inputFC)
    if extension.upper() == ".LYR":
        tempFeatures = True
        inFeatures = UTILS.returnScratchName("TempFeaturesForGAPY")
        DM.MakeFeatureLayer(inputFC, inFeatures)
    else:
        tempFeatures = False
        inFeatures = inputFC

    #### Create Structure and Parameter Info ####
    gaTable = GAPY.ga_table()
    gaTable.max_warnings = warnings
    if fieldNames:
        fieldNames = tuple(fieldNames)
    else:
        fieldNames = ()

    #### Try and Load the Feature Class ####
    loadInfo = None
    strError = None
    try:
        loadInfo = gaTable.load(inFeatures, fieldNames, spatRef)

    except (TypeError, RuntimeError), strError:
        pass

    finally:
        #### Report Failure Message ####
        if strError:
            msg = strError[0]
            if msg == "cannot find input field":
                #### Field(s) Invalid ####
                ARCPY.AddIDMessage("ERROR", 369)
                raise SystemExit()
            elif msg == "open FeatureClass/FeatureLayer":
                #### FC Invalid ####
                ARCPY.AddIDMessage("ERROR", 732, "Input Features", inputFC)
                raise SystemExit()
            else:
                #### Catchall/Unknown Error ####
                ARCPY.AddIDMessage("ERROR", 581)
                raise SystemExit()

    #### Delete Temporary Feature Layer ####
    if tempFeatures:
        UTILS.passiveDelete(inFeatures)

    return gaTable, loadInfo

def checkProfessionalLicense(spaceConcept):
    """Checks for Professional ArcGIS License for polygon contiguity.
    
    INPUTS:
    spaceConcept (str): conceptualization of spatial relationships
    """

    productInfo = ARCPY.ProductInfo()
    if productInfo not in ["ArcInfo", "ArcServer"]:
        ARCPY.AddIDMessage("Error", 844, spaceConcept)
        raise SystemExit()    

def createSpatialFieldAliases(fieldNames, addString = None, wType = None, 
                              exponent = 1.0, rowStandard = True):
    """Creates field aliases for the different concepts of spatial 
    relationships.

    INPUTS:
    fieldNames (list): list of base field names
    addString {str, None}: additional token to add to alias
    wType {int, None}: spatial conceptualization (1)
    exponent {float, 1.0}: distance decay
    rowStandard {bool, True}: row standardize weights?

    OUTPUT:
    aliases (list): field aliases

    NOTES:
    (1) See the wTypeDispatch dictionary in WeightsUtilities.py for a 
        complete list of spatial conceptualizations and their corresponding
        integer values.
    """

    aliases = []

    for field in fieldNames:
        alias = [field]
        try:
            conceptStr = concept2Alias[wType]
            if wType == 0:
                iExp = int(exponent)
                if iExp != 1:
                    conceptStr += "^" + str(iExp) 
            alias.append(conceptStr)
        except:
            pass

        if addString != None:
            alias.append(addString)
        if rowStandard:
            alias.append("RS")
        alias = " ".join(alias)
        aliases.append(alias)

    return aliases

def compareSpatialRefWeights(inRefName, outRefName):
    """Compares the names of two spatial reference objects to warn the
    user if spatial references different for SWM and output
    coordinate system.

    INPUTS:
    inRefName (str): name of spatial reference for input feature class. 
    outRefname (str): name of spatial reference defined for output.
    """
    
    if inRefName != outRefName:
        ARCPY.AddIDMessage("WARNING", 982, inRefName, outRefName)

def checkGeographicCoord(spatRefType, spaceConcept):
    """Check to see if the spatial reference type is Geographic
    Coordinate System, which is invalid for Inverse Distance and Zone of
    Indifference spatial concepts.

    INPUTS:
    spatRefType (str): spatial reference type
    spaceConcept (str): conceptualization fo spatial relationships
    """

    if spatRefType == "Geographic":
        ARCPY.AddIDMessage("WARNING", 981, spaceConcept)

def euclideanDistance(x0, x1, y0, y1):
    """Returns the Euclidean Distance between two points.

    INPUTS:
    x0 (float): xCoord for point 0
    x1 (float): xCoord for point 1
    y0 (float): yCoord for point 0
    y1 (float): yCoord for point 1
    """

    return NUM.sqrt( (x0 - x1)**2.0 + (y0 - y1)**2.0 ) 

def manhattanDistance(x0, x1, y0, y1):
    """Returns the Manhattan Distance between two points.

    INPUTS:
    x0 (float): xCoord for point 0
    x1 (float): xCoord for point 1
    y0 (float): yCoord for point 0
    y1 (float): yCoord for point 1
    """

    return abs(x0 - x1) + abs(y0 - y1)

def distance2Weight(distance, exponent = 1.0, wType = 0, threshold = None):
    """Returns a modified version of inverse distance for given 
    distance. (1)

    INPUTS:
    distance (float): previously calculated distance
    exponent (int, float): distance decay component
    wType (int): type of weight (see wTypeDispatch)

    OUTPUT:
    weight (float): calculated weight based on distance criteria.

    NOTES:
    (1)  Essentially, a zone of indifference with 1 as the 
         threshold distance.  I.e. any distance less that 1 is given a 
         weight of 1.  All others are inverse distance 1/d**exponent, 
         unless fixed is set to 1.... then all weights are 1.
    """

    if wType == 1:
        #### Fixed Distance ####
        weight = 1.0
    elif wType == 7:
        if threshold == None:
            weight = 1.0
        else:
            if distance > threshold:
                weight = 1.0 / ((distance - threshold) + 1.0)
            else:
                weight = 1.0
    else: 
        if distance <= 1.0:
            weight = 1.0
        else:
            weight = 1.0 / (distance**exponent)

    return weight

def checkDistanceThreshold(ssdo, threshold, weightType = 0, silent = False):
    """Checks whether search threshold is appropriate given the extent
    of the feature class and the concept of spatial relationship chosen.

    INPUTS:
    extent (str): string representation of extent (9.2 or GAPY version)
    threshold (float): given distance threshold for neighborhood search
    weightType {int, 0}: spatial conceptualization (1) (2)
    silent {bool, False}: show greater than max extent warnings?

    OUTPUT:
    threshold (float): threshold/threshold that is to be used in analysis
    maxSet (bool): was the threshold set to the max of the extent? 

    NOTES:
    (1) See the wTypeDispatch dictionary in WeightsUtilities.py for a 
        complete list of spatial conceptualizations and their corresponding
        integer values.
    (2) This method is only called for distanced based weights:
        0 = Inverse Distance
        1 = Fixed Distance
        7 = Zone of Indifference (ZOI)
    """

    maxSet = False

    if threshold < 0:
        #### Negative Values Not Valid ####
        ARCPY.AddIDMessage("ERROR", 933)
        raise SystemExit()

    softWarn = False
    if ssdo.useChordal:
        softMaxExtent = ssdo.sliceInfo.maxExtent
        hardMaxExtent = ARC._ss.get_max_gcs_distance(ssdo.spatialRef)
        if softMaxExtent < hardMaxExtent:
            maxExtent = softMaxExtent
            softWarn = True
        else:
            maxExtent = hardMaxExtent
    else:
        env = UTILS.Envelope(ssdo.extent)
        maxExtent = env.maxExtent

    if threshold == 0:
        if weightType in [1, 7]:
            #### Infinite Radius Not Valid For Fixed and ZOI ####
            ARCPY.AddIDMessage("ERROR", 928)
            raise SystemExit()
        else:
            #### Set to Max Extent for Inverse ####
            threshold = maxExtent 
            maxSet = True

    #### Assure that the Radius is Smaller than the Max Extent ####
    if threshold > maxExtent:
        if weightType in [1, 7]:
            #### Can Not be Greater or Equal to Extent ####
            #### Applies to Fixed (1) and ZOI (7) ####
            if ssdo.useChordal and not softWarn:
                ARCPY.AddIDMessage("ERROR", 1607)
                raise SystemExit()
            else:
                ARCPY.AddIDMessage("ERROR", 929)
                raise SystemExit()
        else:
            #### Set to Max Length of Extent for Inverse #### 
            if not silent:
                if ssdo.useChordal and not softWarn:
                    ARCPY.AddIDMessage("WARNING", 1607)
                    ARCPY.AddIDMessage("WARNING", 1608)
                else:
                    ARCPY.AddIDMessage("WARNING", 929)
                    ARCPY.AddIDMessage("WARNING", 946)
            threshold = maxExtent
            maxSet = True
    
    #### Assure that the Radius is Larger than 1000th Max Extent ####
    minimumRadius = (maxExtent * .001)
    if threshold < minimumRadius and threshold != 0:
        if weightType in [0, 1]:
            #### If Inverse or Fixed, Raise an Error ####
            ARCPY.AddIDMessage("ERROR", 897, threshold)
            raise SystemExit()
        else:
            #### Zone of Indifference, Set to One if Less ####
            if threshold < 1:
                threshold = 1

    ##### Increase Radius If MaxSet ####
    if maxSet and not ssdo.useChordal:
        threshold = threshold * 1.5

    return threshold, maxSet

def validateDistanceMethod(distanceMethodString, spatRef):
    sType = spatRef.type.upper()
    if sType == "GEOGRAPHIC":
        return "EUCLIDEAN", "euclidean"
    else:
        return distanceMethodString.upper(), distanceMethodString.lower()

def createThresholdDist(ssdo, concept = "EUCLIDEAN"):
    """Creates a default threshold distance for neighborhood searching.
    This function uses the GA table to find the nearest neighbor for
    each feature. (1)    

    INPUTS:
    gaTable (obj): instance of a GA Table
    concept {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN distance
    distanceInfo {obj, None}: instance of UTILS.DistanceInfo

    OUTPUT:
    threshold (float): default distance threshold

    NOTES:
    (1) The distance for each feature is calculated, and the maximum is 
        returned as the default threshold.  This function assumes the GA 
        Table has already been created.
    """

    #### Set Progressor for Search ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84144))

    #### Create k-Nearest Neighbor Search Type ####
    gaSearch = GAPY.ga_nsearch(ssdo.gaTable)
    ssConcept, gaConcept = validateDistanceMethod(concept, ssdo.spatialRef)
    gaSearch.init_nearest(0.0, 1, gaConcept)
    neighDist = ARC._ss.NeighborDistances(ssdo.gaTable, gaSearch)
    N = len(neighDist)
    threshold = 0.0
    sumDist = 0.0 

    #### Find Maximum Nearest Neighbor Distance ####
    for row in xrange(N):
        dij = neighDist[row][-1][0]
        if dij > threshold:
            threshold = dij
        sumDist += dij

        ARCPY.SetProgressorPosition()

    #### Increase For Rounding Error ####
    threshold = threshold * 1.0001
    avgDist = sumDist / (N * 1.0)

    #### Add Linear/Angular Units ####
    thresholdStr = ssdo.distanceInfo.printDistance(threshold)
    ARCPY.AddIDMessage("Warning", 853, thresholdStr)

    #### Chordal Default Check ####
    if ssdo.useChordal:
        hardMaxExtent = ARC._ss.get_max_gcs_distance(ssdo.spatialRef)
        if threshold > hardMaxExtent:
            ARCPY.AddIDMessage("ERROR", 1609)
            raise SystemExit()

    #### Clean Up ####
    del gaSearch
    
    return threshold, avgDist

def parseGAWarnings(gaWarnings):
    """Returns the Object ID for all features in a dataset that has bad
    records.

    INPUTS:
    gaWarnings (obj): GA Warnings Object

    OUTPUT:
    badRecs (list): list of bad records
    """

    badRecs = []
    for warning in gaWarnings:
        if warning[0] != 39999:
            badRecs.append( str(warning[1]) )

    return badRecs

def returnHeader(ssdo, weightsFile, swmFileBool = True):
    """Checks whether the masterField of a given spatial weights file 
    is in the given input feature class.

    INPUTS:
    inputFC (str): catalogue path to the table
    weightsFile (str): path to the spatial weights matrix file
    swmFileBool {bool, True}: is the weightsFile in *.swm format?

    OUTPUT:
    masterFieldName (str): name of the weights file unique ID field
    spatialRefName (str): spatial reference name
    """

    #### Obtain the Unique ID Field from the Spatial Weight File ####
    isGALNonUnique = False
    if swmFileBool:
        swm = SWMReader(weightsFile)
        fo = swm.fo
        masterField = swm.masterField
        spatialRefName = swm.spatialRefName
    else:
        ext = OS.path.splitext(weightsFile)[-1].upper()
        fo, info = textWeightsHeader(weightsFile)
        isGAL = ext == ".GAL"
        if isGAL:
            masterFieldInd = -2
        else:
            masterFieldInd = -1

        headerInfo = info.split()
        if len(headerInfo) > 1 or (not isGAL):
            masterField = headerInfo[masterFieldInd]
        else:
            masterField = None
            isGALNonUnique = True
        spatialRefName = ""
    fo.close()

    #### Check to See if in InputFC ####
    masterFieldObj = None
    if masterField == None:
        lf = ARCPY.ListFields(ssdo.inputFC, ssdo.oidName)
        masterFieldObj = lf[0]
    else:
        for fieldName, fieldObj in ssdo.allFields.iteritems():
            if fieldObj.baseName.upper() == masterField.upper():
                masterFieldObj = fieldObj

    if masterFieldObj == None:
        ARCPY.AddIDMessage("ERROR", 949, masterField, weightsFile)
        raise SystemExit()

    #### Assure Master Field is an Integer ####
    if not isGALNonUnique:
        dataType = ERROR.data2Type[masterFieldObj.type]
        if dataType not in [0,1]:
            typeString = ERROR.returnFieldTypes([0,1])
            ARCPY.AddIDMessage("ERROR", 640, masterField, typeString)
            raise SystemExit()

    return masterFieldObj.name.upper(), spatialRefName

def getWeightsValuesSWM(info, master2Order, varVals, rowStandard = True,
                        isSubSet = False, potVals = None):
    """Formats an entry of a SWM file for use in Global and Local
    Statistics.

    INPUTS:
    info (tuple): result of readWeightsEntry()
    master2Order (dict): uniqueID = order in values array
    varVals (array): values for all of the features
    rowStandard {bool, True}: return row standardized matrix?
    isSubSet {bool, False}: extra calcs are required (selection sets)
    potVals {array, None}: self weight values

    OUTPUT:
    masterID (int): unique ID for the current row in the SWM file
    orderID (int): order of the feature in the values array
    ownVal (float): given features own value
    nhIDs (list): unique IDs for neighbors
    nhVals (list): list of values for neighboring features
    weights (array): weights correspnding to the given neighbors
    """

    #### Parse Weights Entry ####
    masterID, nn, nhsTemp, weightsTemp, sumUnstandard = info
    potBool = (potVals != None)

    #### Get Self Values ####
    orderID = master2Order[masterID]
    ownVal = varVals[orderID]

    #### Empty Result Structures ####
    nhIDs = []
    nhVals = []
    weights = []

    #### Resolve Traditional Neighbors/Weights ####
    if isSubSet or potBool:
        #### Selection Set or Self Potential Field ####
        #### Requires Restandardization of Weights ####
        if nn:
            for i in xrange(nn):
                nh = nhsTemp[i]
                if master2Order.has_key(nh):
                    nhOrder = master2Order[nh]
                    nhIDs.append(nhOrder)
                    nhVals.append(varVals[nhOrder])
                    nhWeight = weightsTemp[i]
                    if rowStandard:
                        #### Unstandardize if Necessary ####
                        nhWeight = nhWeight * sumUnstandard[0]
                    weights.append(nhWeight)

        #### Self Weight ####
        if potBool:
            nhIDs.append(orderID)
            nhVals.append(ownVal)
            weights.append(potVals[orderID])

        #### Re-Standardize ####
        nn = len(nhIDs)
        if nn:
            weights = NUM.array(weights)
            if rowStandard:
                weights = (1.0 / weights.sum()) * weights

    else:
        #### No Selection Set ####
        if nn:
            for i in xrange(nn):
                nh = nhsTemp[i]
                nhOrder = master2Order[nh]
                nhIDs.append(nhOrder)
                nhVals.append(varVals[nhOrder])
        weights = weightsTemp

    return orderID, ownVal, nhIDs, nhVals, weights

def getWeightsValuesCont(masterID, master2Order, contDict, varVals, 
                         rowStandard = True, potVals = None):
    """Formats an entry of a contiguity dictionary for use in Global 
    and Local Statistics.

    INPUTS:
    contDict (tuple): result of polygonNeighborDict
    master2Order (dict): uniqueID = order in values array
    varVals (array): values for all of the features
    rowStandard {bool, True}: return row standardized matrix?
    potVals {array, None}: self weight values

    OUTPUT:
    masterID (int): unique ID for the current row in the SWM file
    orderID (int): order of the feature in the values array
    ownVal (float): given features own value
    nhIDs (list): unique IDs for neighbors
    nhVals (list): list of values for neighboring features
    weights (array): weights correspnding to the given neighbors
    """

    #### Get Self Values ####
    orderID = master2Order[masterID]
    ownVal = varVals[orderID]
    potBool = (potVals != None)

    #### Empty Result Structures ####
    nhIDs = []
    nhVals = []
    weights = []

    #### Resolve Traditional Neighbors/Weights ####
    try:
        otherNeighs = contDict[masterID]
        for nh in otherNeighs:
            if nh != masterID:
                nhOrder = master2Order[nh]
                nhIDs.append(nhOrder)
                nhVals.append(varVals[nhOrder])
                weights.append(1.0)
    except:
        pass

    #### Assign Self Neighbor ####
    if potBool:
        nhIDs.append(orderID)
        nhVals.append(ownVal)
        weights.append(potVals[orderID])

    #### Row Standardize ####
    nn = len(nhIDs)
    if nn:
        weights = NUM.array(weights)
        if rowStandard:
            weights = (1.0 / weights.sum()) * weights

    return orderID, ownVal, nhIDs, nhVals, weights

def getWeightsValuesText(masterID, master2Order, weightDict, varVals, 
                         potVals = None, allowSelf = False):
    """Formats an entry of a text weights dictionary for use in Global 
    and Local Statistics.

    INPUTS:
    weightDict (tuple): result of buildTextWeightDict
    master2Order (dict): uniqueID = order in values array
    varVals (array): values for all of the features
    potVals {array, None}: self weight values
    allowSelf {bool, False}: allow i == j for spatial weights

    OUTPUT:
    masterID (int): unique ID for the current row in the SWM file
    orderID (int): order of the feature in the values array
    ownVal (float): given features own value
    nhIDs (list): unique IDs for neighbors
    nhVals (list): list of values for neighboring features
    weights (array): weights correspnding to the given neighbors
    """

    #### Get Self Values ####
    orderID = master2Order[masterID]
    ownVal = varVals[orderID]
    potBool = (potVals != None)

    #### Empty Result Structures ####
    nhIDs = []
    nhVals = []
    weights = []
    selfIncluded = False
    ownWeight = 0.0

    #### Resolve Neighbors/Weights ####
    if weightDict.has_key(masterID):
        otherNeighs, otherWeights = weightDict[masterID]
        c = 0
        for nh in otherNeighs:
            if master2Order.has_key(nh):
                nhOrder = master2Order[nh]
                if nh == masterID:
                    #### Self Neighbor ####
                    selfIncluded = True
                    ownWeight = otherWeights[c]
                else:
                    #### Traditional Weights ####
                    nhIDs.append(nhOrder)
                    nhVals.append(varVals[nhOrder])
                    weights.append(otherWeights[c])
            c += 1

    #### Resolve Self Neighbor ####
    if allowSelf:
        if potBool:
            #### Overwrite Text Weight With Self Potential Value ####
            ownWeight = potVals[orderID]

        #### Assure Non-Zero Weight, Negatives Already Set to Zero ####
        zeroSelf = UTILS.compareFloat(0.0, ownWeight)

        #### Add Self Values If Not Zero Or Has Other Neighs ####
        if len(nhIDs) or not zeroSelf:
            nhIDs.append(orderID)
            nhVals.append(ownVal)
            weights.append(ownWeight)

    #### No Row Standardize, Text Weights As Defined ####
    weights = NUM.array(weights)

    return orderID, ownVal, nhIDs, nhVals, weights

def getWeightsValuesOTF_Potent(neighWeights, row, varVals, potVals = None):
    """Formats an entry of a GA Table set of weights and values for
    Global and Local Statistics..

    INPUTS:
    neighWeights (class): Instance of NeighborWeights
    row (int): index of GA Table
    varVals (array): values for all of the features
    potVals {array, None}: self weight values

    OUTPUT:
    orderID (int): order of the feature in the values array
    ownVal (float): given features own value
    nhIDs (list): unique IDs for neighbors
    nhVals (list): list of values for neighboring features
    weights (array): weights correspnding to the given neighbors

    NOTES:
    (1) See the wTypeDispatch dictionary in WeightsUtilities.py for a 
        complete list of spatial conceptualizations and their corresponding
        integer values.
    """

    #### Get Self Values ####
    ownVal = varVals[row]
    potBool = (potVals != None)

    #### Empty Result Structures ####
    nhIDs, weights = neighWeights[row]
    nhVals = NUM.take(varVals, nhIDs)

    if potBool:
        weights[-1] = potVals[row]
    
    return row, ownVal, nhIDs, nhVals, weights

def getWeightsValuesOTF(neighWeights, row, varVals):
    """Formats an entry of a GA Table set of weights and values for
    Global and Local Statistics..

    INPUTS:
    row (int): index of GA Table
    varVals (array): values for all of the features

    OUTPUT:
    orderID (int): order of the feature in the values array
    ownVal (float): given features own value
    nhIDs (list): unique IDs for neighbors
    nhVals (list): list of values for neighboring features
    weights (array): weights correspnding to the given neighbors

    NOTES:
    (1) See the wTypeDispatch dictionary in WeightsUtilities.py for a 
        complete list of spatial conceptualizations and their corresponding
        integer values.
    """

    #### Get Self Values ####
    ownVal = varVals[row]

    #### Empty Result Structures ####
    nhIDs, weights = neighWeights[row]
    nhVals = NUM.take(varVals, nhIDs)

    return row, ownVal, nhIDs, nhVals, weights

################### Contiguity Functions ##################

def polygonNeighborDict(inputFC, masterField, contiguityType = "ROOK"):
    """Build a dictionary containing polygon contiguity based on FID.

    INPUTS:
    inputFC (str, POLYGON): path to the input feature class    
    masterField (str): unique ID Field
    contiguityType {str, ROOK}: ROOK or QUEEN contiguity (1)

    OUTPUT:
    polyNeighborDict (dict): MasterID = list of neighbor IDs

    NOTES:
    (1) ROOK = Edges only, QUEEN = Edges and Vertices (Nodes)
    """

    #### Assure Polygon FC ####
    d = ARCPY.Describe(inputFC)
    if d.shapeType.upper() != "POLYGON":
        ARCPY.AddIDMessage("ERROR", 914)
        raise SystemExit()

    #### Use Polygon Neighbor Tool ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84126))
    contTable = "in_memory\contTabWU"
    ANA.PolygonNeighbors(inputFC, contTable, masterField, 
                         "AREA_OVERLAP", "NO_BOTH_SIDES")

    #### Create Result Structure ####
    polyNeighDict = COLL.defaultdict(list)
    rookType = contiguityType == 'ROOK'

    #### Create Cursor and Read Results ####
    rows = DA.SearchCursor(contTable, "*")
    for row in rows:
        include = True
        rowID, masterID, neighID, area, length, count = row
        noOverlap = UTILS.compareFloat(0.0, area)
        if rookType and noOverlap:
            if UTILS.compareFloat(0.0, length):
                include = False
        if include:
            polyNeighDict[masterID].append(neighID)
            polyNeighDict[neighID].append(masterID)

    #### Clean Up ####
    del rows
    UTILS.passiveDelete(contTable)

    return polyNeighDict

#################### Conversion Utilities ##################

def textWeightsHeader(textWeightsFile):
    """Returns the Master ID Field Name for a text formatted spatial
    weights matrix file.

    INPUTS:
    textWeightsFile (str): path to the text spatial weights file

    OUTPUT:
    fo (object): open text file pointer
    header (str): master ID fieldname
    """

    fo = UTILS.openFile(textWeightsFile, "r")
    header = fo.readline().strip()

    return fo, header

def buildTextWeightDict(textWeightsFile, master2Order): 
    """Processes spatial weights in text format and returns the
    information in a dictionary structure.

    INPUTS:
    textWeightsFile (str): path to the text spatial weights file
    master2Order (dict): uniqueID = order in values array

    OUTPUT:
    weightDict (dict): Unique ID: [ (neighIDs), (weights) ]
    """

    fo, masterField = textWeightsHeader(textWeightsFile)

    #### Possible to Run Out of Memory if Too Many Neighbors ####
    #### See Tool Documentation for Explanation ####
    weightDict = {}
    weightSum = 0.0
    negativeWeights = False
    errMess = "Invalid text weights format."

    for line in fo:
        #### Unpack and Check Format ####
        try:
            masterID, nid, weight = line.split() 
            masterID = int(masterID)
        except:
            ARCPY.AddError(errMess)
            raise SystemExit()

        #### Process Intersection in Weights Matrix ####
        if master2Order.has_key(masterID):
            try:
                nhID = int(nid)
                weight = LOCALE.atof(weight)
            except:
                ARCPY.AddIDMessage("Error", 919)
                raise SystemExit()
            if weight < 0.0:
                #### Do Not Add Negative Weights ####
                negativeWeights = True
            elif UTILS.compareFloat(weight, 0.0):
                #### Do Not Add Zero Weights ####
                pass
            else:
                try:
                    weightDict[masterID][0].append(nhID)
                    weightDict[masterID][1].append(weight)
                except:
                    weightDict[masterID] = ([nhID], [weight])
        else:
            #### Unique Id Does Not Exist / Not In Selection ####
            pass

    #### Report Negative Weights ####
    if negativeWeights:
        ARCPY.AddIDMessage("Warning", 941)

    fo.close()

    return weightDict
