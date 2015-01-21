"""
Tool Name:     Generate Spatial Weights From Network
Source Name:   Network2SWM.py
Version:       ArcGIS 10.0
Author:        Environmental Systems Research Institute Inc.
Description:   Creates spatial weights in SWM format from a combination
               of network data and feature classes. 
"""


################### Imports ########################

import os as OS
import locale as LOCALE
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.na as NET
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO 
import WeightsUtilities as WU 

################### GUI Interface ######################

def setupNetwork2SWM():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    #### Process Dialogue Inputs ####
    inputFC = ARCPY.GetParameterAsText(0)      
    masterField = ARCPY.GetParameterAsText(1)
    swmFile = ARCPY.GetParameterAsText(2)
    inputNetwork = ARCPY.GetParameterAsText(3)
    impedance = ARCPY.GetParameterAsText(4)

    cutoff = UTILS.getNumericParameter(5)
    if not cutoff:
        cutoff = "#"

    numberOfNeighs = UTILS.getNumericParameter(6)
    if not numberOfNeighs:
        numberOfNeighs = "#"

    inputBarrier = UTILS.getTextParameter(7)
    if not inputBarrier:
        inputBarrier = "#"

    uturnPolicy = ARCPY.GetParameterAsText(8)

    restrictions = UTILS.getTextParameter(9)
    if not restrictions:
        restrictions = "#"

    hierarchyBool = ARCPY.GetParameter(10)
    if hierarchyBool:
        hierarchy = 'USE_HIERARCHY'
    else:
        hierarchy = 'NO_HIERARCHY'

    searchTolerance = UTILS.getTextParameter(11)
    if not searchTolerance:
        searchTolerance = "#"

    #### Assign to appropriate spatial weights method ####
    spaceConcept = ARCPY.GetParameterAsText(12)
    spaceConcept = spaceConcept + "_DISTANCE"
    try:
        wType = WU.weightDispatch[spaceConcept]
    except:
        ARCPY.AddIDMessage("Error", 723)
        raise SystemExit()

    #### Must Be Inverse Distance [0] or Fixed Distance [1] ####
    if wType not in [0,1]:
        ARCPY.AddIDMessage("Error", 723)
        raise SystemExit()
    else:
        fixed = wType

    exponent = UTILS.getNumericParameter(13)
    rowStandard = ARCPY.GetParameter(14)

    network2SWM(inputFC, masterField, swmFile, inputNetwork, impedance, 
                cutoff = cutoff, numberOfNeighs = numberOfNeighs,
                inputBarrier = inputBarrier, uturnPolicy = uturnPolicy, 
                restrictions = restrictions, hierarchy = hierarchy, 
                searchTolerance = searchTolerance, fixed = fixed, 
                exponent = exponent, rowStandard = rowStandard)

