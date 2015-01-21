"""
Tool Name: Optimized Hot Spot Analysis (Getis-Ord Gi*)
Source Name: OptimizedHotSpotAnalysis.py
Version: ArcGIS 10.1.2
Author: ESRI

Optimized version of Hot-Spot Analysis.  Given incident points or
weighted features (points or polygons), creates a map of statistically
significant hot and cold spots.  It evaluates the characteristics of
the input feature class to produce optimal results.
"""

################### Imports ########################
import sys as SYS
import math as MATH
import os as OS
import numpy as NUM
import collections as COLL
import arcgisscripting as ARC
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.da as DA
import arcpy.analysis as ANA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO
import Stats as STATS
import WeightsUtilities as WU
import gapy as GAPY
import locale as LOCALE
import MoransI_Increment as MI
import CollectEvents as EVENTS
import Gi as GISTAR
LOCALE.setlocale(LOCALE.LC_ALL, '')

############################ Local Variables ###############################

nnScale = 2.0
numPerms = None
minNumNeighsSet = 3
maxNumNeighsSet = 30
minNumFeatures = 30
additionalZeroDistScale = "ALL"
#additionalZeroDistScale = .1
indentAnswerStr = "    - "
aggTypes = {"SNAP_NEARBY_INCIDENTS_TO_CREATE_WEIGHTED_POINTS" : 0,
            "COUNT_INCIDENTS_WITHIN_FISHNET_POLYGONS": 1,
            "COUNT_INCIDENTS_WITHIN_AGGREGATION_POLYGONS": 2}
aggMins = {0:60, 1:30, 2:30}
aggHeaders = {0:84448, 1:84456, 2:84456}
aggOutliers = {0:84494, 1:84495, 2:84496}
mercatorProjection = ARCPY.SpatialReference(54004)

############################ Local Methods ##############################

def getPolyExtent(polyDict):
    pointList = []
    for ind, poly in polyDict.iteritems():
        for point in poly:
            pointList.append(point)

    points = NUM.array(pointList)
    minX, minY = points.min(0)
    maxX, maxY = points.max(0)
    return ARCPY.Extent(minX, minY, maxX, maxY)

def printWeightAnswer(y):
    """Describes the Weight/Analysis/Count Field."""

    minY = y.min()
    maxY = y.max()
    avgY = y.mean()
    stdY = y.std()

    minStr = ARCPY.GetIDMessage(84271) + ":"
    maxStr = ARCPY.GetIDMessage(84272) + ":"
    avgStr = ARCPY.GetIDMessage(84261) + ":"
    stdStr = ARCPY.GetIDMessage(84262) + ":"
    padStr = " " * 7

    minString = LOCALE.format("%0.4f", minY)
    maxString = LOCALE.format("%0.4f", maxY)
    avgString = LOCALE.format("%0.4f", avgY)
    stdString = LOCALE.format("%0.4f", stdY)
    row1 = [padStr, minStr, minString]
    row2 = [padStr, maxStr, maxString]
    row3 = [padStr, avgStr, avgString]
    row4 = [padStr, stdStr, stdString]
    results =  [row1, row2, row3, row4]
    outputTable = UTILS.outputTextTable(results, pad = 1,
                     justify = ['left', 'left', 'right'])

    ARCPY.AddMessage(outputTable)

def printOHSLocationalOutliers(lo, aggType = 1):
    """Prints the results of input incident locational outliers."""

    printOHSSubject(84438, addNewLine = False)
    aggResult = ARCPY.GetIDMessage(aggOutliers[aggType])
    if lo.numOutliers:
        if lo.numOutliers == 1:
            msg = ARCPY.GetIDMessage(84493).format(aggResult)
        else:
            msg = ARCPY.GetIDMessage(84434).format(lo.numOutliers, aggResult)
    else:
        msg = ARCPY.GetIDMessage(84437)

    printOHSAnswer(msg)

def printOHSSection(messID, prependNewLine = False):
    """Prints Section Message Header to Results Window."""

    msg = ARCPY.GetIDMessage(messID)
    msg = " " + msg + " "
    msg = msg.center(78, "*")
    if prependNewLine:
        msg = "\n" + msg
    ARCPY.AddMessage(msg)

def printOHSSubject(messID, addNewLine = True):
    """Prints Subject Message Header to Results Window."""

    msg = ARCPY.GetIDMessage(messID)
    if addNewLine:
        msg += "\n"
    ARCPY.AddMessage(msg)

def printOHSAnswer(messStr, addNewLine = True):
    """Prints Subject Message Header to Results Window."""

    msg = indentAnswerStr + messStr
    if addNewLine:
        msg += "\n"
    ARCPY.AddMessage(msg)

