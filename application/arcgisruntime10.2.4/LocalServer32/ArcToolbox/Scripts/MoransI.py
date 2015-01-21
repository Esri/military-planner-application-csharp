"""
Tool Name:     Global Moran's I
Source Name:   GlobalI.py
Version:       ArcGIS 10.1
Author:        Environmental Systems Research Institute Inc.
Description:   Computes Global Moran's I statistic
"""

################### Imports ########################
import sys as SYS
import os as OS
import numpy as NUM
import xml.etree.ElementTree as ET
import arcgisscripting as ARC
import arcpy as ARCPY
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO
import Stats as STATS
import WeightsUtilities as WU
import gapy as GAPY
import SSReport as REPORT
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

################### GUI Interface ###################

def setupGlobalI():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)                    
    varName = ARCPY.GetParameterAsText(1).upper()              
    displayIt = ARCPY.GetParameter(2) 

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

    #### Create a Spatial Stats Data Object (SSDO) ####
    ssdo = SSDO.SSDataObject(inputFC, useChordal = True)

    #### Set Unique ID Field ####
    masterField = UTILS.setUniqueIDField(ssdo, weightsFile = weightsFile)

    #### Populate SSDO with Data ####
    if WU.gaTypes[spaceConcept]:
        ssdo.obtainDataGA(masterField, [varName], minNumObs = 3, 
                          warnNumObs = 30)
    else:
        ssdo.obtainData(masterField, [varName], minNumObs = 3, 
                        warnNumObs = 30)

    #### Run Spatial Autocorrelation ####
    gi = GlobalI(ssdo, varName, wType, weightsFile = weightsFile, 
                 concept = concept, rowStandard = rowStandard, 
                 threshold = threshold, exponent = exponent)

    #### Report and Set Parameters ####
    giString, ziString, pvString = gi.report()
    try:
        ARCPY.SetParameterAsText(8, giString)
        ARCPY.SetParameterAsText(9, ziString)
        ARCPY.SetParameterAsText(10, pvString)
    except:
        ARCPY.AddIDMessage("WARNING", 902)

    #### Create HTML Output ####
    if displayIt:
        htmlOutFile = gi.reportHTML(htmlFile = None)
        ARCPY.SetParameterAsText(11, htmlOutFile)