def network2SWM(inputFC, masterField, swmFile, inputNetwork, 
                impedance, cutoff = "#", numberOfNeighs = "#", 
                inputBarrier = "#", uturnPolicy = "ALLOW_UTURNS", 
                restrictions = "#", hierarchy = 'NO_HIERARCHY',
                searchTolerance = "#", fixed = 0,
                exponent = 1.0, rowStandard = True):

    """Creates spatial weights in SWM format from a combination
    of network data and feature classes.

    INPUTS: 
    inputFC (str): path to the input feature class
    masterField (str): field in table that serves as the mapping
    swmFile (str): path to the SWM file
    inputNetwork (str): path to the network dataset (*.nd)
    impedance (str): attribute from network dataset (1)
    cutoff {float, "#"}: impedance threshold
    numberOfNeighs {int, "#"}: number of neighbors to return
    inputBarrier {str, "#"}: path to the input barrier feature class
    uturnPolicy {str, ALLOW_UTURNS}: uturn policy (2)
    restrictions {str, "#"}: attribute from network dataset (3)
    hierarchy {str, NO_HIERARCHY}: NO_HIERARCHY or USE_HIERARCHY
    searchTolerance {linear measure, "#"}: snap tolerance for network (4)
    fixed {int, 0}: Invert impedance as weight or return a weight = 1? 
    exponent {float, 1.0}: distance decay
    rowStandard {bool, True}: row standardize weights?

    NOTES:
    (1) E.g. MINUTES and METERS
    (2) E.g. ALLOW_UTURNS or NO_UTURNS
    (3) E.g. ONEWAY
    (4) E.g. 5000 METERS
    """
    
    #### Check out Network Analyst ####
    try:
        ARCPY.CheckOutExtension("Network")
    except:
        ARCPY.AddIDMessage("ERROR", 849)
        raise SystemExit()

    #### OD Matrix and Layers ####
    ODCostMatrix = "ODMatrix"
    BarriersLayerNames = {"POINT": 'Barriers',
                          "POLYLINE" : 'PolylineBarriers',
                          "LINE" : 'PolylineBarriers',
                          "POLYGON" : 'PolygonBarriers'}
    lines = ODCostMatrix + "\\Lines"
    destFCLayer = "NetSWM_Dest"

    ##### Delete Layers If They Exist ####
    cleanupNetLayer(ODCostMatrix)
    cleanupNetLayer(destFCLayer)
    cleanupNetLayer(lines)

    #### Get Master Field From inputFC ####
    ssdo = SSDO.SSDataObject(inputFC,
                             useChordal = False)
    ssdo.obtainDataGA(masterField, minNumObs = 2)
    master2Order = ssdo.master2Order
    masterFieldObj = ssdo.allFields[masterField.upper()]
    allMaster = master2Order.keys()
    numObs = ssdo.numObs
    numPossNeighs = numObs - 1
    
    #### Get Spatial Ref From Net Data Set ####
    netDesc = ARCPY.Describe(inputNetwork)
    netSpatialRef = netDesc.SpatialReference
    netSpatName = netSpatialRef.Name

    #### Set Maximum Neighbor Argument ####
    if numberOfNeighs == "#":
        numberOfNeighs = min( [numPossNeighs, 30] )
        ARCPY.AddIDMessage("WARNING", 1012, numberOfNeighs)

    if numberOfNeighs >= numObs:
        numberOfNeighs = numPossNeighs
        ARCPY.AddIDMessage("WARNING", 1013, numberOfNeighs)

    if numberOfNeighs == 0:
        numberOfNeighs = numPossNeighs

    #### All Features are Related.  Force Inverse Impedance ####
    if (numObs - numberOfNeighs) <= 1:
        if fixed:
            ARCPY.AddIDMessage("WARNING", 974)
            fixed = 0

    #### Add Self Neighbor For OD Solve ####
    numberOfNeighsOD = numberOfNeighs + 1

    #### Make OD Cost Matrix Layer ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84132))
    odCostMatrixLayer = NET.MakeODCostMatrixLayer(inputNetwork, ODCostMatrix, impedance, cutoff,
                              numberOfNeighsOD, "#", uturnPolicy,
                              restrictions, hierarchy, "#", "NO_LINES").getOutput(0)
    
    #### OD Matrix and Layers ####
    naClassNames = NET.GetNAClassNames(odCostMatrixLayer)
    destinationLayer = ODCostMatrix + OS.sep + naClassNames["Destinations"]
    originLayer = ODCostMatrix + OS.sep + naClassNames["Origins"]
    lines = ODCostMatrix + OS.sep + naClassNames["ODLines"]

    #### Add Barriers ####
    if inputBarrier != "" and inputBarrier != "#":
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84147))
        barDesc = ARCPY.Describe(inputBarrier)
        barShapeType = barDesc.ShapeType.upper()
        if barShapeType in BarriersLayerNames:
            barString = naClassNames[BarriersLayerNames[barShapeType]]
            NET.AddLocations(ODCostMatrix, barString, inputBarrier, "",
                             searchTolerance)

    #### Add Master Field to OD for Selection ####
    masterType = UTILS.convertType[masterFieldObj.type]
    NET.AddFieldToAnalysisLayer(ODCostMatrix, naClassNames["Destinations"], masterField,
                                masterType)

    #### Add Destinations ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84133)) 
    masterToken = "Name " + masterField + " #;"
    masterToken += masterField + " " + masterField + " #"
    NET.AddLocations(ODCostMatrix, naClassNames["Destinations"], inputFC, masterToken,
                     searchTolerance, exclude_restricted_elements = "EXCLUDE")

    #### Initialize Spatial Weights Matrix File ####
    hierarchyBool = hierarchy == 'USE_HIERARCHY'
    addConcept = WU.wTypeDispatch[fixed].split("_")[0]
    forceFixed = (fixed == True)
    swmWriter = WU.SWMWriter(swmFile, masterField, netSpatName, 
                             numObs, rowStandard,
                             inputFC = inputFC, wType = 10,
                             inputNet = inputNetwork, 
                             impedanceField = impedance,
                             barrierFC = inputBarrier,
                             uturnPolicy = uturnPolicy,
                             restrictions = restrictions,
                             useHierarchy = hierarchyBool,
                             searchTolerance = searchTolerance,
                             addConcept = addConcept,
                             exponent = exponent,
                             forceFixed = forceFixed)

    #### Create FieldList for Subset Searching ####
    totalImpedance = "Total_" + impedance
    fieldList = ";".join( ["NAME", totalImpedance] )

    #### Get Chunks if Necessary ####
    numOrigins = int(10000000. / numObs)
    allMaster.sort()
    chunkedIDs = UTILS.chunk(allMaster, numOrigins)
    sqlStrings = UTILS.sqlChunkStrings(inputFC, masterField, chunkedIDs)
    numChunks = len(sqlStrings)

    #### Create Field Map for Origins ####
    masterToken = "Name " + masterField + " #"
    orgFieldMap = [masterToken, 'CurbApproach CurbApproach 0', 
                    'SourceID SourceID #', 'SourceOID SourceOID #',
                    'PosAlong PosAlong #', 'SideOfEdge SideOfEdge #']   
    orgFieldMap = ";".join(orgFieldMap)

    #### Keep Track of Features That Snap to Network ####
    snappedFeatures = set([])

    for chunkNum in xrange(numChunks):
        progMsg = ARCPY.GetIDMessage(84145).format(chunkNum + 1, numChunks)
        ARCPY.SetProgressor("default", progMsg)
        
        #### Make Origins from Chunk of Destinations ####
        sqlValue = sqlStrings[chunkNum]
        DM.MakeFeatureLayer(destinationLayer, destFCLayer, sqlValue)
        NET.AddLocations(ODCostMatrix, naClassNames["Origins"], destFCLayer, orgFieldMap,
                         "#", "#", "#", "#", "CLEAR")

        #### Solve OD Matrix and Select Data ####
        NET.Solve(ODCostMatrix, "SKIP")

        #### Count the Number of NonZero Spatial Linkages #### 
        numLinks = UTILS.getCount(lines)

        #### Create Search Cursor for OD Line Info ####
        rows = ARCPY.SearchCursor(lines, "", None, fieldList)
        row = rows.next()

        #### Set Tool Progressor and Process Information ####
        ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84127), 0, numLinks, 1)

        #### Process First Record ####
        ODInfo = row.getValue("NAME")
        lastID, neighID = [ int(i) for i in ODInfo.split(" - ") ]
        impValue = row.getValue(totalImpedance)
        weight = WU.distance2Weight(impValue, wType = fixed, 
                                    exponent = exponent)
        neighs = []
        weights = []
        if lastID != neighID:
            neighs.append(neighID)
            weights.append(weight)

        #### Process Remaining Records ####
        progMsg = ARCPY.GetIDMessage(84146).format(chunkNum + 1, numChunks)
        ARCPY.SetProgressor("step", progMsg, 0, numLinks, 1)
        while row:
            #### Get Origin and Destination Unique IDs ####
            ODInfo = row.getValue("NAME")
            masterID, neighID = [ int(i) for i in ODInfo.split(" - ") ]

            #### Obtain Impedance and Create Weight ####
            impValue = row.getValue(totalImpedance)
            weight = WU.distance2Weight(impValue, wType = fixed, 
                                        exponent = exponent)

            #### Check Whether it is the Same ID ####
            if masterID == lastID:
                if masterID != neighID:
                    neighs.append(neighID)
                    weights.append(weight)

            else:
                #### New ID, Add Last ID Result to SWM File ####
                swmWriter.swm.writeEntry(lastID, neighs, weights) 
                snappedFeatures.add(lastID)

                #### Reset and Initialize Containers ####
                neighs = []
                weights = []
                if masterID != neighID: 
                    neighs.append(neighID)
                    weights.append(weight)
                lastID = masterID

            ARCPY.SetProgressorPosition()
            row = rows.next()

        #### Write Last ID Result ####
        swmWriter.swm.writeEntry(lastID, neighs, weights) 
        snappedFeatures.add(lastID)

        #### Clean Up ####
        del rows

    ##### Delete Layers If They Exist ####
    cleanupNetLayer(ODCostMatrix)
    cleanupNetLayer(destFCLayer)
    cleanupNetLayer(lines)

    #### Add Empty SWM Entries for Features Not Snapped to Network ####
    notSnapped = snappedFeatures.symmetric_difference(allMaster)
    for masterID in notSnapped:
        swmWriter.swm.writeEntry(masterID, [], [])

    #### Report Warning/Max Neighbors ####
    swmWriter.reportNeighInfo()

    #### Clean Up ####
    swmWriter.close()

    #### Report Spatial Weights Summary ####
    swmWriter.report()

    #### Report SWM File is Large ####
    swmWriter.reportLargeSWM()

def cleanupNetLayer(netLayer):
    """Tries to delete Network OD Cost Layers.
    
    INPUTS:
    netLayer (str): network OD cost layer
    """
    try:
        DM.Delete(netLayer)
    except:
        pass

if __name__ == '__main__':
    setupNetwork2SWM()
