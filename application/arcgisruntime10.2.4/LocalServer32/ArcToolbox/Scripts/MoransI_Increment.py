"""
Tool Name:     Incremental Spatial Autocorrelation
Source Name:   MoransI_Increment.py
Version:       ArcGIS 10.1
Author:        Environmental Systems Research Institute Inc.
Description:   Computes Global Moran's I statistic
"""

################### Imports ########################
import sys as SYS
import os as OS
import numpy as NUM
import collections as COLL
import arcgisscripting as ARC
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO
import Stats as STATS
import WeightsUtilities as WU
import gapy as GAPY
import locale as LOCALE
import pylab as PYLAB
import matplotlib.pyplot as PLT
import SSReport as REPORT
LOCALE.setlocale(LOCALE.LC_ALL, '')

################ Output Field Names #################
iaFieldNames = ["Distance", "MoransI", "ExpectedI",
                "Variance", "z-score", "p-value"]

################### GUI Interface ###################

def setupGlobalI_Increment():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    #### Input Features and Variable ####
    inputFC = ARCPY.GetParameterAsText(0)
    varName = ARCPY.GetParameterAsText(1).upper()

    #### Number of Distance Thresholds ####
    nIncrements = UTILS.getNumericParameter(2)
    if nIncrements > 30:
        nIncrements = 30

    #### Starting Distance ####
    begDist = UTILS.getNumericParameter(3)

    #### Step Distance ####
    dIncrement = UTILS.getNumericParameter(4)

    #### EUCLIDEAN or MANHATTAN ####
    distanceConcept = ARCPY.GetParameterAsText(5).upper().replace(" ", "_")
    concept = WU.conceptDispatch[distanceConcept]

    #### Row Standardized ####
    rowStandard = ARCPY.GetParameter(6)

    #### Output Table ####
    outputTable = UTILS.getTextParameter(7)

    #### Report File ####
    reportFile = UTILS.getTextParameter(8)

    #### Create a Spatial Stats Data Object (SSDO) ####
    ssdo = SSDO.SSDataObject(inputFC, useChordal = True)

    #### Set Unique ID Field ####
    masterField = UTILS.setUniqueIDField(ssdo)

    #### Populate SSDO with Data ####
    ssdo.obtainDataGA(masterField, [varName], minNumObs = 4,
                      warnNumObs = 30)

    #### Run Analysis ####
    gi = GlobalI_Step(ssdo, varName, nIncrements = nIncrements,
                      begDist = begDist, dIncrement = dIncrement,
                      concept = concept, rowStandard = rowStandard)

    #### Report Results ####
    reportTable = gi.report()

    #### Optionally Create Output ####
    if outputTable:
        outputTable, dbf = gi.createOutput(outputTable)
        if dbf:
            ARCPY.SetParameterAsText(7, outputTable)

    if reportFile:
        gi.createOutputGraphic(reportFile, gi.firstPeakInd, gi.maxPeakInd)

    #### Set Peak Distances ####
    firstPeak = gi.firstPeakDistance
    if firstPeak == None:
        firstPeak = ""
    ARCPY.SetParameterAsText(9, firstPeak)

    maxPeak = gi.maxPeakDistance
    if maxPeak == None:
        maxPeak = ""
    ARCPY.SetParameterAsText(10, maxPeak)