def scaleDecision(avgDist, medDist):
    """Retuns Fishnet Distance w/ unknown boundary.

    INPUTS:
    avgDist (float): average nearest neighbor distance
    medDist (float): median nearest neighbor distance
    """

    msg = "Using {0} NN Distance * Nearest Neighbor Scale: {1} * {2} = {3}"
    if avgDist > medDist:
        outName = "Average"
        outLeft = avgDist
        testScale = avgDist / medDist
        outDist = avgDist
    else:
        outName = "Median"
        outLeft = medDist
        testScale = medDist / avgDist
        outDist = medDist

    if testScale > nnScale:
        outScale = testScale
    else:
        outScale = nnScale

    dist = outDist * outScale

    return dist

def knnDecision(ssdo):
    """If no peak autocorrelation distance is found, then return the average
    at which all features have a desired set of nearest neighbors.  This value
    is scaled to be larger than 3 and no larger than 30.  If computed value is
    larger than 1 standard distance, then return the standard distance
    instead.

    INPUTS:
    ssdo (class): instance of Spatial Stats Data Object
    """

    numNeighs = int(ssdo.numObs * .05)
    if numNeighs < minNumNeighsSet:
        numNeighs = minNumNeighsSet
    if numNeighs > maxNumNeighsSet:
        numNeighs = maxNumNeighsSet

    #### KNN Subject ####
    msg = ARCPY.GetIDMessage(84463)
    ARCPY.SetProgressor("step", msg, 0, ssdo.numObs, 1)
    printOHSSubject(84463, addNewLine = False)

    #### Create k-Nearest Neighbor Search Type ####
    gaTable = ssdo.gaTable
    gaSearch = GAPY.ga_nsearch(gaTable)
    gaSearch.init_nearest(0.0, numNeighs, 'euclidean')
    neighDist = ARC._ss.NeighborDistances(gaTable, gaSearch)
    N = len(gaTable)
    distances = NUM.empty((N, ), float)

    #### Find All Nearest Neighbor Distance ####
    for row in xrange(N):
        distances[row] = neighDist[row][-1][-1]
        ARCPY.SetProgressorPosition()

    #### Make Sure it is not Larger Than Standard Distance ####
    meanDist = distances.mean()
    if ssdo.useChordal:
        distValue = meanDist
        distanceStr = ssdo.distanceInfo.printDistance(distValue)
        msg = ARCPY.GetIDMessage(84464).format(numNeighs, distanceStr)
    else:
        sd = UTILS.standardDistanceCutoff(ssdo.xyCoords)
        if meanDist > sd:
            distValue = sd
            distanceStr = ssdo.distanceInfo.printDistance(distValue)
            msg = ARCPY.GetIDMessage(84465).format(distanceStr)
        else:
            distValue = meanDist
            distanceStr = ssdo.distanceInfo.printDistance(distValue)
            msg = ARCPY.GetIDMessage(84464).format(numNeighs, distanceStr)

    #### KNN/STD Answer ####
    printOHSAnswer(msg)

    return distValue

def setupOptHotSpot():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    #### Input Parameters ####
    inputFC = ARCPY.GetParameterAsText(0)
    outputFC = ARCPY.GetParameterAsText(1)
    varName = UTILS.getTextParameter(2, fieldName = True)
    aggMethod = UTILS.getTextParameter(3)
    if aggMethod:
        aggType = aggTypes[aggMethod.upper()]
    else:
        aggType = 1
    boundaryFC = UTILS.getTextParameter(4)
    polygonFC = UTILS.getTextParameter(5)
    outputRaster = UTILS.getTextParameter(6)


    makeFeatureLayerNoExtent = UTILS.clearExtent(DM.MakeFeatureLayer)
    selectLocationNoExtent = UTILS.clearExtent(DM.SelectLayerByLocation)
    featureLayer = "InputOHSA_FC"
    makeFeatureLayerNoExtent(inputFC, featureLayer)
    if boundaryFC:
        selectLocationNoExtent(featureLayer, "INTERSECT",
                                 boundaryFC, "#",
                                 "NEW_SELECTION")
        polygonFC = None

    if polygonFC:
        selectLocationNoExtent(featureLayer, "INTERSECT",
                                 polygonFC, "#",
                                 "NEW_SELECTION")
        boundaryFC = None

    #### Create SSDO ####
    ssdo = SSDO.SSDataObject(featureLayer, templateFC = outputFC, 
                             useChordal = True)

    hs = OptHotSpots(ssdo, outputFC, varName = varName, aggType = aggType,
                      polygonFC = polygonFC, boundaryFC = boundaryFC,
                      outputRaster = outputRaster)

    DM.Delete(featureLayer)

