"""
Tool Name:     Generate Spatial Weights Matrix 
Source Name:   Weights.py
Version:       ArcGIS 10.0
Author:        Environmental Systems Research Institute Inc.
Description:   Creates spatial weights in SWM format:
               
               Header Information:
                    MasterField (str)
                    Row Standard (boolean)
                    N (int) # of observations in W

               Weight Information comes in the form of four seperate
               arrays of information for each record:
                    Unique_ID (int), Number of Neighbors (int)
                    Neighbors IDs (array of ints)
                    Weights (array of floats)
                    SumWeights (float) [unstandardized sum]
"""

################### Imports ########################
import os as OS
import sys as SYS
import numpy as NUM
import locale as LOCALE
import arcgisscripting as ARC
import arcpy as ARCPY
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import WeightsUtilities as WU
import SSDataObject as SSDO 
import gapy as GAPY
import SSTimeUtilities as TUTILS

################### Helper Methods #####################
def checkDistanceThresholdSWM(ssdo, threshold, maxExtent):
    if threshold < 0:
        #### Negative Values Not Valid ####
        ARCPY.AddIDMessage("ERROR", 933)
        raise SystemExit()

    softWarn = False
    if ssdo.useChordal:
        softMaxExtent = maxExtent
        hardMaxExtent = ARC._ss.get_max_gcs_distance(ssdo.spatialRef)
        if softMaxExtent < hardMaxExtent:
            maxExtent = softMaxExtent
            softWarn = True
        else:
            maxExtent = hardMaxExtent

    if threshold == 0:
        #### Infinite Radius Not Valid For Fixed and ZOI ####
        ARCPY.AddIDMessage("ERROR", 928)
        raise SystemExit()

    #### Assure that the Radius is Smaller than the Max Extent ####
    if threshold > maxExtent:
        #### Can Not be Greater or Equal to Extent ####
        #### Applies to Fixed (1) and ZOI (7) ####
        if ssdo.useChordal and not softWarn:
            ARCPY.AddIDMessage("ERROR", 1607)
            raise SystemExit()
        else:
            ARCPY.AddIDMessage("ERROR", 929)
            raise SystemExit()
    
    return threshold