class GlobalI_Step(object):
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

    def __init__(self, ssdo, varName, nIncrements = 10,
                 begDist = None, dIncrement = None,
                 concept = "EUCLIDEAN", rowStandard = True,
                 stdDeviations = 0, includeCoincident = True,
                 silent = False, stopMax = None):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())
        self.idsWarn = []
        self.idsMax = []

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
        self.master2Order = ssdo.master2Order
        masterField = ssdo.masterField
        concept = self.concept

        #### Populate SSDO with Data ####
        field = ssdo.fields[varName]
        self.y = field.returnDouble()
        self.numObs = ssdo.numObs
        gaExtent = UTILS.get92Extent(ssdo.extent)

        #### Set Envelope or Slice ####
        if ssdo.useChordal:
            softMaxExtent = ssdo.sliceInfo.maxExtent
            hardMaxExtent = ARC._ss.get_max_gcs_distance(ssdo.spatialRef)
            maxExtent = min(softMaxExtent, hardMaxExtent)
        else:
            env = UTILS.Envelope(ssdo.extent)
            maxExtent = env.maxExtent

        #### Set Maximum Distance Allowed ####
        extentBool = (self.begDist != None) or (self.dIncrement != None) or ssdo.useChordal
        if extentBool:
            #### If User Provides Either Input, Set to 75% Max Extent ####
            self.maxDistance = maxExtent * 0.75
            self.allDefaults = False
        else:
            #### Set to Diameter of Standard Distance ####
            self.maxDistance = UTILS.standardDistanceCutoff(ssdo.xyCoords)
            self.allDefaults = True

        minimumRadius = (maxExtent * .001)

        #### Determine Starting Distance ####
        if self.begDist != None and self.begDist > self.maxDistance:
            ARCPY.AddIDMessage("WARNING", 929)
            self.begDist = None
        self.calculatedBegDist = self.begDist == None
        self.calculatedIncDist = self.dIncrement == None

        if self.calculatedBegDist or self.calculatedIncDist:
            outlierInfo = UTILS.LocationInfo(ssdo,
                                concept = self.concept,
                                stdDeviations = self.stdDeviations,
                                includeCoincident = self.includeCoincident,
                                silentThreshold = True)
            threshold = outlierInfo.threshold
            avgDist = outlierInfo.avgDist

            if self.begDist == None:
                self.begDist = threshold
            if self.dIncrement == None:
                self.dIncrement = avgDist

        #### Negative Values Not Valid ####
        if self.begDist < 0:
            ARCPY.AddIDMessage("ERROR", 933)
            raise SystemExit()

        #### Beginning Distance is too Small ####
        if self.begDist < minimumRadius:
            ARCPY.AddIDMessage("ERROR", 897, self.begDist)
            raise SystemExit()

        #### Determine All Distance Cutoffs ####
        cutoffs = UTILS.createCutoffsStep(self.begDist, self.dIncrement,
                                          self.nIncrements)

        #### Check Cutoff Values ###
        countMaxSet = (cutoffs > self.maxDistance).sum()
        if countMaxSet:
            #### Throw Warning if ANY Distances Larger than Max Extent ####
            if (not self.calculatedBegDist) and (not self.calculatedIncDist):
                ARCPY.AddIDMessage("WARNING", 1285, countMaxSet, self.nIncrements)

            cutoffs = UTILS.createCutoffsMaxDist(self.begDist, self.maxDistance,
                                                 self.nIncrements)
            self.dIncrement = cutoffs[1] - cutoffs[0]

        #### Print Threshold Distance ####
        stepMax = cutoffs[-1]
        thresholdStr = ssdo.distanceInfo.printDistance(self.begDist)
        threshBool = self.calculatedBegDist
        if threshBool and not self.silent:
            ARCPY.AddIDMessage("WARNING", 853, thresholdStr)

        if self.begDist > (maxExtent * 0.51) \
                    and not self.calculatedBegDist:
            ARCPY.AddIDMessage("WARNING", 934)
        elif stepMax > maxExtent \
                    and not self.calculatedIncDist:
            ARCPY.AddIDMessage("WARNING", 935)

        #### Create Results Labels and Field Names ####
        resLabels = [ARCPY.GetIDMessage(84179), ARCPY.GetIDMessage(84148),
                     ARCPY.GetIDMessage(84149), ARCPY.GetIDMessage(84150),
                     ARCPY.GetIDMessage(84151), ARCPY.GetIDMessage(84152)]
        self.resLabels = [ i.replace(":", "").strip() for i in resLabels ]

        #### Set Attributes ####
        self.stepMax = stepMax
        self.cutoffs = NUM.array(cutoffs)
        self.reverseOrder = range(self.nIncrements - 1, -1, -1)
        self.cutoffOrder = range(self.nIncrements)
        self.largestDistBand = self.cutoffs[-1]

    def construct(self):
        """Constructs the neighborhood structure for each feature and
        dispatches the appropriate values for the calculation of the
        statistic."""

        #### Shorthand Attributes ####
        ssdo = self.ssdo
        numObs = ssdo.numObs
        master2Order = ssdo.master2Order
        masterField = ssdo.masterField
        concept = self.concept
        iterVals = range(numObs)
        rowStandard = self.rowStandard
        wType = 1

        yVar = NUM.var(self.y)
        if NUM.isnan(yVar) or yVar <= 0.0:
            ARCPY.AddIDMessage("ERROR", 906)
            raise SystemExit()

        #### Create Deviation Variables ####
        self.yBar = NUM.mean(self.y)
        self.yDev = self.y - self.yBar

        #### Create Results Array ####
        self.giResults = NUM.zeros((self.nIncrements, 6))

        #### Run Max Distance and Bin NN ####
        msgProg = ARCPY.GetIDMessage(84423)
        self.rowSum = NUM.zeros((numObs, self.nIncrements), float)
        self.weightVals = NUM.ones((numObs, self.nIncrements), float)
        self.noNeighs = NUM.zeros((self.nIncrements,), int)
        self.breaks = COLL.defaultdict(NUM.array)
        self.numFeatures = NUM.ones((self.nIncrements,), int) * ssdo.numObs
        self.totalNeighs = NUM.zeros((self.nIncrements,), float)
        ARCPY.SetProgressor("step", msgProg, 0, ssdo.numObs, 1)
        if not self.silent:
            ARCPY.AddMessage("\n" + msgProg)
        gaSearch = GAPY.ga_nsearch(ssdo.gaTable)
        gaSearch.init_nearest(self.stepMax, 0, concept.lower())
        gaTable = ssdo.gaTable
        numCalcs = 0
        warnThrown = (self.silent == True) or (self.allDefaults == True)
        self.warnNeighsExceeded = warnThrown
        self.maxNeighsExceeded = warnThrown
        self.completed = False

        nb = ARC._ss.NeighborBins(gaTable, gaSearch, self.cutoffs)
        c = 0
        for counts, breaks in nb:
            numDists = len(breaks)
            if numDists:
                #### Add Warning if Possibly Going to Run out of Memory ####
                numCalcs += numDists
                if numCalcs > 20000000 and not warnThrown:
                    if not self.silent:
                        ARCPY.AddIDMessage("WARNING", 1389)
                    warnThrown = True

                self.breaks[c] = breaks
                noNeighInd = NUM.where(counts == 0)[0]
                if len(noNeighInd):
                    for noInd in noNeighInd:
                        self.noNeighs[noInd] += 1
                        self.numFeatures[noInd] -= 1
                if rowStandard:
                    self.weightVals[c] = 1./counts
                    self.rowSum[c] = 1.0
                else:
                    self.rowSum[c] = counts * 1.0
                self.totalNeighs += counts
            else:
                #### Never Included in Spatial Autocorrelation ####
                for ind in xrange(self.nIncrements):
                    self.noNeighs[ind] += 1
                    self.numFeatures[ind] -= 1

            #### Warn Number of Neighs ####
            if numDists >= WU.warnNumberOfNeighbors:
                self.idsWarn.append(self.ssdo.order2Master[c])
                if not self.warnNeighsExceeded:
                    ARCPY.AddIDMessage("WARNING", 1420,
                                       WU.warnNumberOfNeighbors)
                    self.warnNeighsExceeded = True
            c += 1
            ARCPY.SetProgressorPosition()
        
        #### Report if All Features Have No Neighbors ####
        self.s0 = self.rowSum.sum(0)
        noNeighsAllInd = NUM.where(self.s0 == 0.0)[0]
        if len(noNeighsAllInd):
            cutoffNoNeighs = self.cutoffs[noNeighsAllInd]
            dist = [UTILS.formatValue(i, "%0.2f") for i in cutoffNoNeighs]
            distanceStr = ", ".join(dist)
            ARCPY.AddIDMessage("ERROR", 1388, distanceStr)
            raise SystemExit()

        #### Report on Features with Large Number of Neighbors ####
        throwWarnings = (self.silent == True) or (self.allDefaults == True)
        if not throwWarnings:
            self.reportWarnings()
            self.reportMaximums()

        #### Calculate Statistic ####
        msgProg = ARCPY.GetIDMessage(84280)
        ARCPY.SetProgressor("step", msgProg, 0, ssdo.numObs, 1)
        if not self.silent:
            ARCPY.AddMessage("\n" + msgProg)
        self.numer = NUM.zeros((self.nIncrements,), float)
        self.denom = NUM.sum(self.yDev**2.0)
        self.s1 = NUM.zeros((self.nIncrements,), float)
        self.colSum = NUM.zeros((numObs, self.nIncrements), float)

        for i in xrange(ssdo.numObs):
            if self.breaks.has_key(i):
                binIndices = self.breaks[i]
                yDev0 = self.yDev[i]
                gaSearch.search_by_idx(i)
                w0 = self.weightVals[i]
                c = 0
                for nh in gaSearch:
                    start = binIndices[c]
                    yDev1 = self.yDev[nh.idx]
                    w1 = self.weightVals[nh.idx][start:]
                    w0c = w0[start:]
                    values = (yDev1 * w1) * yDev0
                    self.numer[start:] += values
                    self.s1[start:] += ((w0c + w1)**2.0)
                    self.colSum[i][start:] += w1
                    c += 1

            ARCPY.SetProgressorPosition()

        #### Calculate Moran's I ####
        self.calculate()

        #### Pack Results ####
        for ind in self.cutoffOrder:
            res = (self.cutoffs[ind], self.gi[ind], self.ei[ind],
                   self.vi[ind], self.zi[ind], self.pVal[ind])
            self.giResults[ind] = res

        if not self.silent:
            ARCPY.AddMessage("\n")

        #### Calculate Peak Distances ####
        ziResults = [ value[4] for value in self.giResults ]
        firstPeakInd, maxPeakInd = UTILS.returnPeakIndices(ziResults,
                                                  levelFilter = 1.65)

        #### Add Warning if No Valid Peaks are Found ####
        if firstPeakInd == None and maxPeakInd == None:
            if not self.silent:
                ARCPY.AddIDMessage("WARNING", 1284)

        if firstPeakInd == None:
            self.firstPeakDistance = None
            self.firstPeakZ = None
        else:
            self.firstPeakDistance = self.cutoffs[firstPeakInd]
            self.firstPeakZ = self.zi[firstPeakInd]


        if maxPeakInd == None:
            self.maxPeakDistance = None
            self.maxPeakZ = None
        else:
            self.maxPeakDistance = self.cutoffs[maxPeakInd]
            self.maxPeakZ = self.zi[maxPeakInd]

        self.firstPeakInd = firstPeakInd
        self.maxPeakInd = maxPeakInd
        self.completed = True

        return True

    def calculate(self):
        """Calculate Moran's I Statistic."""

        s0 = self.s0
        self.s1 = .5 * self.s1
        s1 = self.s1
        n = self.numFeatures * 1.0
        s2 = ((self.rowSum + self.colSum)**2.0).sum(0)
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
        if NUM.any(NUM.isnan(self.vi)) or NUM.any(self.vi <= 0.0):
            ARCPY.AddIDMessage("ERROR", 906)
            raise SystemExit()

        self.standDev = NUM.sqrt(self.vi)
        self.zi = (self.gi - self.ei)/self.standDev
        self.pVal = NUM.array([STATS.zProb(i, type = 2) for i in self.zi])

    def reportWarnings(self, numFeatures = 30):
        if len(self.idsWarn):
            self.idsWarn.sort()
            idsOut = [ str(i) for i in self.idsWarn[0:numFeatures] ]
            idsOut = ", ".join(idsOut)
            ARCPY.AddIDMessage("WARNING", 1422, self.ssdo.masterField, idsOut)

    def reportMaximums(self, numFeatures = 30):
        if len(self.idsMax):
            self.idsMax.sort()
            idsOut = [ str(i) for i in self.idsMax[0:numFeatures] ]
            idsOut = ", ".join(idsOut)
            ARCPY.AddIDMessage("WARNING", 1423, self.ssdo.masterField, idsOut)

    def report(self, fileName = None):
        """Reports the Moran's I results as a message or to a file.

        INPUTS:
        fileName {str, None}: path to a text file to populate with results.
        """

        header = ARCPY.GetIDMessage(84160) + ARCPY.GetIDMessage(84282)
        results = [ self.resLabels ]
        hasNoNeighs = self.noNeighs.any()
        strNoNeighs = ARCPY.GetIDMessage(84111)

        #### Create Output Text Table ####
        for testIter in range(self.nIncrements):
            d, gi, ei, vi, zi, pv = self.giResults[testIter]
            d = LOCALE.format("%0.2f", round(d, 2))
            gi = LOCALE.format("%0.6f", gi)
            ei = LOCALE.format("%0.6f", ei)
            vi = LOCALE.format("%0.6f", vi)
            zi = LOCALE.format("%0.6f", zi)
            pv = LOCALE.format("%0.6f", pv)

            #### Add Asterisk to No Neigh Distances ####
            if hasNoNeighs:
                numNoNeighs = self.noNeighs[testIter]
                if numNoNeighs:
                    d += strNoNeighs
                else:
                    d += " "
            res = [d, gi, ei, vi, zi, pv]
            results.append(res)

        outputReport = UTILS.outputTextTable(results, header = header,
                                             justify = "right", pad = 1)

        #### Report Peaks ####
        firstPeakMess = ARCPY.GetIDMessage(84419)
        decimalSep = UTILS.returnDecimalChar()
        if decimalSep == ".":
            numSep = ","
        else:
            numSep = ";"
        if self.firstPeakInd != None:

            zi = LOCALE.format("%0.6f", self.giResults[self.firstPeakInd,4])
            d = LOCALE.format("%0.2f", round(self.firstPeakDistance, 2))

            firstPeakMess = firstPeakMess.format(d, numSep, zi)
        else:
            firstPeakMess = firstPeakMess.format("None", numSep, "None")
        outputReport += "\n" + firstPeakMess + "\n"

        maxPeakMess = ARCPY.GetIDMessage(84420)
        if self.maxPeakInd != None:
            zi = LOCALE.format("%0.6f", self.giResults[self.maxPeakInd,4])
            d = LOCALE.format("%0.2f", round(self.maxPeakDistance, 2))
            maxPeakMess = maxPeakMess.format(d, numSep, zi)
        else:
            maxPeakMess = maxPeakMess.format("None", numSep,"None")
        outputReport += maxPeakMess

        #### Add Linear/Angular Unit ####
        distanceOut = self.ssdo.distanceInfo.outputString
        dmsg = ARCPY.GetIDMessage(84344)
        distanceMeasuredStr = dmsg.format(distanceOut)
        outputReport += "\n%s\n" % distanceMeasuredStr

        if fileName:
            if hasNoNeighs:
                noNeighMess = ARCPY.GetIDMessage(84417) + "\n"
                outputReport += noNeighMess
            f = UTILS.openFile(fileName, "w")
            f.write(outputReport)
            f.close()
        else:
            ARCPY.AddMessage(outputReport)
            if hasNoNeighs:
                ARCPY.AddIDMessage("WARNING", 1532)

        return outputReport

    def createOutput(self, outputTable):
        """Creates Moran's I Step Output Table.

        INPUTS
        outputTable (str): path to the output table
        """

        #### Allow Overwrite Output ####
        ARCPY.env.overwriteOutput = 1

        #### Get Output Table Name With Extension if Appropriate ####
        outputTable, dbf = UTILS.returnTableName(outputTable)

        #### Set Progressor ####
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84008))

        #### Delete Table If Exists ####
        UTILS.passiveDelete(outputTable)

        #### Create Table ####
        outPath, outName = OS.path.split(outputTable)
        try:
            DM.CreateTable(outPath, outName)
        except:
            ARCPY.AddIDMessage("ERROR", 541)
            raise SystemExit()

        #### Add Result Fields ####
        self.outputFields = []
        for field in iaFieldNames:
            fieldOut = ARCPY.ValidateFieldName(field, outPath)
            UTILS.addEmptyField(outputTable, fieldOut, "DOUBLE")
            self.outputFields.append(fieldOut)

        #### Create Insert Cursor ####
        try:
            insert = DA.InsertCursor(outputTable, self.outputFields)
        except:
            ARCPY.AddIDMessage("ERROR", 204)
            raise SystemExit()

        #### Add Rows to Output Table ####
        for testIter in xrange(self.nIncrements):
            insert.insertRow(self.giResults[testIter])

        #### Clean Up ####
        del insert

        return outputTable, dbf

    def createOutputGraphic(self, fileName, firstInd = None, maxInd = None):

        #### Set Progressor ####
        writeMSG = ARCPY.GetIDMessage(84186)
        ARCPY.SetProgressor("step", writeMSG, 0, 3, 1)
        ARCPY.AddMessage(writeMSG)

        #### Set Colors ####
        colors = NUM.array(["#4575B5", "#849EBA", "#C0CCBE", "#FFFFBF",
          "#FAB984", "#ED7551", "#D62F27"])
        cutoffs = NUM.array([-2.58, -1.96, -1.65, 1.65, 1.96, 2.58])

        #### Import Matplotlib ####
        pdfOutput = REPORT.openPDF(fileName)

        #### Set Base Figure ####
        title = ARCPY.GetIDMessage(84334)
        report = REPORT.startNewReport(22, title = title, landscape = True,
                                       titleFont = REPORT.ssTitleFont)
        grid = report.grid
        startRow = 1
        gridPlot = PLT.subplot2grid(grid.gridInfo, (startRow, 0),
                                    colspan = 20, rowspan = 16)

        #### Set Data ####
        distVals = []
        zVals = []
        for testIter in range(self.nIncrements):
            d, gi, ei, vi, zi, pv = self.giResults[testIter]
            distVals.append(d)
            zVals.append(zi)

        #### Plot Values ####
        zVals = NUM.array(zVals)
        binVals = NUM.digitize(zVals, cutoffs)
        binColors = colors[binVals]

        #### Line Graph First ####
        lines = PLT.plot(distVals, zVals, color='k', linestyle='-')

        #### Add Series and First/Max Points ####
        if firstInd != None:
            #### First Peak ####
            firstPoint = PLT.plot(distVals[firstInd], zVals[firstInd],
                                  color='#00FFFF', marker='o', alpha = 0.7,
                                  markeredgecolor='k', markersize = 14)

        if maxInd != None:
            #### Max Peak ####
            if maxInd != firstInd:
                maxPoint = PLT.plot(distVals[maxInd], zVals[maxInd],
                                    color='#00FFFF', marker='o', alpha = 0.7,
                                    markeredgecolor='k', markersize = 14)

        #### Points Next ####
        for ind, dist in enumerate(distVals):
            color = binColors[ind]
            points = PLT.plot(dist, zVals[ind], color=color, marker='o',
                              alpha = 0.7, markeredgecolor='k',
                              markersize = 8)

        #### Set Axis and Tick Labels ####
        yLabel = ARCPY.GetIDMessage(84335)
        distanceOut = self.ssdo.distanceInfo.outputString
        xLabel = ARCPY.GetIDMessage(84077).format(distanceOut)
        PYLAB.ylabel(yLabel, fontproperties = REPORT.ssLabFont, labelpad = 20)
        PYLAB.xlabel(xLabel, fontproperties = REPORT.ssLabFont, labelpad = 20)
        gridPlot.yaxis.grid(True, linestyle='-', which='major',
                            color='lightgrey', alpha=0.5)
        REPORT.setTickFontSize(gridPlot)

        #### Scoot Max Z ####
        minD, maxD = UTILS.increaseMinMax(distVals, multiplier = .15)
        minZ, maxZ = UTILS.increaseMinMax(zVals, multiplier = .15)
        PYLAB.ylim(ymin = minZ, ymax = maxZ)
        PYLAB.xlim(xmin = minD, xmax = maxD)

        #### Create Legend ####
        rColors = [ i for i in reversed(colors) ]
        grid.writeCell((startRow, 20), yLabel, colspan = 2,
                        fontObj = REPORT.ssBoldFont, justify = "right")
        labels = ["> 2.58", "1.96 - 2.58", "1.65 - 1.96", "-1.65 - 1.65",
                  "-1.96 - -1.65", "-2.58 - -1.96", "< -2.58"]

        gridCount = 0
        for ind, lab in enumerate(labels):
            color = rColors[ind]
            row = ind + 1 + startRow
            gridCount += 1

            #### Add Points ####
            gridLegend = PLT.subplot2grid(grid.gridInfo, (row, 20))
            PLT.plot(0.0, 0.0, color = color, marker = "o", alpha = .7)
            REPORT.clearGrid(gridLegend)

            #### Add Text ####
            gridLegend = PLT.subplot2grid(grid.gridInfo, (row, 21))
            PLT.text(0.0, 0.3, lab, fontproperties = REPORT.ssFont,
                     horizontalalignment = "left")
            REPORT.clearGrid(gridLegend)

        #### Add Peak Marker ####
        currentRow = startRow + gridCount + 1
        grid.createLineRow(currentRow, startCol = 20, endCol = 22)
        currentRow += 1

        gridLegend = PLT.subplot2grid(grid.gridInfo, (currentRow, 20))
        PLT.plot(0.0, 0.0, color='#00FFFF', marker='o', alpha = 0.4,
                 markeredgecolor='k', markersize = 14)
        REPORT.clearGrid(gridLegend)

        #### Add Text ####
        gridLegend = PLT.subplot2grid(grid.gridInfo, (currentRow, 21))
        PLT.text(0.0, 0.3, "Peaks", fontproperties = REPORT.ssFont,
                 horizontalalignment = "left")
        REPORT.clearGrid(gridLegend)

        #### Add To PDF ####
        PLT.savefig(pdfOutput, format='pdf')
        PLT.close()
        ARCPY.SetProgressorPosition()

        #### Tabular Output ####
        title = ARCPY.GetIDMessage(84160) + ARCPY.GetIDMessage(84282)
        titlePlus = title + " " + ARCPY.GetIDMessage(84377)
        report = REPORT.startNewReport(7, title = title, landscape = True,
                                       titleFont = REPORT.ssTitleFont)
        grid = report.grid

        #### Create Column Labels ####
        grid.createColumnLabels(self.resLabels, justify = "right",
                                fontObj = REPORT.ssBoldFont)

        #### Create Output Text Table ####
        hasNoNeighs = self.noNeighs.any()
        strNoNeighs = ARCPY.GetIDMessage(84111)
        for testIter in range(self.nIncrements):
            if grid.rowCount >= 19:
                #### Finalize Page ####
                grid.finalizeTable()
                report.write(pdfOutput)

                #### New Page ####
                report = REPORT.startNewReport(7, title = titlePlus,
                                                   landscape = True,
                                     titleFont = REPORT.ssTitleFont)
                grid = report.grid

                #### Create Column Labels ####
                grid.createColumnLabels(self.resLabels, justify = "right",
                                        fontObj = REPORT.ssBoldFont)

            #### Get Results ####
            d, gi, ei, vi, zi, pv = self.giResults[testIter]
            d = LOCALE.format("%0.2f", round(d, 2))

            #### Add Asterisk to No Neigh Distances ####
            if hasNoNeighs:
                numNoNeighs = self.noNeighs[testIter]
                if numNoNeighs:
                    d += strNoNeighs
                else:
                    d += " "

            grid.writeCell((grid.rowCount, 0), d,
                            justify = "right")
            grid.writeCell((grid.rowCount, 1),
                            LOCALE.format("%0.6f", gi),
                            justify = "right")
            grid.writeCell((grid.rowCount, 2),
                            LOCALE.format("%0.6f", ei),
                            justify = "right")
            grid.writeCell((grid.rowCount, 3),
                            LOCALE.format("%0.6f", vi),
                            justify = "right")
            grid.writeCell((grid.rowCount, 4),
                            LOCALE.format("%0.6f", zi),
                            justify = "right")
            grid.writeCell((grid.rowCount, 5),
                            LOCALE.format("%0.6f", pv),
                            justify = "right")
            grid.stepRow()

        if grid.rowCount <= 19:
            grid.createLineRow(grid.rowCount, startCol = 0, endCol = 7)
            grid.stepRow()

        #### Add Footnotes, Peaks, Linear Unit, No Neighbor Message ####
        footNotes = []

        #### Report Peaks ####
        firstPeakMess = ARCPY.GetIDMessage(84419)
        decimalSep = UTILS.returnDecimalChar()
        if decimalSep == ".":
            numSep = ","
        else:
            numSep = ";"
        if self.firstPeakInd != None:
            zi = LOCALE.format("%0.6f", self.giResults[self.firstPeakInd,4])
            d = LOCALE.format("%0.2f", round(self.firstPeakDistance, 2))
            firstPeakMess = firstPeakMess.format(d, numSep, zi)
        else:
            firstPeakMess = firstPeakMess.format("None",numSep, "None")
        footNotes += REPORT.splitFootnote(firstPeakMess, 145)

        maxPeakMess = ARCPY.GetIDMessage(84420)
        if self.maxPeakInd != None:
            zi = LOCALE.format("%0.6f", self.giResults[self.maxPeakInd,4])
            d = LOCALE.format("%0.2f", round(self.maxPeakDistance, 2))
            maxPeakMess = maxPeakMess.format(d, numSep, zi)
        else:
            maxPeakMess = maxPeakMess.format("None",numSep, "None")
        footNotes += REPORT.splitFootnote(maxPeakMess, 145)

        #### Add Linear/Angular Unit ####
        distanceOut = self.ssdo.distanceInfo.outputString
        dmsg = ARCPY.GetIDMessage(84344)
        distanceMeasuredStr = dmsg.format(distanceOut)
        footNotes += REPORT.splitFootnote(distanceMeasuredStr, 145)

        #### Add No Neighbor Message ####
        if hasNoNeighs:
            noNeighMess = ARCPY.GetIDMessage(84417)
            footNotes += REPORT.splitFootnote(noNeighMess, 145)

        for line in footNotes:
            if grid.rowCount >= 19:
                #### Finalize Page ####
                grid.finalizeTable()
                report.write(pdfOutput)

                #### New Page ####
                report = REPORT.startNewReport(7, title = titlePlus,
                                                   landscape = True,
                                     titleFont = REPORT.ssTitleFont)

                grid = report.grid

            #### Write Footnote ####
            grid.writeCell((grid.rowCount, 0), line,
                            colspan = 7, justify = "left")
            grid.stepRow()

        grid.finalizeTable()

        #### Add To PDF ####
        report.write(pdfOutput)
        ARCPY.SetProgressorPosition()

        ##### Add Dataset/Parameter Info ####
        paramLabels = [84253, 84016, 84374, 84375, 84376, 84235, 84236, 84418]
        paramLabels = [ ARCPY.GetIDMessage(i) for i in paramLabels ]

        paramValues = [self.ssdo.inputFC, self.varName,
                       "%i" % self.nIncrements,
                       UTILS.formatValue(self.begDist),
                       UTILS.formatValue(self.dIncrement),
                       self.concept, "%s" % self.rowStandard,
                       str(self.ssdo.selectionSet)]

        title = ARCPY.GetIDMessage(84373)
        REPORT.createParameterPage(paramLabels, paramValues,
                                   title = title,
                                   pdfOutput = pdfOutput,
                                   titleFont = REPORT.ssTitleFont)

        #### Finish Up ####
        ARCPY.AddMessage(fileName)
        pdfOutput.close()
        ARCPY.SetProgressorPosition()


if __name__ == "__main__":
    setupGlobalI_Increment()