class OptHotSpots(object):
    """Optimized Hot-Spot Analysis Super Class.

    INPUTS:
    ssdo (obj): instance of SSDataObject where data has NOT been loaded
    outputFC (str): path to the output feature class
    varName {str, None}: name of the analysis/weight field
    aggType {int, 1}: type of aggregation method for unmarked points
    polygonFC {str, None}: path to polygons for aggregating incidents
    boundaryFC {str, None}: path to polygon(s) defining study area

    """

    def __init__(self, ssdo, outputFC, varName = None,
                 aggType = 1, polygonFC = None,
                 boundaryFC = None, outputRaster = None):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())
        ARCPY.env.overwriteOutput = True
        self.startExtent = ARCPY.env.extent
        ARCPY.env.extent = ""
        self.cleanUpList = []

        #### Runtime Checks ####
        if self.varName:
            self.varPopName = self.varName
        else:
            self.varPopName = None
            if self.aggType == 0:
                self.boundaryFC = None
                self.polygonFC = None
            if self.aggType == 1:
                self.polygonFC = None
            if self.aggType == 2:
                self.boundaryFC = None

        #### Hot Spot Subject String (Incident Counts or Fieldname Values ####
        if self.varPopName:
            varString = self.varPopName + " " + ARCPY.GetIDMessage(84468)
        else:
            varString = ARCPY.GetIDMessage(84469)
        self.varString = varString

        self.initialize()
        self.doHotSpots()
        if self.outputRaster:
            self.doRaster(self.outputRaster, varName = self.varPopName)
        self.cleanUp()

    def cleanUp(self):
        #### Delete Temp Structures ####
        for tempItem in self.cleanUpList:
            UTILS.passiveDelete(tempItem)
        
        #### Reset Extent ####
        ARCPY.env.extent = self.startExtent

        #### Final Line Print ####
        ARCPY.AddMessage("\n")

    def initialize(self):
        #### Decision Tree ####
        if not self.varName:
            #### Unmarked Points ####
            self.minNumIncidents = aggMins[self.aggType]
            if self.aggType == 0:
                self.doIntegrate()
            elif self.aggType == 2:
                self.doPoint2Poly()
            else:
                self.doFishnet()
        else:
            #### Weighted Features ####
            self.setAnalysisSSDO(self.ssdo.inputFC, self.varName)

    def checkPolygons(self, numObs):
        if numObs < minNumFeatures:
            ARCPY.AddIDMessage("ERROR", 1535, str(minNumFeatures))
            self.cleanUp()
            raise SystemExit()
        else:
            msg = ARCPY.GetIDMessage(84491).format(numObs)
            printOHSAnswer(msg)

    def checkBoundary(self):
        printOHSSubject(84486, addNewLine = False)

        #### Assure That There Is Only a Single Polygon ####
        cnt = UTILS.getCount(self.boundaryFC)
        if cnt > 1:
            #### Dissolve Polys into Boundary ####
            dissolveFC = UTILS.returnScratchName("Dissolve_TempFC")
            DM.Dissolve(self.boundaryFC, dissolveFC, "#", "#", "SINGLE_PART",
                        "DISSOLVE_LINES")
            self.boundaryFC = dissolveFC
            self.cleanUpList.append(dissolveFC)

        #### Read Boundary FC ####
        ssdoBound = SSDO.SSDataObject(self.boundaryFC,
                                 explicitSpatialRef = self.ssdo.spatialRef,
                                 silentWarnings = True,
                                 useChordal = True)

        polyDict, polyAreas = UTILS.readPolygonFC(self.boundaryFC,
                                spatialRef = self.ssdo.spatialRef,
                                useGeodesic = self.ssdo.useChordal)
        self.boundArea = sum(polyAreas.values())
        self.boundExtent = getPolyExtent(polyDict)

        del ssdoBound

        if UTILS.compareFloat(0.0, self.boundArea):
            #### Invalid Study Area ####
            ARCPY.AddIDMessage("ERROR", 932)
            self.cleanUp()
            raise SystemExit()
        else:
            areaStr = self.ssdo.distanceInfo.printDistance(self.boundArea)
            msg = ARCPY.GetIDMessage(84492).format(areaStr)
            printOHSAnswer(msg)

    def checkIncidents(self, numObs):
        self.cnt = numObs
        if self.aggType == 1 and not self.boundaryFC:
            #### Fish w/o Boundary Requires Twice Number ####
            self.minNumIncidents = self.minNumIncidents * 2
        if self.cnt < self.minNumIncidents:
            if self.aggType in [0,1]:
                if self.boundaryFC:
                    ARCPY.AddIDMessage("ERROR", 1570, str(self.minNumIncidents))
                else:
                    ARCPY.AddIDMessage("ERROR", 1536, 
                                       str(self.minNumIncidents),
                                       ARCPY.GetIDMessage(84501))
            else:
                ARCPY.AddIDMessage("ERROR", 1574, str(self.minNumIncidents))
            self.cleanUp()
            raise SystemExit()

        msg = ARCPY.GetIDMessage(84485).format(self.cnt)
        printOHSAnswer(msg)

    def doPoint2Poly(self):

        #### Initial Data Assessment ####
        printOHSSection(84428, prependNewLine = True)
        printOHSSubject(84431, addNewLine = False)
        self.ssdo.obtainData(self.ssdo.oidName)
        self.checkIncidents(self.ssdo.numObs)
        if len(self.ssdo.badRecords):
            ARCPY.AddMessage("\n")
        #################################

        #### Checking Polygon Message ####
        printOHSSubject(84430, addNewLine = False)

        #### Spatial Join (Hold Messages) ####
        outputFieldMaps = "EMPTY"
        tempFC = UTILS.returnScratchName("SpatialJoin_TempFC")
        self.cleanUpList.append(tempFC)
        joinWithSpatialRef = UTILS.funWithSpatialRef(ANA.SpatialJoin,
                                                     self.ssdo.spatialRef,
                                                     outputFC = tempFC)
        joinWithXY = UTILS.funWithXYTolerance(joinWithSpatialRef,
                                              self.ssdo.distanceInfo)
        joinWithXY(self.polygonFC, self.ssdo.inputFC, tempFC,
                   "JOIN_ONE_TO_ONE", "KEEP_ALL",
                   outputFieldMaps)

        #### Set VarName, MasterField, AnalysisSSDO ####
        self.createAnalysisSSDO(tempFC, "JOIN_COUNT")

    def validateRaster(self, ssdoCoords):

        printOHSSubject(84439, addNewLine = False)
        envMask = ARCPY.env.mask
        maskExists = False
        if envMask:
            try:
                descMask = ARCPY.Describe(envMask)
                maskExists = True
            except:
                maskExists = False

        if not envMask or not maskExists:
            #### Use Convex Hull ####
            msg = ARCPY.GetIDMessage(84440)
            ARCPY.SetProgressor("default", msg)
            printOHSAnswer(msg)
            boundaryFC = UTILS.returnScratchName("tempCH_FC")
            UTILS.minBoundGeomPoints(ssdoCoords, boundaryFC,
                                     geomType = "CONVEX_HULL",
                                     spatialRef = self.ssdo.spatialRef)
            self.boundaryFC = boundaryFC
            self.cleanUpList.append(boundaryFC)

        self.maskExists = maskExists

    def doIntegrate(self):
        #### Initial Data Assessment ####
        printOHSSection(84428, prependNewLine = True)
        printOHSSubject(84431, addNewLine = False)

        #### Find Unique Locations ####
        msg = ARCPY.GetIDMessage(84441)
        ARCPY.SetProgressor("default", msg)
        initCount = UTILS.getCount(self.ssdo.inputFC)
        self.checkIncidents(initCount)
        collectedPointFC = UTILS.returnScratchName("Collect_InitTempFC")
        collInfo = EVENTS.collectEvents(self.ssdo, collectedPointFC)
        self.cleanUpList.append(collectedPointFC)
            
        collSSDO = SSDO.SSDataObject(collectedPointFC,
                                explicitSpatialRef = self.ssdo.spatialRef,
                                        useChordal = True)
        collSSDO.obtainDataGA(collSSDO.oidName)
        #################################

        #### Locational Outliers ####
        lo = UTILS.LocationInfo(collSSDO, concept = "EUCLIDEAN",
                                silentThreshold = True, stdDeviations = 3)
        printOHSLocationalOutliers(lo, aggType = self.aggType)

        #### Raster Boundary ####
        if self.outputRaster:
            self.validateRaster(collSSDO.xyCoords)

        #### Agg Header ####
        printOHSSection(84444)

        #### Copy Features for Integrate ####
        msg = ARCPY.GetIDMessage(84443)
        ARCPY.SetProgressor("default", msg)
        intFC = UTILS.returnScratchName("Integrated_TempFC")
        self.cleanUpList.append(intFC)
        DM.CopyFeatures(self.ssdo.inputFC, intFC)

        #### Make Feature Layer To Avoid Integrate Bug with Spaces ####
        mfc = "Integrate_MFC_2"
        DM.MakeFeatureLayer(intFC, mfc)
        self.cleanUpList.append(mfc)

        #### Snap Subject ####
        printOHSSubject(84442, addNewLine = False)
        nScale = (collSSDO.numObs * 1.0) / self.cnt
        if lo.nonZeroAvgDist < lo.nonZeroMedDist:
            useDist = lo.nonZeroAvgDist * nScale
            useType = "average"
        else:
            useDist = lo.nonZeroMedDist * nScale
            useType = "median"
        distance2Integrate = lo.distances[lo.distances < useDist]
        distance2Integrate = NUM.sort(distance2Integrate)
        numDists = len(distance2Integrate)

        #### Max Snap Answer ####
        msg = ARCPY.GetIDMessage(84445)
        useDistStr = self.ssdo.distanceInfo.printDistance(useDist)
        msg = msg.format(useDistStr)
        printOHSAnswer(msg)

        percs = [10, 25, 100]
        indices = [ int(numDists * (i * .01)) for i in percs ]
        if indices[-1] >= numDists:
            indices[-1] = -1

        ARCPY.SetProgressor("default", msg)
        for pInd, dInd in enumerate(indices):
            dist = distance2Integrate[dInd]
            snap = self.ssdo.distanceInfo.linearUnitString(dist,
                                                           convert = True)
            DM.Integrate(mfc, snap)
        del collSSDO

        #### Run Collect Events ####
        collectedFC = UTILS.returnScratchName("Collect_TempFC")
        self.cleanUpList.append(collectedFC)
        intSSDO = SSDO.SSDataObject(intFC,
                                    explicitSpatialRef = self.ssdo.spatialRef,
                                    silentWarnings = True,
                                    useChordal = True)
        intSSDO.obtainDataGA(intSSDO.oidName)
        EVENTS.collectEvents(intSSDO, collectedFC)
        descTemp = ARCPY.Describe(collectedFC)
        oidName = descTemp.oidFieldName

        #### Delete Integrated FC ####
        del intSSDO

        #### Set VarName, MasterField, AnalysisSSDO ####
        self.createAnalysisSSDO(collectedFC, "ICOUNT")

    def doFishnet(self):
        #### Initial Data Assessment ####
        printOHSSection(84428, prependNewLine = True)
        printOHSSubject(84431, addNewLine = False)

        #### Find Unique Locations ####
        msg = ARCPY.GetIDMessage(84441)
        ARCPY.SetProgressor("default", msg)
        initCount = UTILS.getCount(self.ssdo.inputFC)
        self.checkIncidents(initCount)
        collectedPointFC = UTILS.returnScratchName("Collect_InitTempFC")
        collInfo = EVENTS.collectEvents(self.ssdo, collectedPointFC)
        self.cleanUpList.append(collectedPointFC)
        collSSDO = SSDO.SSDataObject(collectedPointFC,
                                   explicitSpatialRef = self.ssdo.spatialRef,
                                   useChordal = True)
        collSSDO.obtainDataGA(collSSDO.oidName)
        #################################

        if self.boundaryFC:
            #### Assure Boundary FC Has Area and Obtain Chars ####
            self.checkBoundary()

        #### Location Outliers ####
        lo = UTILS.LocationInfo(collSSDO, concept = "EUCLIDEAN",
                                silentThreshold = True, stdDeviations = 3)
        printOHSLocationalOutliers(lo, aggType = self.aggType)

        #### Agg Header ####
        printOHSSection(84444)
        if self.boundaryFC:
            extent = self.boundExtent
            forMercExtent = self.boundExtent
            countMSGNumber = 84453

        else:
            countMSGNumber = 84452
            extent = None
            forMercExtent = collSSDO.extent

        if collSSDO.useChordal:
            extentFC_GCS = UTILS.returnScratchName("TempGCS_Extent")
            extentFC_Merc = UTILS.returnScratchName("TempMercator_Extent")
            points = NUM.array([ [forMercExtent.XMin, forMercExtent.YMax],
                                 [forMercExtent.XMax, forMercExtent.YMin] ])
            UTILS.createPointFC(extentFC_GCS, points, 
                                spatialRef = collSSDO.spatialRef)
            DM.Project(extentFC_GCS, extentFC_Merc, mercatorProjection)
            d = ARCPY.Describe(extentFC_Merc)
            extent = d.extent
            fishOutputCoords = mercatorProjection 
        else:
            fishOutputCoords = self.ssdo.spatialRef

        #### Fish Subject ####
        printOHSSubject(84449, addNewLine = False)
        dist = scaleDecision(lo.nonZeroAvgDist, lo.nonZeroMedDist)
        area = 0.0

        #### Construct Fishnet ####
        fish = UTILS.FishnetInfo(collSSDO, area, extent,
                                 explicitCellSize = dist)
        dist = fish.quadLength
        snap = self.ssdo.distanceInfo.linearUnitString(dist)

        #### Cell Size Answer ####
        snapStr = self.ssdo.distanceInfo.printDistance(dist)
        msg = ARCPY.GetIDMessage(84450).format(snapStr)
        printOHSAnswer(msg)
        self.fish = fish

        #### Fishnet Count Subject ####
        printOHSSubject(84451, addNewLine = False)

        #### Create Temp Fishnet Grid ####
        gridFC = UTILS.returnScratchName("Fishnet_TempFC")
        self.cleanUpList.append(gridFC)

        #### Apply Output Coords to Create Fishnet ####
        oldSpatRef = ARCPY.env.outputCoordinateSystem
        ARCPY.env.outputCoordinateSystem = fishOutputCoords

        #### Fish No Extent ####
        oldExtent = ARCPY.env.extent
        ARCPY.env.extent = ""

        #### Apply Max XY Tolerance ####
        fishWithXY = UTILS.funWithXYTolerance(DM.CreateFishnet,
                                              self.ssdo.distanceInfo)

        #### Execute Fishnet ####
        fishWithXY(gridFC, self.fish.origin, self.fish.rotate,
                   self.fish.quadLength, self.fish.quadLength,
                   self.fish.numRows, self.fish.numCols, self.fish.corner,
                   "NO_LABELS", self.fish.extent, "POLYGON")

        #### Project Back to GCS if Use Chordal ####
        if collSSDO.useChordal:
            gridFC_ProjBack = UTILS.returnScratchName("TempFC_Proj")
            DM.Project(gridFC, gridFC_ProjBack, collSSDO.spatialRef)
            UTILS.passiveDelete(gridFC)
            gridFC = gridFC_ProjBack

        #### Set Env Output Coords Back ####
        ARCPY.env.outputCoordinateSystem = oldSpatRef

        #### Create Empty Field Mappings to Ignore Atts ####
        fieldMap = ARCPY.FieldMappings()
        fieldMap.addTable(self.ssdo.inputFC)
        fieldMap.removeAll()

        #### Fishnet Count Answer ####
        printOHSAnswer(ARCPY.GetIDMessage(countMSGNumber))

        #### Create Weighted Fishnet Grid ####
        tempFC = UTILS.returnScratchName("Optimized_TempFC")
        self.cleanUpList.append(tempFC)
        joinWithXY = UTILS.funWithXYTolerance(ANA.SpatialJoin,
                                              self.ssdo.distanceInfo)
        joinWithXY(gridFC, self.ssdo.inputFC, tempFC,
                   "JOIN_ONE_TO_ONE", "KEEP_ALL", "EMPTY")

        #### Clean Up Temp FCs ####
        UTILS.passiveDelete(gridFC)

        #### Remove Locations Outside Boundary FC ####
        featureLayer = "ClippedPointFC"
        DM.MakeFeatureLayer(tempFC, featureLayer)
        if self.boundaryFC:
            msg = ARCPY.GetIDMessage(84454)
            ARCPY.SetProgressor("default", msg)
            DM.SelectLayerByLocation(featureLayer, "INTERSECT",
                                     self.boundaryFC, "#",
                                     "NEW_SELECTION")
            DM.SelectLayerByLocation(featureLayer, "INTERSECT",
                                 "#", "#", "SWITCH_SELECTION")
            DM.DeleteFeatures(featureLayer)
        else:
            if additionalZeroDistScale == "ALL":
                msg = ARCPY.GetIDMessage(84455)
                ARCPY.SetProgressor("default", msg)
                DM.SelectLayerByAttribute(featureLayer, "NEW_SELECTION",
                                      '"Join_Count" = 0')
                DM.DeleteFeatures(featureLayer)

            else:
                distance = additionalZeroDistScale * fish.quadLength
                distanceStr = self.ssdo.distanceInfo.linearUnitString(distance, 
                                                                convert = True)
                nativeStr = self.ssdo.distanceInfo.printDistance(distance)
                msg = "Removing cells further than %s from input pointsd...." 
                ARCPY.AddMessage(msg % nativeStr)
                DM.SelectLayerByLocation(featureLayer, "INTERSECT",
                                         self.ssdo.inputFC, distanceStr,
                                         "NEW_SELECTION")
                DM.SelectLayerByLocation(featureLayer, "INTERSECT",
                                         "#", "#", "SWITCH_SELECTION")
                DM.DeleteFeatures(featureLayer)

        DM.Delete(featureLayer)
        del collSSDO

        ARCPY.env.extent = oldExtent
        self.createAnalysisSSDO(tempFC, "JOIN_COUNT")

    def createAnalysisSSDO(self, tempFC, varName):
        self.varName = varName
        self.analysisSSDO = SSDO.SSDataObject(tempFC,
                                   explicitSpatialRef = self.ssdo.spatialRef,
                                   useChordal = True)
        self.masterField = UTILS.setUniqueIDField(self.analysisSSDO)
        self.analysisSSDO.obtainDataGA(self.masterField, [self.varName])

        if self.aggType == 2:
            #### Verify Enough Polygons ####
            self.checkPolygons(self.analysisSSDO.numObs)

            #### Locational Outliers ####
            lo = UTILS.LocationInfo(self.analysisSSDO, concept = "EUCLIDEAN",
                                silentThreshold = True, stdDeviations = 3)
            printOHSLocationalOutliers(lo, aggType = self.aggType)

            #### Agg Header ####
            printOHSSection(84444)

            #### Do Spatial Join ####
            msg = ARCPY.GetIDMessage(84458)
            printOHSSubject(84458, addNewLine = False)
            msg = ARCPY.GetIDMessage(84489)
            printOHSAnswer(msg)

        #### Analyze Incident Subject ####
        msgID = aggHeaders[self.aggType]
        msg = ARCPY.GetIDMessage(msgID)
        ARCPY.SetProgressor("default", msg)
        printOHSSubject(msgID, addNewLine = False)

        #### Errors and Warnings ####
        y = self.analysisSSDO.fields[self.varName].returnDouble()
        yVar = NUM.var(y)
        if self.analysisSSDO.numObs < 30:
            #### Too Few Aggregated Features ####
            if self.boundaryFC:
                ARCPY.AddIDMessage("ERROR", 1573)
            else:
                ARCPY.AddIDMessage("ERROR", 1572)
            self.cleanUp()
            raise SystemExit()

        #### Zero Variance ####
        if NUM.isnan(yVar) or yVar <= 0.0:
            if self.aggType == 2:
                ARCPY.AddIDMessage("ERROR", 1534)
                self.cleanUp()
                raise SystemExit()
            else:
                ARCPY.AddIDMessage("ERROR", 1533)
                self.cleanUp()
                raise SystemExit()

        #### Count Description ####
        if self.aggType:
            msgID = 84490
        else:
            msgID = 84447
        msg = ARCPY.GetIDMessage(msgID).format(len(y))
        printOHSAnswer(msg, addNewLine = False)
        varNameCounts = ARCPY.GetIDMessage(84488)
        msg = ARCPY.GetIDMessage(84446).format(varNameCounts)
        printOHSAnswer(msg, addNewLine = False)
        printWeightAnswer(y)

    def setAnalysisSSDO(self, tempFC, varName):
        #### Initial Data Assessment ####
        printOHSSection(84428, prependNewLine = True)

        self.varName = varName
        self.analysisSSDO = self.ssdo
        self.masterField = UTILS.setUniqueIDField(self.analysisSSDO)
        if UTILS.renderType[self.ssdo.shapeType.upper()]:
            stringShape =  ARCPY.GetIDMessage(84502)
        else:
            stringShape =  ARCPY.GetIDMessage(84501)

        #### Assure Enough Features (Q) ####
        printOHSSubject(84429, addNewLine = False)
        self.analysisSSDO.obtainDataGA(self.masterField, [self.varName])
        if len(self.analysisSSDO.badRecords):
            ARCPY.AddMessage("\n")
        if self.analysisSSDO.numObs < 30:
            ARCPY.AddIDMessage("ERROR", 1571, '30', stringShape)
            self.cleanUp()
            raise SystemExit()

        msg = ARCPY.GetIDMessage(84485).format(self.analysisSSDO.numObs)
        printOHSAnswer(msg)

        #### Errors and Warnings ####
        printOHSSubject(84432, addNewLine = False)
        y = self.analysisSSDO.fields[self.varName].returnDouble()
        yVar = NUM.var(y)

        #### Zero Variance ####
        if NUM.isnan(yVar) or yVar <= 0.0:
            ARCPY.AddIDMessage("ERROR", 1575)
            self.cleanUp()
            raise SystemExit()

        #### Analysis Var Description ####
        msg = ARCPY.GetIDMessage(84446).format(self.varName)
        printOHSAnswer(msg, addNewLine = False)
        printWeightAnswer(y)

        #### Locational Outliers ####
        lo = UTILS.LocationInfo(self.analysisSSDO, concept = "EUCLIDEAN",
                                silentThreshold = True, stdDeviations = 3)
        printOHSLocationalOutliers(lo, aggType = 2)

        #### Raster Boundary ####
        if self.outputRaster:
            self.validateRaster(self.analysisSSDO.xyCoords)

    def doHotSpots(self):
        #### Scale Header ####
        printOHSSection(84459)

        #### Scale Subject ####
        msg = ARCPY.GetIDMessage(84460)
        ARCPY.SetProgressor("default", msg)
        printOHSSubject(84460, addNewLine = False)

        #### Run Incremental Spatial AutoCorrelation ####
        self.templateDir = OS.path.dirname(OS.path.dirname(SYS.argv[0]))
        mi = MI.GlobalI_Step(self.analysisSSDO, self.varName,
                             includeCoincident = False,
                             stdDeviations = 3,
                             silent = True,
                             stopMax = 500)

        #### Set Distance or KNN ####
        peakFound = False
        if mi.completed:
            if mi.firstPeakDistance:
                distanceBand = mi.firstPeakDistance
                distanceStr = self.ssdo.distanceInfo.printDistance(distanceBand)
                peakInd = mi.firstPeakInd
                msg = ARCPY.GetIDMessage(84461).format(distanceStr)
                printOHSAnswer(msg)
                numNeighs = 0
                wType = 1
                peakFound = True

            elif mi.maxPeakDistance:
                distanceBand = mi.maxPeakDistance
                distanceStr = self.ssdo.distanceInfo.printDistance(distanceBand)
                peakInd = mi.maxPeakInd
                msg = ARCPY.GetIDMessage(84461).format(distanceStr)
                printOHSAnswer(msg)
                numNeighs = 0
                wType = 1
                peakFound = True

        if not peakFound:
            #### Use KNN If No Peak OR More than 500 Neighs ####
            msg = ARCPY.GetIDMessage(84462)
            printOHSAnswer(msg)
            distanceBand = knnDecision(self.analysisSSDO)
            distanceStr = self.ssdo.distanceInfo.printDistance(distanceBand)
            wType = 1
            numNeighs = 0

        self.distanceBand = distanceBand
        self.distanceStr = distanceStr

        #### Run Local Gi* ####
        msg = ARCPY.GetIDMessage(84466)
        ARCPY.SetProgressor("default", msg)

        #### Hot Spot Header ####
        printOHSSection(84466)

        #### Subject w/ Value - Use AddMessage Explicitly ####
        varMSG = ARCPY.GetIDMessage(84467).format(self.varString)
        ARCPY.AddMessage(varMSG)

        #### Run Analysis ####
        gi = GISTAR.LocalG(self.analysisSSDO, self.varName, self.outputFC,
                           wType, threshold = distanceBand,
                           numNeighs = numNeighs,
                           permutations = numPerms,
                           applyFDR = True)

        #### FDR Significance ####
        numSig = (gi.giBins != 0).sum()
        msg = ARCPY.GetIDMessage(84470).format(numSig)
        printOHSAnswer(msg)

        #### Wrap Up Header ####
        printOHSSection(84471)

        #### Subject w/ Value - Use AddMessage Explicitly ####
        outMSG = ARCPY.GetIDMessage(84475).format(self.outputFC)
        ARCPY.AddMessage(outMSG)
        giField, pvField = gi.outputResults()
        hotMSG = ARCPY.GetIDMessage(84476).format(self.varString)
        printOHSAnswer(hotMSG, addNewLine = False)
        coldMSG = ARCPY.GetIDMessage(84477).format(self.varString)
        printOHSAnswer(coldMSG)

        #### Set the Default Symbology ####
        self.params = ARCPY.gp.GetParameterInfo()
        try:
            renderType = UTILS.renderType[self.analysisSSDO.shapeType.upper()]
            renderLayerFile = GISTAR.giRenderDict[renderType]
            fullRLF = OS.path.join(self.templateDir, "Templates",
                                   "Layers", renderLayerFile)
            self.params[1].Symbology = fullRLF
        except:
            ARCPY.AddIDMessage("WARNING", 973)

    def doRaster(self, outputRaster, varName = None):
        """Creates the Output Raster."""

        renderType = UTILS.renderType[self.ssdo.shapeType.upper()]
        if renderType:
            #### No Output When Not Points ####
            printOHSSubject(84480)
        else:
            if varName:
                msg = ARCPY.GetIDMessage(84479)
                rasterLayerFile = "PointDensityHSGray.lyr"
            else:
                msg = ARCPY.GetIDMessage(84478)
                rasterLayerFile = "PointDensityHSGrayPoints.lyr"
            ARCPY.SetProgressor("default", msg)

            #### Subject w/ Value - Use AddMessage Explicitly ####
            outMSG = ARCPY.GetIDMessage(84497).format(outputRaster)
            ARCPY.AddMessage(outMSG)

            #### Distance Band Answer ####
            msg = ARCPY.GetIDMessage(84481).format(self.distanceStr)
            printOHSAnswer(msg, addNewLine = False)

            #### Clip Message ####
            if self.maskExists:
                msg = ARCPY.GetIDMessage(84483)
            else:
                msg = ARCPY.GetIDMessage(84482)
            printOHSAnswer(msg)

            #### Do Raster ####
            try:
                UTILS.fc2DensityRaster(self.ssdo.inputFC, outputRaster,
                                       varName,
                                       boundaryFC = self.boundaryFC,
                                       searchRadius = self.distanceBand)
            except:
                msg = ARCPY.GetIDMessage(84498)
                printOHSAnswer(msg)

            #### Set Symbology ####
            fullRLF = OS.path.join(self.templateDir, "Templates",
                                   "Layers", rasterLayerFile)
            self.params[6].Symbology = fullRLF

if __name__ == "__main__":
    setupOptHotSpot()