################### GUI Interface ######################
def setupWeights():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)      
    masterField = ARCPY.GetParameterAsText(1)
    swmFile = ARCPY.GetParameterAsText(2)
    spaceConcept = ARCPY.GetParameterAsText(3)
    distanceConcept = ARCPY.GetParameterAsText(4)
    exponent = UTILS.getNumericParameter(5)
    threshold = UTILS.getNumericParameter(6)
    kNeighs = UTILS.getNumericParameter(7)
    rowStandard = ARCPY.GetParameter(8)
    tableFile = ARCPY.GetParameterAsText(9)

    #### Assess Temporal Options ####'
    timeField = UTILS.getTextParameter(10, fieldName = True)
    timeType = UTILS.getTextParameter(11)
    timeValue = UTILS.getNumericParameter(12)

    #### Assign to appropriate spatial weights method ####
    try:
        wType = WU.weightDispatch[spaceConcept]
    except:
        ARCPY.AddIDMessage("Error", 723)
        raise SystemExit()

    #### EUCLIDEAN or MANHATTAN ####
    concept = WU.conceptDispatch[distanceConcept]
    if not kNeighs:
        kNeighs = 0

    if wType <= 1:
        #### Distance Based Weights ####
        ARCPY.AddMessage(ARCPY.GetIDMessage(84118))

        #### Set Options for Fixed vs. Inverse ####
        if wType == 0:        
            exponent = exponent
            fixed = 0
        else:
            exponent = 1
            fixed = 1
        
        #### Execute Distance-Based Weights ####
        w = distance2SWM(inputFC, swmFile, masterField, fixed = fixed, 
                         concept = concept, exponent = exponent, 
                         threshold = threshold, kNeighs = kNeighs, 
                         rowStandard = rowStandard)

    elif wType == 2:
        #### k-Nearest Neighbors Weights ####
        ARCPY.AddMessage(ARCPY.GetIDMessage(84119))
        w = kNearest2SWM(inputFC, swmFile, masterField, concept = concept,
                         kNeighs = kNeighs, rowStandard = rowStandard)

    elif wType == 3:
        #### Delaunay Triangulation Weights ####
        ARCPY.AddMessage(ARCPY.GetIDMessage(84120))
        w = delaunay2SWM(inputFC, swmFile, masterField, 
                         rowStandard = rowStandard)

    elif wType == 4:
        #### Contiguity Based Weights, Edges Only ####
        ARCPY.AddMessage(ARCPY.GetIDMessage(84121))
        w = polygon2SWM(inputFC, swmFile, masterField, concept = concept, 
                        kNeighs = kNeighs, rowStandard = rowStandard,
                        contiguityType = "ROOK")

    elif wType == 5:
        #### Contiguity Based Weights, Edges and Corners ####
        ARCPY.AddMessage(ARCPY.GetIDMessage(84122))
        w = polygon2SWM(inputFC, swmFile, masterField, concept = concept, 
                        kNeighs = kNeighs, rowStandard = rowStandard,
                        contiguityType = "QUEEN")

    elif wType == 9:
        ARCPY.AddMessage(ARCPY.GetIDMessage(84255))
        w = spaceTime2SWM(inputFC, swmFile, masterField, concept = concept,
                          threshold = threshold, rowStandard = rowStandard,
                          timeField = timeField, timeType = timeType,
                          timeValue = timeValue)

    else:
        #### Tabular Input for Weights ####
        ARCPY.AddMessage(ARCPY.GetIDMessage(84123))
        if tableFile == "" or tableFile == "#":
            ARCPY.AddIDMessage("Error", 721)
            raise SystemExit()
        else: 
            table2SWM(inputFC, masterField, swmFile, tableFile, 
                      rowStandard = rowStandard) 

################### Methods ########################