class GlobalI(object):
    """Calculates Global Morans I:

    INPUTS:
    ssdo (obj): instance of SSDataObject
    varName (str): name of analysis field
    wType (int): spatial conceptualization (1)
    weightsFile {str, None}: path to a spatial weights matrix file
    concept: {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN 
    rowStandard {bool, True}: row standardize weights?
    threshold {float, None}: distance threshold
    exponent {float, 1.0}: distance decay
    displayIt {bool, False}: create graphical html output?

    ATTRIBUTES:
    numObs (int): number of features in analysis
    y (array, numObs x 1): vector of field values
    gi (float): Global Morans I value 
    ei (float): Expected value of Global I
    vi (float): Var of Global I (randomization)
    zi (float): z-score for Global I 
    pVal (float): p-value (two-tailed test)
    standDev (float): sqrt(vi)
    s0,s1,s2 (float): Spatial Weights Characteristics

    NOTES:
    (1) See the wTypeDispatch dictionary in WeightsUtilities.py for a 
        complete list of spatial conceptualizations and their corresponding
        integer values.
    """

    def __init__(self, ssdo, varName, wType, weightsFile = None, 
                 concept = "EUCLIDEAN", rowStandard = True, threshold = None,
                 exponent = 1.0):

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

        #### Initialize Data ####
        self.initialize()

        #### Construct Based on SWM File or On The Fly ####
        self.construct()

        #### Calculate Moran's I ####
        self.calculate()

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

        field = ssdo.fields[varName]
        self.y = field.returnDouble()
        self.numObs = ssdo.numObs
        maxSet = False

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
            self.thresholdStr = ssdo.distanceInfo.printDistance(threshold)
        else:
            self.thresholdStr = "None"

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

        #### Create Base Data Structures/Variables #### 
        self.numer = 0.0
        self.denom = NUM.sum(self.yDev**2.0)
        self.rowSum = NUM.zeros(numObs)
        self.colSum = NUM.zeros(numObs)
        self.s0 = 0
        self.s1 = 0
        self.wij = {}

        #### Set Neighborhood Structure Type ####
        if self.weightsFile:
            if self.swmFileBool:
                #### Open Spatial Weights and Obtain Chars ####
                swm = WU.SWMReader(weightsFile)
                N = swm.numObs
                rowStandard = swm.rowStandard

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
        ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84007), 0, N, 1)

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
                    #### Process Feature Contribution to Moran's I ####
                    self.processRow(orderID, yiDev, nhIDs, 
                                          nhVals, weights) 

            #### Reset Progessor ####
            ARCPY.SetProgressorPosition()

        #### Clean Up ####
        if self.swmFileBool:
            swm.close()
                
        #### Report on Features with No Neighbors ####
        ni.reportNoNeighbors()

        #### Report on Features with Large Number of Neighbors ####
        ni.reportWarnings()
        ni.reportMaximums()
        self.neighInfo = ni

    def processRow(self, orderID, yiDev, nhIDs, nhVals, weights):
        """Processes a features contribution to the Moran's I statistic.
        
        INPUTS:
        orderID (int): order in corresponding numpy value arrays
        yiVal (float): value for given feature
        nhIDs (array, nn): neighbor order in corresponding numpy value arrays
        nhVals (array, nn): values for neighboring features (1)
        weights (array, nn): weight values for neighboring features (1)

        NOTES:
        (1)  nn is equal to the number of neighboring features
        """

        #### Numerator Calculation ####
        sumW = weights.sum()
        self.s0 += sumW
        self.numer += NUM.sum(nhVals * weights) * yiDev

        #### Weights Charactersitics Update ####
        c = 0
        for neighID in nhIDs:
            ij = (orderID, neighID)
            ji = (neighID, orderID)
            w = weights[c] 
            self.s1 += w**2.0
            try:
                self.s1 += 2.0 * w * self.wij.pop(ji)
            except:
                self.wij[ij] = w
            self.rowSum[orderID] += w
            self.colSum[neighID] += w
            c += 1

    def calculate(self):
        """Calculate Moran's I Statistic."""

        s0 = self.s0
        s1 = self.s1
        n = len(self.rowSum) * 1.0
        s2 = NUM.sum( (self.rowSum + self.colSum)**2.0 )
        self.s2 = s2
        self.ei = -1. / (n - 1)
        self.squareExpectedI = self.ei**2
        self.n = n
        scale = n / s0
        s02 = s0 * s0
        n2 = n * n
        n2s1 = n2 * s1
        ns2 = n * s2
        self.gi = (scale * (self.numer/self.denom))
        yDev4Sum = NUM.sum(self.yDev**4) / n
        yDevsqsq = (self.denom / n)**2
        b2 = yDev4Sum / yDevsqsq
        self.b2 = b2
        left = n * ((n2 - (3*n) + 3) * s1 - (n*s2) + 3 * (s02))
        right = b2 * ((n2 - n) * s1 - (2*n*s2) + 6 * (s02))
        denom = (n-1) * (n-2) * (n-3) * s02
        num = (left - right) / denom
        self.expectedSquaredI = num 
        self.vi = self.expectedSquaredI - self.squareExpectedI

        #### Assure that Variance is Larger than Zero ####
        if NUM.isnan(self.vi) or self.vi <= 0.0:
            ARCPY.AddIDMessage("Error", 906)
            raise SystemExit()

        self.standDev = NUM.sqrt(self.vi)
        self.zi = (self.gi - self.ei)/self.standDev
        self.pVal = STATS.zProb(self.zi, type = 2)

    def report(self, fileName = None):
        """Reports the Moran's I results as a message or to a file.  If
        self.displayIt is set to True, then an html graphical report is
        generated to your default temp directory.

        INPUTS:
        fileName {str, None}: path to a text file to populate with results.
        """

        #### Create Output Text Table ####
        header = ARCPY.GetIDMessage(84160)
        giString = LOCALE.format("%0.6f", self.gi)
        eiString = LOCALE.format("%0.6f", self.ei)
        viString = LOCALE.format("%0.6f", self.vi) 
        ziString = LOCALE.format("%0.6f", self.zi) 
        pvString = LOCALE.format("%0.6f", self.pVal) 
        row1 = [ARCPY.GetIDMessage(84148), giString]
        row2 = [ARCPY.GetIDMessage(84149), eiString]
        row3 = [ARCPY.GetIDMessage(84150), viString]
        row4 = [ARCPY.GetIDMessage(84151), ziString]
        row5 = [ARCPY.GetIDMessage(84152), pvString]
        results =  [row1, row2, row3, row4, row5]
        outputTable = UTILS.outputTextTable(results, header = header,
                                            pad = 1)

        #### Add Linear/Angular Unit ####
        if self.wType in [0, 1, 7]:
            distanceOut = self.ssdo.distanceInfo.outputString
            dmsg = ARCPY.GetIDMessage(84344)
            distanceMeasuredStr = dmsg.format(distanceOut)
            outputTable += "\n%s\n" % distanceMeasuredStr

        #### Write/Report Text Output ####
        if fileName:
            f = UTILS.openFile(fileName, "w")
            f.write(outputTable)
            f.close()
        else:
            ARCPY.AddMessage(outputTable)

        #### Set Formatted Floats ####
        self.giString = giString
        self.eiString = eiString
        self.viString = viString
        self.ziString = ziString
        self.pvString = pvString
        
        return giString, ziString, pvString

    def reportHTML(self, htmlFile = None):
        """Generates a graphical html report for Moran's I."""

        #### Shorthand Attributes ####
        zi = self.zi

        #### Progress and Create HTML File Name ####
        writeMSG = ARCPY.GetIDMessage(84228)
        ARCPY.SetProgressor("default", writeMSG)
        ARCPY.AddMessage(writeMSG)
        if not htmlFile:
            prefix = ARCPY.GetIDMessage(84227)
            outputDir = UTILS.returnScratchWorkSpace()
            baseDir = UTILS.getBaseFolder(outputDir)
            htmlFile = UTILS.returnScratchName(prefix, fileType = "TEXT", 
                                           scratchWS = baseDir,
                                           extension = "html")

        #### Obtain Correct Images ####
        imageDir = UTILS.getImageDir()
        clustStr = ARCPY.GetIDMessage(84243)
        dispStr = ARCPY.GetIDMessage(84244)
        if zi <= -2.58:
            imageFile = OS.path.join(imageDir, "dispersedValues01.png")
            info = ("1%", dispStr)
            imageBox = OS.path.join(imageDir, "dispersedBox01.png")
        elif (-2.58 < zi <= -1.96):
            imageFile = OS.path.join(imageDir, "dispersedValues05.png")
            info = ("5%", dispStr)
            imageBox = OS.path.join(imageDir, "dispersedBox05.png")
        elif (-1.96 < zi <= -1.65):
            imageFile = OS.path.join(imageDir, "dispersedValues10.png")
            info = ("10%", dispStr)
            imageBox = OS.path.join(imageDir, "dispersedBox10.png")
        elif (-1.65 < zi < 1.65):
            imageFile = OS.path.join(imageDir, "randomValues.png")
            imageBox = OS.path.join(imageDir, "randomBox.png")
        elif (1.65 <= zi < 1.96):
            imageFile = OS.path.join(imageDir, "clusteredValues10.png")
            info = ("10%", clustStr)
            imageBox = OS.path.join(imageDir, "clusteredBox10.png")
        elif (1.96 <= zi < 2.58):
            imageFile = OS.path.join(imageDir, "clusteredValues05.png")
            info = ("5%", clustStr)
            imageBox = OS.path.join(imageDir, "clusteredBox05.png")
        else:
            imageFile = OS.path.join(imageDir, "clusteredValues01.png")
            info = ("1%", clustStr)
            imageBox = OS.path.join(imageDir, "clusteredBox01.png")

        #### Footnote ####
        footStart = ARCPY.GetIDMessage(84230).format(zi)
        if abs(zi) >= 1.65:
            footEnd = ARCPY.GetIDMessage(84231)
            footEnd = footEnd.format(*info)
            footerText = footStart + footEnd 
        else:
            footEnd = ARCPY.GetIDMessage(84232)
            footerText = footStart + footEnd

        #### Root Element ####
        title = ARCPY.GetIDMessage(84229)
        reportElement, reportTree = REPORT.xmlReport(title = title)

        #### Begin Graphic SubElement ####
        graphicElement = REPORT.xmlGraphic(reportElement, imageFile, 
                                           footerText = footerText)

        #### Floating Table ####
        rowVals = [ [ARCPY.GetIDMessage(84148), self.giString, ""],
                    [ARCPY.GetIDMessage(84151), self.ziString, imageBox],
                    [ARCPY.GetIDMessage(84152), self.pvString, ""] ]

        fTable = REPORT.xmlTable(graphicElement, rowVals, 
                                 tType = "ssFloat")

        #### Moran Table ####
        rowVals = [ [ARCPY.GetIDMessage(84148), self.giString],
                    [ARCPY.GetIDMessage(84149), self.eiString],
                    [ARCPY.GetIDMessage(84150), self.viString],
                    [ARCPY.GetIDMessage(84151), self.ziString],
                    [ARCPY.GetIDMessage(84152), self.pvString] ]

        mTable = REPORT.xmlTable(reportElement, rowVals,
                                 title = ARCPY.GetIDMessage(84160))

        #### Dataset Table ####
        rowVals = [ [UTILS.addColon(ARCPY.GetIDMessage(84233)), 
                     self.ssdo.inputFC],
                    [UTILS.addColon(ARCPY.GetIDMessage(84016)), 
                     self.varName],
                    [UTILS.addColon(ARCPY.GetIDMessage(84234)), 
                     WU.wTypeDispatch[self.wType]],
                    [UTILS.addColon(ARCPY.GetIDMessage(84235)),
                     self.concept],
                    [UTILS.addColon(ARCPY.GetIDMessage(84236)), 
                     str(self.rowStandard)],
                    [UTILS.addColon(ARCPY.GetIDMessage(84237)), 
                     self.thresholdStr],
                    [UTILS.addColon(ARCPY.GetIDMessage(84238)), 
                     str(self.weightsFile)],
                    [UTILS.addColon(ARCPY.GetIDMessage(84418)),
                     str(self.ssdo.selectionSet)] ]

        dTable = REPORT.xmlTable(reportElement, rowVals,
                                 title = ARCPY.GetIDMessage(84239))

        #### Create HTML ####
        html = REPORT.report2html(reportTree, htmlFile)
        ARCPY.AddMessage(htmlFile)

        return htmlFile

if __name__ == "__main__":
    setupGlobalI()