def polygon2SWM(inputFC, swmFile, masterField, 
                concept = "EUCLIDEAN", kNeighs = 0,
                rowStandard = True, contiguityType = "ROOK"):
    """Creates a sparse spatial weights matrix (SWM) based on polygon
    contiguity. 

    INPUTS: 
    inputFC (str): path to the input feature class
    swmFile (str): path to the SWM file.
    masterField (str): field in table that serves as the mapping.
    concept: {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN
    kNeighs {int, 0}: number of neighbors to return (1)
    rowStandard {bool, True}: row standardize weights?
    contiguityType {str, Rook}: {Rook = Edges Only, Queen = Edges/Vertices}

    NOTES:
    (1) kNeighs is used if polygon is not contiguous. E.g. Islands
    """

    #### Set Default Progressor for Neigborhood Structure ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84143))

    #### Create SSDataObject ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = inputFC,
                             useChordal = True)
    cnt = UTILS.getCount(inputFC)
    ERROR.errorNumberOfObs(cnt, minNumObs = 2)

    #### Validation of Master Field ####
    verifyMaster = ERROR.checkField(ssdo.allFields, masterField, 
                                    types = [0,1])

    #### Create GA Data Structure ####
    gaTable, gaInfo = WU.gaTable(ssdo.catPath, [masterField],
                                 spatRef = ssdo.spatialRefString)

    #### Assure Enough Observations ####
    N = gaInfo[0]
    ERROR.errorNumberOfObs(N, minNumObs = 2)

    #### Assure k-Nearest is Less Than Number of Features ####
    if kNeighs >= N:
        ARCPY.AddIDMessage("ERROR", 975)
        raise SystemExit()

    #### Create Nearest Neighbor Search Type For Islands ####
    gaSearch = GAPY.ga_nsearch(gaTable)
    concept, gaConcept = WU.validateDistanceMethod(concept, ssdo.spatialRef)
    gaSearch.init_nearest(0.0, kNeighs, gaConcept)
    if kNeighs > 0:
        forceNeighbor = True
        neighWeights = ARC._ss.NeighborWeights(gaTable, gaSearch, 
                                              weight_type = 1,
                                              row_standard = False)
    else:
        forceNeighbor = False
        neighSearch = None

    #### Create Polygon Neighbors ####
    polyNeighborDict = WU.polygonNeighborDict(inputFC, masterField, 
                                   contiguityType = contiguityType)

    #### Write Poly Neighbor List (Dict) ####
    #### Set Progressor for SWM Writing ####
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84127), 0, N, 1)

    #### Initialize Spatial Weights Matrix File ####
    if contiguityType == "ROOK":
        wType = 4
    else:
        wType = 5

    swmWriter = WU.SWMWriter(swmFile, masterField, ssdo.spatialRefName, 
                             N, rowStandard, inputFC = inputFC,
                             wType = wType, distanceMethod = concept,
                             numNeighs = kNeighs)

    #### Keep Track of Polygons w/o Neighbors ####
    islandPolys = []
    
    #### Write Polygon Contiguity to SWM File ####
    for row in xrange(N):
        rowInfo = gaTable[row]
        oid = rowInfo[0]
        masterID = rowInfo[2]
        neighs = polyNeighborDict[masterID]
        if neighs:
            weights = [ 1. for nh in neighs ]
            isIsland = False
        else:
            isIsland = True
            islandPolys.append(oid)
            weights = []

        #### Get Nearest Neighbor Based On Centroid Distance ####
        if isIsland and forceNeighbor:
            neighs, weights = neighWeights[row]
            neighs = [ gaTable[nh][2] for nh in neighs ]

        #### Add Weights Entry ####
        swmWriter.swm.writeEntry(masterID, neighs, weights)

        #### Set Progress ####
        ARCPY.SetProgressorPosition()

    #### Report on Features with No Neighbors ####
    countIslands = len(islandPolys)
    if countIslands:
        islandPolys.sort()
        if countIslands > 30:
            islandPolys = islandPolys[0:30]
        
        ERROR.warningNoNeighbors(N, countIslands, islandPolys, ssdo.oidName, 
                                 forceNeighbor = forceNeighbor, 
                                 contiguity = True)

    #### Clean Up ####
    swmWriter.close()
    del gaTable

    #### Report Spatial Weights Summary ####
    swmWriter.report()

    #### Report SWM File is Large ####
    swmWriter.reportLargeSWM()

    del polyNeighborDict

def delaunay2SWM(inputFC, swmFile, masterField, rowStandard = True):
    """Creates a sparse spatial weights matrix (SWM) based on Delaunay
    Triangulation.  

    INPUTS: 
    inputFC (str): path to the input feature class
    swmFile (str): path to the SWM file.
    masterField (str): field in table that serves as the mapping.
    rowStandard {bool, True}: row standardize weights?
    """

    #### Set Default Progressor for Neigborhood Structure ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84143))

    #### Create SSDataObject ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = inputFC,
                             useChordal = True)
    cnt = UTILS.getCount(inputFC)
    ERROR.errorNumberOfObs(cnt, minNumObs = 2)

    #### Validation of Master Field ####
    verifyMaster = ERROR.checkField(ssdo.allFields, masterField, types = [0,1])

    #### Create GA Data Structure ####
    gaTable, gaInfo = WU.gaTable(ssdo.catPath, [masterField],
                                 spatRef = ssdo.spatialRefString)

    #### Assure Enough Observations ####
    N = gaInfo[0]
    ERROR.errorNumberOfObs(N, minNumObs = 2)

    #### Process any bad records encountered ####
    numBadRecs = cnt - N
    if numBadRecs:
        badRecs = WU.parseGAWarnings(gaTable.warnings)
        err = ERROR.reportBadRecords(cnt, numBadRecs, badRecs,
                                     label = ssdo.oidName)

    #### Create Delaunay Neighbor Search Type ####
    gaSearch = GAPY.ga_nsearch(gaTable)
    gaSearch.init_delaunay()
    neighWeights = ARC._ss.NeighborWeights(gaTable, gaSearch, 
                                           weight_type = 1,
                                           row_standard = False)

    #### Set Progressor for Weights Writing ####
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84127), 0, N, 1)

    #### Initialize Spatial Weights Matrix File ####
    swmWriter = WU.SWMWriter(swmFile, masterField, ssdo.spatialRefName, 
                             N, rowStandard, inputFC = inputFC,
                             wType = 3)

    #### Unique Master ID Dictionary ####
    masterSet = set([])

    for row in xrange(N):
        masterID = int(gaTable[row][2])
        if masterID in masterSet:
            ARCPY.AddIDMessage("Error", 644, masterField)
            ARCPY.AddIDMessage("Error", 643)
            raise SystemExit()
        else:
            masterSet.add(masterID)

        neighs, weights = neighWeights[row]
        neighs = [ gaTable[nh][2] for nh in neighs ]

        #### Add Spatial Weights Matrix Entry ####
        swmWriter.swm.writeEntry(masterID, neighs, weights) 

        #### Set Progress ####
        ARCPY.SetProgressorPosition()

    #### Clean Up ####
    swmWriter.close()
    del gaTable

    #### Report if Any Features Have No Neighbors ####
    swmWriter.reportNoNeighbors()

    #### Report Spatial Weights Summary ####
    swmWriter.report()

    #### Report SWM File is Large ####
    swmWriter.reportLargeSWM()

def kNearest2SWM(inputFC, swmFile, masterField, concept = "EUCLIDEAN", 
                 kNeighs = 1, rowStandard = True):
    """Creates a sparse spatial weights matrix (SWM) based on k-nearest
    neighbors.

    INPUTS: 
    inputFC (str): path to the input feature class
    swmFile (str): path to the SWM file.
    masterField (str): field in table that serves as the mapping.
    concept: {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN 
    kNeighs {int, 1}: number of neighbors to return
    rowStandard {bool, True}: row standardize weights?
    """

    #### Assure that kNeighs is Non-Zero ####
    if kNeighs <= 0:
        ARCPY.AddIDMessage("ERROR", 976)
        raise SystemExit()

    #### Set Default Progressor for Neigborhood Structure ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84143))

    #### Create SSDataObject ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = inputFC,
                             useChordal = True)
    cnt = UTILS.getCount(inputFC)
    ERROR.errorNumberOfObs(cnt, minNumObs = 2)

    #### Validation of Master Field ####
    verifyMaster = ERROR.checkField(ssdo.allFields, masterField, types = [0,1])

    #### Create GA Data Structure ####
    gaTable, gaInfo = WU.gaTable(ssdo.catPath, [masterField],
                                 spatRef = ssdo.spatialRefString)

    #### Assure Enough Observations ####
    N = gaInfo[0]
    ERROR.errorNumberOfObs(N, minNumObs = 2)

    #### Process any bad records encountered ####
    numBadRecs = cnt - N
    if numBadRecs:
        badRecs = WU.parseGAWarnings(gaTable.warnings)
        err = ERROR.reportBadRecords(cnt, numBadRecs, badRecs,
                                     label = ssdo.oidName)

    #### Assure k-Nearest is Less Than Number of Features ####
    if kNeighs >= N:
        ARCPY.AddIDMessage("ERROR", 975)
        raise SystemExit()

    #### Create k-Nearest Neighbor Search Type ####
    gaSearch = GAPY.ga_nsearch(gaTable)
    concept, gaConcept = WU.validateDistanceMethod(concept, ssdo.spatialRef)
    gaSearch.init_nearest(0.0, kNeighs, gaConcept)
    neighWeights = ARC._ss.NeighborWeights(gaTable, gaSearch, 
                                           weight_type = 1,
                                           row_standard = False)

    #### Set Progressor for Weights Writing ####
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84127), 0, N, 1)

    #### Initialize Spatial Weights Matrix File ####
    swmWriter = WU.SWMWriter(swmFile, masterField, ssdo.spatialRefName, 
                             N, rowStandard, inputFC = inputFC,
                             wType = 2, distanceMethod = concept,
                             numNeighs = kNeighs)

    #### Unique Master ID Dictionary ####
    masterSet = set([])

    for row in xrange(N):
        masterID = int(gaTable[row][2])
        if masterID in masterSet:
            ARCPY.AddIDMessage("Error", 644, masterField)
            ARCPY.AddIDMessage("Error", 643)
            raise SystemExit()
        else:
            masterSet.add(masterID)

        neighs, weights = neighWeights[row]
        neighs = [ gaTable[nh][2] for nh in neighs ]

        #### Add Spatial Weights Matrix Entry ####
        swmWriter.swm.writeEntry(masterID, neighs, weights) 

        #### Set Progress ####
        ARCPY.SetProgressorPosition()

    swmWriter.close()
    del gaTable

    #### Report Warning/Max Neighbors ####
    swmWriter.reportNeighInfo()

    #### Report Spatial Weights Summary ####
    swmWriter.report()

    #### Report SWM File is Large ####
    swmWriter.reportLargeSWM()

def distance2SWM(inputFC, swmFile, masterField, fixed = 0, 
                 concept = "EUCLIDEAN", exponent = 1.0, threshold = None, 
                 kNeighs = 1, rowStandard = True):
    """Creates a sparse spatial weights matrix (SWM) based on k-nearest
    neighbors.

    INPUTS: 
    inputFC (str): path to the input feature class
    swmFile (str): path to the SWM file.
    masterField (str): field in table that serves as the mapping.
    fixed (boolean): fixed (1) or inverse (0) distance? 
    concept: {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN 
    exponent {float, 1.0}: distance decay
    threshold {float, None}: distance threshold
    kNeighs (int): number of neighbors to return
    rowStandard {bool, True}: row standardize weights?
    """

    #### Create SSDataObject ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = inputFC,
                             useChordal = True)

    #### Validation of Master Field ####
    verifyMaster = ERROR.checkField(ssdo.allFields, masterField, types = [0,1])

    #### Read Data ####
    ssdo.obtainDataGA(masterField, minNumObs = 2)
    N = ssdo.numObs
    gaTable = ssdo.gaTable
    if fixed:
        wType = 1
    else:
        wType = 0

    #### Set Default Progressor for Neigborhood Structure ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84143))

    #### Set the Distance Threshold ####
    concept, gaConcept = WU.validateDistanceMethod(concept, ssdo.spatialRef)
    if threshold == None:
        threshold, avgDist = WU.createThresholdDist(ssdo, 
                                        concept = concept)

    #### Assures that the Threshold is Appropriate ####
    gaExtent = UTILS.get92Extent(ssdo.extent)
    threshold, maxSet = WU.checkDistanceThreshold(ssdo, threshold,
                                                  weightType = wType)

    #### If the Threshold is Set to the Max ####
    #### Set to Zero for Script Logic ####
    if maxSet:
        #### All Locations are Related ####
        threshold = SYS.maxint
        if N > 500:
            ARCPY.AddIDMessage("Warning", 717)

    #### Assure k-Nearest is Less Than Number of Features ####
    if kNeighs >= N and fixed:
        ARCPY.AddIDMessage("ERROR", 975)
        raise SystemExit()

    #### Create Distance/k-Nearest Neighbor Search Type ####
    gaSearch = GAPY.ga_nsearch(gaTable)
    gaSearch.init_nearest(threshold, kNeighs, gaConcept)
    neighWeights = ARC._ss.NeighborWeights(gaTable, gaSearch, 
                                           weight_type = wType,
                                           exponent = exponent,
                                           row_standard = False)

    #### Set Progressor for Weights Writing ####
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84127), 0, N, 1)

    #### Initialize Spatial Weights Matrix File ####
    swmWriter = WU.SWMWriter(swmFile, masterField, ssdo.spatialRefName, 
                             N, rowStandard, inputFC = inputFC,
                             wType = wType, distanceMethod = concept,
                             exponent = exponent, threshold = threshold)

    #### Unique Master ID Dictionary ####
    masterDict = {}

    #### Unique Master ID Dictionary ####
    masterSet = set([])

    for row in xrange(N):
        masterID = int(gaTable[row][2])
        if masterID in masterSet:
            ARCPY.AddIDMessage("Error", 644, masterField)
            ARCPY.AddIDMessage("Error", 643)
            raise SystemExit()
        else:
            masterSet.add(masterID)

        neighs, weights = neighWeights[row]
        neighs = [ gaTable[nh][2] for nh in neighs ]

        #### Add Spatial Weights Matrix Entry ####
        swmWriter.swm.writeEntry(masterID, neighs, weights) 

        #### Set Progress ####
        ARCPY.SetProgressorPosition()

    swmWriter.close()
    del gaTable

    #### Report Warning/Max Neighbors ####
    swmWriter.reportNeighInfo()

    #### Add Linear/Angular Unit (Distance Based Only) ####
    distanceOut = ssdo.distanceInfo.outputString
    distanceOut = [ARCPY.GetIDMessage(84344).format(distanceOut)]

    #### Report Spatial Weights Summary ####
    swmWriter.report(additionalInfo = distanceOut)

    #### Report SWM File is Large ####
    swmWriter.reportLargeSWM()

def spaceTime2SWM(inputFC, swmFile, masterField, concept = "EUCLIDEAN",
                  threshold = None, rowStandard = True,
                  timeField = None, timeType = None,
                  timeValue = None):
    """
    inputFC (str): path to the input feature class
    swmFile (str): path to the SWM file.
    masterField (str): field in table that serves as the mapping.
    concept: {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN 
    threshold {float, None}: distance threshold
    rowStandard {bool, True}: row standardize weights?
    timeField {str, None}: name of the date-time field
    timeType {str, None}: ESRI enumeration of date-time intervals
    timeValue {float, None}: value forward and backward in time
    """

    #### Assure Temporal Parameters are Set ####
    if not timeField:
        ARCPY.AddIDMessage("ERROR", 1320)
        raise SystemExit()
    if not timeType:
        ARCPY.AddIDMessage("ERROR", 1321)
        raise SystemExit()
    if not timeValue or timeValue <= 0:
        ARCPY.AddIDMessage("ERROR", 1322)
        raise SystemExit()

    #### Create SSDataObject ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = inputFC,
                             useChordal = True)
    cnt = UTILS.getCount(inputFC)
    ERROR.errorNumberOfObs(cnt, minNumObs = 2)
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84001), 0, cnt, 1)

    #### Validation of Master Field ####
    verifyMaster = ERROR.checkField(ssdo.allFields, masterField, types = [0,1])
    badIDs = []

    #### Create Temporal Hash ####
    timeInfo = {}
    xyCoords = NUM.empty((cnt, 2), float)

    #### Process Field Values ####
    fieldList = [masterField, "SHAPE@XY", timeField]
    try:
        rows = DA.SearchCursor(ssdo.catPath, fieldList, "", 
                               ssdo.spatialRefString)
    except:
        ARCPY.AddIDMessage("ERROR", 204)
        raise SystemExit()

    #### Add Data to GATable and Time Dictionary ####
    c = 0
    for row in rows:
        badRow = False

        #### Assure Masterfield is Valid ####
        masterID = row[0]
        if masterID == None or masterID == "":
            badRow = True

        #### Assure Date/Time is Valid ####
        timeStamp = row[-1]
        if timeStamp == None or timeStamp == "":
            badRow = True

        #### Assure Centroid is Valid ####
        badXY = row[1].count(None)
        if not badXY:
            x,y = row[1]
            xyCoords[c] = (x,y)
        else:
            badRow = True

        #### Process Data ####
        if not badRow:
            if timeInfo.has_key(masterID):
                #### Assure Uniqueness ####
                ARCPY.AddIDMessage("Error", 644, masterField)
                ARCPY.AddIDMessage("Error", 643)
                raise SystemExit()
            else:
                #### Fill Date/Time Dict ####
                startDT, endDT = TUTILS.calculateTimeWindow(timeStamp, 
                                                            timeValue, 
                                                            timeType)
                timeInfo[masterID] = (timeStamp, startDT, endDT)

        else:
            badIDs.append(masterID)

        #### Set Progress ####
        c += 1
        ARCPY.SetProgressorPosition()

    #### Clean Up ####
    del rows

    #### Get Set of Bad IDs ####
    numBadObs = len(badIDs)
    badIDs = list(set(badIDs))
    badIDs.sort()
    badIDs = [ str(i) for i in badIDs ]
    
    #### Process any bad records encountered ####
    if numBadObs:
        ERROR.reportBadRecords(cnt, numBadObs, badIDs, label = masterField)

    #### Load Neighbor Table ####
    gaTable, gaInfo = WU.gaTable(ssdo.inputFC, 
                                 fieldNames = [masterField, timeField],
                                 spatRef = ssdo.spatialRefString)
    numObs = len(gaTable)
    xyCoords = xyCoords[0:numObs]

    #### Set the Distance Threshold ####
    concept, gaConcept = WU.validateDistanceMethod(concept, ssdo.spatialRef)
    if threshold == None:
        #### Set Progressor for Search ####
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84144))

        #### Create k-Nearest Neighbor Search Type ####
        gaSearch = GAPY.ga_nsearch(gaTable)
        gaSearch.init_nearest(0.0, 1, gaConcept)
        neighDist = ARC._ss.NeighborDistances(gaTable, gaSearch)
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

    #### Create Missing SSDO Info ####
    extent = UTILS.resetExtent(xyCoords)

    #### Reset Coordinates for Chordal ####
    if ssdo.useChordal:
        sliceInfo = UTILS.SpheroidSlice(extent, ssdo.spatialRef)
        maxExtent = sliceInfo.maxExtent
    else:
        env = UTILS.Envelope(extent)
        maxExtent = env.maxExtent

    threshold = checkDistanceThresholdSWM(ssdo, threshold, maxExtent)
    
    #### Set Default Progressor for Neigborhood Structure ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84143))

    #### Create Distance Neighbor Search Type ####
    gaSearch = GAPY.ga_nsearch(gaTable)
    gaSearch.init_nearest(threshold, 0, gaConcept)
    neighSearch = ARC._ss.NeighborSearch(gaTable, gaSearch)

    #### Set Progressor for Weights Writing ####
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84127), 0, numObs, 1)

    #### Initialize Spatial Weights Matrix File ####
    swmWriter = WU.SWMWriter(swmFile, masterField, ssdo.spatialRefName, 
                             numObs, rowStandard, inputFC = inputFC,
                             wType = 9, distanceMethod = concept,
                             threshold = threshold, timeField = timeField,
                             timeType = timeType, timeValue = timeValue)

    for row in xrange(numObs):
        masterID = gaTable[row][2]

        #### Get Date/Time Info ####
        dt0, startDT0, endDT0 = timeInfo[masterID]

        nhs = neighSearch[row]
        neighs = []
        weights = []
        for nh in nhs:
            #### Search Through Spatial Neighbors ####
            neighID = gaTable[nh][2]

            #### Get Date/Time Info ####
            dt1, startDT1, endDT1 = timeInfo[neighID]

            #### Filter Based on Date/Time ####
            insideTimeWindow = TUTILS.isTimeNeighbor(startDT0, endDT0, dt1)
            if insideTimeWindow:
                neighs.append(neighID)
                weights.append(1.0)

        #### Add Spatial Weights Matrix Entry ####
        swmWriter.swm.writeEntry(masterID, neighs, weights) 

        #### Set Progress ####
        ARCPY.SetProgressorPosition()

    swmWriter.close()
    del gaTable

    #### Report Warning/Max Neighbors ####
    swmWriter.reportNeighInfo()

    #### Report Spatial Weights Summary ####
    swmWriter.report()

    #### Report SWM File is Large ####
    swmWriter.reportLargeSWM()

def table2SWM(inputFC, masterField, swmFile, tableFile, rowStandard = True):
    """Converts a weigths matrix in table format into SWM format.

    INPUTS:
    inputFC (str): path to the input feature class
    masterField (str): field in table that serves as the mapping.
    swmFile (str): path to the SWM file.
    tableFile (str) path to the database table
    rowStandard {bool, True}: row standardize weights?
    """

    #### Set Default Progressor for Neigborhood Structure ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84123))

    #### Create SSDataObject ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = inputFC)

    #### Obtain Unique IDs from Input Feature Class ####
    ssdo.obtainData(masterField, minNumObs = 2)
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84123))
    master2Order = ssdo.master2Order
    allMaster = master2Order.keys()
    n = ssdo.numObs

    #### Create Search Cursor for Input Weights Table ####
    neighFieldName = "NID" 
    weightFieldName = "WEIGHT"
    fieldList = [masterField, neighFieldName, weightFieldName]
    try:
        rows = DA.SearchCursor(tableFile, fieldList)
    except:
        ARCPY.AddIDMessage("Error", 722)
        raise SystemExit()

    #### Initialize Spatial Weights Matrix File ####
    swmWriter = WU.SWMWriter(swmFile, masterField, ssdo.spatialRefName, 
                             n, rowStandard, inputFC = inputFC,
                             wType = 8, inputTable = tableFile)

    #### Set Progressor for SWM Reading/Writing ####
    c = 0
    cnt = UTILS.getCount(tableFile)
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84123), 0, cnt, 1)
    lastID = "NULL"
    neighs = []
    weights = []

    #### Process Spatial Weights ####
    for row in rows:
        masterID = row[0]

        if master2Order.has_key(masterID):
            neighID = row[1]
            weight = row[2]

            if masterID == lastID:
                #### Append to Current Record ####
                try:
                    testNeigh = master2Order[neighID]
                    neighs.append(neighID)
                    weights.append(weight)
                except:
                    #### NID Does Not Exist / Not In Selection ####
                    pass

                #### Set Progress ####
                ARCPY.SetProgressorPosition()

            else:
                #### Create New Record if not NULL ####
                if lastID != "NULL":
                    allMaster.remove(lastID)
                    swmWriter.swm.writeEntry(lastID, neighs, weights) 

                    #### Reset and Initialize Containers ####
                    neighs = [neighID]
                    weights = [weight]

                else:
                    #### Create First Record ####
                    try:
                        testNeigh = master2Order[neighID]
                        neighs.append(neighID)
                        weights.append(weight)
                    except:
                        #### NID Does Not Exist / Not In Selection ####
                        pass

                lastID = masterID

                #### Set Progress ####
                ARCPY.SetProgressorPosition()
        else:
            #### Unique Id Does Not Exist / Not In Selection ####
            ARCPY.SetProgressorPosition()

    #### Write Last Record ####
    swmWriter.swm.writeEntry(lastID, neighs, weights) 
    try:
        allMaster.remove(lastID)
    except:
        pass

    #### Set Progress ####
    ARCPY.SetProgressorPosition()

    #### Write No Neighbor Features ####
    for masterID in allMaster:
        swmWriter.swm.writeEntry(masterID, [], []) 

    #### Report Warning/Max Neighbors ####
    swmWriter.reportNeighInfo()

    #### Report Spatial Weights Summary ####
    swmWriter.report()

    #### Report SWM File is Large ####
    swmWriter.reportLargeSWM()

    #### Clean Up ####
    swmWriter.close()
    del rows

if __name__ == '__main__':
    setupWeights()
