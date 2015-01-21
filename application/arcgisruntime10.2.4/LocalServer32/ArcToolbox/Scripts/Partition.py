"""
Tool Name:  Group Similar Features 
Source Name: Partition.py
Version: ArcGIS 10.1
Author: ESRI

This tool performs constrained aggregative clustering based on traditional
k-means and spatial k-means based on a minimum spanning tree algorithm:

Source:
R. M. Assuncao, M. C. Neves, G. Camara and C. d. C. Frietas, 2006
Efficient regionalisation techniques for socio-economic geographical units
using minimum spanning trees.
"International Journal of Geographical Information Science"
"""

################### Imports ########################
import sys as SYS
import os as OS
import locale as LOCALE
import numpy as NUM
import numpy.random as RAND
import arcgisscripting as ARC
import arcpy as ARCPY
import arcpy.analysis as ANA
import arcpy.management as DM
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO
import Stats as STATS
import WeightsUtilities as WU
import collections as COLL
import operator as OP
import gapy as GAPY
import SSReport as REPORT
import pylab as PYLAB
import matplotlib.pyplot as PLT
import copy as COPY

################ Output Field Names #################
gaFieldNames = ["SS_GROUP", "SS_SEED"]

#### Matplotlib Properties ####
colors = ["#78AAFF", "#FF6455", "#7DDC55", "#FFB400", "#C864E1", 
          "#BEA064", "#FABEC8", "#AFAFAF", "#005AE6", "#E60000", 
          "#37A000", "#960096", "#B4FF00", "#822800", "#3C6E82", 
          "#FF00C3", "#00E6AA", "#FFE600", "#002378", "#D78787", 
          "#282828", "#73E1E1", "#006400", "#E1C3FF", "#966432", 
          "#FFC88C", "#D2FFBE", "#CDE1FF", "#FFFF87", "#F0F0F0"]

numRows = 20
nearEnd = numRows - 3
rowFormat = ["%s"] + (["%0.4f"] * 5)

#### Global Variables ####
maxNumGroups = 15
maxNumVars = 15
aSpatialOptimizeIters = 10
aSpatialIters = 100

decimalSep = UTILS.returnDecimalChar()
if decimalSep == ".":
    numSep = ","
else:
    numSep = ";"

#### Matplotlib Functions ####
def numberOfGroupPages(numGroups, numVars):
    parBoxPlot = 1
    paramPage = 1
    groupLines = 5 + (numGroups * (numVars + 2))
    groupPages = (groupLines / 20) + 1
    varLines = numVars * (numGroups + 3)
    varPages = (varLines / 20) + 1
    numPages = parBoxPlot + paramPage + groupPages + varPages
    return numPages

def createRow(grid, outInfo, values, color = "black", addGroup = True):
    #### Table Info ####
    row = grid.rowCount
    for ind, info in enumerate(outInfo):
        strInfo = LOCALE.format(rowFormat[ind], info)
        textGrid = PLT.subplot2grid(grid.gridInfo, (row, ind))
        PLT.text(0.0, 0.5, strInfo, color = color, 
                 fontproperties=REPORT.ssFont, **REPORT.bAlignment)
        REPORT.clearGrid(textGrid)

    #### Box Plot ####
    boxGrid = PLT.subplot2grid(grid.gridInfo, (row, 6), colspan = 2)
    bp = PLT.boxplot(values, vert = 0, widths = .7)
    PLT.setp(bp['boxes'], color='black')
    PLT.setp(bp['whiskers'], color='black', ls = 'solid')
    PLT.setp(bp['medians'], color='black') 
    PLT.setp(bp['fliers'], color='black')  

    #### Add Mean Value ####
    PLT.plot(outInfo[1], 1., color = color, marker = "o")

    #### Add Group Specific Info ####
    if addGroup:
        minVal = outInfo[3]
        maxVal = outInfo[4]
        PLT.plot((minVal, minVal), (.75, 1.25), color = color, linestyle = "-")
        PLT.plot((maxVal, maxVal), (.75, 1.25), color = color, linestyle = "-")
    REPORT.clearGrid(boxGrid)
    grid.stepRow()

def newGroup(grid, label, color, colspan = 5):
    grid.writeCell((grid.rowCount, 0), label, colspan = colspan, 
                    color = color, fontObj = REPORT.ssBoldFont, justify = "left")
    grid.createLineRow(grid.rowCount, startCol = colspan)
    grid.stepRow()

def newVarGroup(grid, R2String):
    grid.writeCell((grid.rowCount, 0), R2String, colspan = 2,
                    fontObj = REPORT.ssBoldFont, justify = "left")
    grid.createLineRow(grid.rowCount, startCol = 2, endCol = 8, 
                       color = "black")
    grid.stepRow()

################## Helper Functions ##################

def getCentroid(x, partIDs):
    return x[partIDs].mean(0)

def dist2Centroid(x, centroid, partIDs = None):
    if partIDs:
        x = x[partIDs]
    dist = ((x - centroid)**2.0).sum(1)
    return dist

def varDist2Centroid(x, centroid, partIDs = None):
    if partIDs:
        x = x[partIDs]
    dist = ((x - centroid)**2.0).sum(0)
    return dist

################### GUI Interface ###################
def setupPartition():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)                    
    masterField = ARCPY.GetParameterAsText(1).upper()            
    outputFC = ARCPY.GetParameterAsText(2)

    #### User Defined Number of Groups ####
    kPartitions = UTILS.getNumericParameter(3)

    analysisFields = ARCPY.GetParameterAsText(4).upper()   
    analysisFields = analysisFields.split(";")

    #### Conceptualization ####
    spaceConcept = ARCPY.GetParameterAsText(5).upper()

    #### EUCLIDEAN or MANHATTAN ####
    distanceConcept = ARCPY.GetParameterAsText(6).upper().replace(" ", "_")
    if distanceConcept == "#" or distanceConcept == "": 
        distanceConcept = "EUCLIDEAN"

    #### Number of Neighbors ####
    numNeighs = UTILS.getNumericParameter(7)

    #### Quick Validation of k-nearest ####
    if spaceConcept == "K_NEAREST_NEIGHBORS":
        if numNeighs <= 0:
            ARCPY.AddIDMessage("ERROR", 976)
            raise SystemExit()

    #### Spatial Weights Matrix File ####
    weightsFile = UTILS.getTextParameter(8)    
    useWeightsFile = spaceConcept == "GET_SPATIAL_WEIGHTS_FROM_FILE"
    if not weightsFile and useWeightsFile:
        ARCPY.AddIDMessage("ERROR", 930)
        raise SystemExit()
    if weightsFile and not useWeightsFile:
        ARCPY.AddIDMessage("WARNING", 925)
        weightsFile = None

    #### Initialization Approach ####
    initMethod = ARCPY.GetParameterAsText(9)
    if initMethod == "#" or initMethod == "": 
        initMethod = "FIND_SEED_LOCATIONS"

    #### Initial Seed/Solution Field ####
    fieldList = [ i for i in analysisFields ]
    initField = UTILS.getTextParameter(10, fieldName = True) 
    if initField != None:
        fieldList.append(initField)

    if spaceConcept == "NO_SPATIAL_CONSTRAINT":
        if initMethod == "GET_SEEDS_FROM_FIELD" and initField == None:
            ARCPY.AddIDMessage("ERROR", 1327)
            raise SystemExit()

    #### Report File ####
    reportFile = ARCPY.GetParameterAsText(11)    
    if reportFile == "#" or reportFile == "": 
        reportFile = None
    else:
        #### Validate Number of Vars/Groups for Report (Max 15) ####
        if kPartitions > maxNumGroups or len(analysisFields) > maxNumVars:
            reportFile = None
            ARCPY.AddIDMessage("WARNING", 1328)

    #### Permutations ####
    optimalBool = ARCPY.GetParameter(12)

    #### Warn About Chordal Bool ####
    if spaceConcept in ["NO_SPATIAL_CONSTRAINT",
                        "GET_SPATIAL_WEIGHTS_FROM_FILE"]:
        useChordal = False
    else:
        useChordal = True

    #### Create SSDataObject ####
    ssdo = SSDO.SSDataObject(inputFC, templateFC = outputFC, 
                             useChordal = useChordal)

    #### Populate SSDO with Data ####
    if spaceConcept in ["DELAUNAY_TRIANGULATION", "K_NEAREST_NEIGHBORS"]:
        ssdo.obtainDataGA(masterField, fieldList, minNumObs = 3, 
                          warnNumObs = 30)
    else:
        ssdo.obtainData(masterField, fieldList, minNumObs = 3, 
                        warnNumObs = 30)

    #### Execute ####
    part = Partition(ssdo, analysisFields, spaceConcept = spaceConcept,
                     distConcept = distanceConcept, numNeighs = numNeighs,
                     weightsFile = weightsFile, initMethod = initMethod,
                     kPartitions = kPartitions, initField = initField,
                     optimizeGroups = optimalBool)

    #### Report ####
    pdfOutput = part.report(fileName = reportFile, optimal = optimalBool)

    #### Create OutputFC ####
    part.createOutput(outputFC)

    #### Optimal Number of Partitions ####
    if optimalBool:
        #### Get FStat Info ####
        maxInd, maxGroup, maxFStat = part.fStatInfo

        #### Plot Results ####
        if reportFile:
            if part.aspatial:
                plotFStats(pdfOutput, part.groupList, part.fStatRes,
                           maxInd = maxInd)
            else:
                plotFStatsSpatial(pdfOutput, part.groupList, part.fStatRes,
                                  maxInd = maxInd)

        #### Set Derived Output ####
        ARCPY.SetParameterAsText(13, part.fStat)
        ARCPY.SetParameterAsText(14, maxGroup)
        ARCPY.SetParameterAsText(15, maxFStat)

    else:
        #### Set All Derived F-Stats to Main Partition Values ####
        ARCPY.SetParameterAsText(13, part.fStat)
        ARCPY.SetParameterAsText(14, "")
        ARCPY.SetParameterAsText(15, "")

class Partition(object):
    """Traditional k-means classification algorithm:
    
    INPUTS: 
    ssdo (obj): instance of SSDataObject
    weightsFile {str, None}: path to a spatial weights matrix file
    concept: {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN 
    numNeighs {long, None}: if space concept is K_NEAREST_NEIGHBORS
    """

    def __init__(self, ssdo, varNames,
                 spaceConcept = "NO_SPATIAL_CONSTRAINT", 
                 distConcept = "EUCLIDEAN",
                 numNeighs = None, weightsFile = None,
                 initMethod = "FIND_SEED_LOCATIONS",
                 kPartitions = 5, initField = None,
                 optimizeGroups = False):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())

        #### Assure Number of Groups/Features is Possible ####
        if kPartitions >= ssdo.numObs:
            ARCPY.AddIDMessage("ERROR", 1387)
            raise SystemExit()

        #### Set Group Limit ####
        if optimizeGroups:
            self.kLimit = max(maxNumGroups, self.kPartitions)
            #### Assure kLimit Does Not Exceed Num Features ####
            if self.kLimit >= ssdo.numObs:
                self.kLimit = ssdo.numObs - 1
        else:
            self.kLimit = self.kPartitions

        #### Assess Whether SWM File Being Used ####
        self.swmFileBool = False 
        self.weightsBool = False
        if weightsFile:
            weightSuffix = weightsFile.split(".")[-1].lower()
            self.swmFileBool = (weightSuffix == "swm")
            self.weightsBool = True

        #### Initialize Data ####
        self.organizeData()

        #### A-Spatial Versus Spatial ####
        if self.spaceConcept == "NO_SPATIAL_CONSTRAINT":

            #### Set Aspatial Bool ####
            self.aspatial = True
            self.numFeatures = self.ssdo.numObs

            #### Find Feasible Solution(s) ####
            if self.optimizeGroups:
                self.optimize()
            else:
                #### Set Seeds ####
                self.setSeeds()
                self.aspatialSolve()
            
        else:

            #### Set Aspatial Bool ####
            self.aspatial = False

            #### Find Feasible Solution(s) ####
            if self.optimizeGroups:
                self.optimize()
            else:
                self.minSpanTree()
                self.spatialSolve()

    def optimize(self):
        ARCPY.AddMessage(ARCPY.GetIDMessage(84325))
        baseNumParts = self.kPartitions

        if self.aspatial:
            #### Aspatial Optimization ####
            ARCPY.AddIDMessage("WARNING", 1326)
            self.groupList = range(2, self.kLimit + 1)
            ng = len(self.groupList)
            self.fStatRes = NUM.zeros((ng, aSpatialOptimizeIters), float)
            self.medianList = []

            #### Loop Through Num Groups ####
            for row, numPart in enumerate(self.groupList):
                finalize = numPart == baseNumParts
                self.kPartitions = numPart

                #### Max FStat For User Selected Group ####
                highestFStat = -999999.0
                fStatSolution = None

                #### Loop Through Number of Iterations ####
                for iter in xrange(aSpatialOptimizeIters):
                    silent = iter != 0
                    self.setSeeds(silent = silent)
                    self.aspatialSolve(finalize = False)
                    fStat = self.getFStatFromSolution(self.iterGroups)
                    self.fStatRes[row, iter] = fStat
                    if finalize:
                        #### Assess Best Solution For User Selected Group ####
                        if fStat > highestFStat:
                            highestFStat = fStat
                            fStatSolution = self.iterGroups

                #### Set Solution and Stats ####
                if finalize:
                    self.finalizeSolution(fStatSolution)
                
                #### Assess Group Simulation Results ####
                fVals = self.fStatRes[row]
                meanF = fVals.mean()
                minF = fVals.min()
                maxF = fVals.max()
                medF = STATS.median(fVals)
                self.medianList.append(medF)
                fRes = (numPart, LOCALE.format("%0.4f", meanF), numSep,
                        LOCALE.format("%0.4f", minF), 
                        LOCALE.format("%0.4f", maxF), 
                        LOCALE.format("%0.4f", medF))
                msg = ARCPY.GetIDMessage(84407).format(*fRes)
                ARCPY.AddMessage(msg)

            if baseNumParts > maxNumGroups:
                #### Final Run If Desired Num Groups > than Max Parts ####
                self.kPartitions = baseNumParts
                self.setSeeds()
                self.aspatialSolve()

            #### Report Highest Pseudo-F (Aspatial) ####
            self.fStatInfo = summarizeFStats(self.fStatRes, self.groupList)

        else:
            #### Spatial Optimization ####
            self.minSpanTree()
            self.spatialSolve(optimize = True)

            #### Report Highest Pseudo-F (Spatial) ####
            self.fStatInfo = summarizeFStatsSpatial(self.fStatRes, 
                                                    self.groupList)

    def organizeData(self):
        """Organizes the data for the partitioning algorithms.
        """

        #### Shorthand Attributes ####
        ssdo = self.ssdo

        #### Remove Any Variables With No Variation ####
        self.badVarNames = []
        for varName in self.varNames:
            vVar = ssdo.fields[varName].data.var()
            if NUM.isnan(vVar) or vVar <= 0.0:
                self.badVarNames.append(varName)

        numBadVars = len(self.badVarNames)
        numInitVars = len(self.varNames)
        if numBadVars == numInitVars:
            #### All Fields Have No Variance ####
            ARCPY.AddIDMessage("ERROR", 1203)
            raise SystemExit()

        if numBadVars:
            badS = ", ".join(self.badVarNames)
            nBad = str(numBadVars)
            nInit = str(numInitVars)
            ARCPY.AddIDMessage("WARNING", 1204, nBad, nInit)
            ARCPY.AddIDMessage("WARNING", 1209, badS)
            for varName in self.badVarNames:
                self.varNames.remove(varName)

        #### Create Design Matrix ####
        self.n = self.ssdo.numObs
        self.k = len(self.varNames)
        self.x = NUM.zeros((self.n, self.k), dtype = float)
        for column, varName in enumerate(self.varNames):
            self.x[:,column] = ssdo.fields[varName].data

        self.z = STATS.zTransform(self.x)
        self.zMean = self.z.mean(0)
        ss = dist2Centroid(self.z, self.zMean)
        self.SST = ss.sum()
        self.varSST = varDist2Centroid(self.z, self.zMean)
        self.varSSE = NUM.zeros((self.kPartitions, self.k))

        #### Calculate Global AIC ####
        self.globalAIC = 2. + ((self.ssdo.numObs * 1.) * \
                         NUM.log(self.SST) / self.ssdo.numObs) 

    def setSeeds(self, silent = False):
        if self.initMethod == "GET_SEEDS_FROM_FIELD":
            #### Get User Defined Seed Field ####
            seedData = self.ssdo.fields[self.initField].data
            seedIndices = NUM.array(NUM.where(seedData == 1)[0], NUM.int32)
            lenSeeds = len(seedIndices)
            if lenSeeds == 0:
                #### No Valid Seeds ####
                ARCPY.AddIDMessage("ERROR", 1205, self.initField)
                raise SystemExit()

            if lenSeeds > self.kPartitions:
                #### More Seeds Than Number of Groups ####
                if not silent:
                    ARCPY.AddIDMessage("WARNING", 1206, self.kPartitions, lenSeeds)
                permSeeds = RAND.permutation(seedIndices)
                seedIndices = NUM.array(permSeeds[0:self.kPartitions])

            if lenSeeds < self.kPartitions:
                #### Less Seeds Than Number of Groups ####
                newSeedNum = self.kPartitions - lenSeeds
                if not silent:
                    ARCPY.AddIDMessage("WARNING", 1207, newSeedNum)
                seedIndices = ARC._ss.kmeans_plus_plus(self.z, 
                                                  self.kPartitions,
                                                  seedIndices)

        elif self.initMethod == "FIND_SEED_LOCATIONS":
            seedIndices = ARC._ss.kmeans_plus_plus(self.z, self.kPartitions)
        else:
            randInd = RAND.permutation(self.ssdo.numObs)
            seedIndices = randInd[0:self.kPartitions]

        self.partIDs = range(self.kPartitions)
        self.seeds = NUM.zeros(self.n, dtype = NUM.int32)
        self.seeds[seedIndices] = 1
        self.seedIndices = NUM.array(seedIndices, dtype = NUM.int32)
    
    def aspatialSolve(self, finalize = True):
        feasible = True
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84259))
        closest, iters = ARC._ss.kmeans_solve(self.z, self.seedIndices, 
                                       max_iters = aSpatialIters)
        feasible = iters < aSpatialIters

        if not feasible:
            #### Failed to Solve, Return Unique ID of Seed Features ####
            s = [str(self.ssdo.order2Master[i]) for i in self.seedIndices]
            s = ", ".join(s)
            ARCPY.AddIDMessage("WARNING", 1208, aSpatialIters)
            ARCPY.AddIDMessage("WARNING", 1424, self.ssdo.masterField, s)

        #### Set Attributes ####
        self.iters = iters
        self.iterGroups = closest

        #### Finalize ####
        if finalize:
            self.finalizeSolution(closest)

    def minSpanTree(self):
        #### Shorthand Attributes ####
        ssdo = self.ssdo
        weightsFile = self.weightsFile
        master2Order = ssdo.master2Order
        masterField = self.ssdo.masterField
        numObs = self.ssdo.numObs
        self.partition = NUM.zeros((numObs,), NUM.int32)

        #### Keep Track of Features with No Neighbors ####
        self.numFeatures = 0
        self.idsNoNeighs = []
        linkWatch = COLL.defaultdict(set)
        links = []
        weights = []

        contTypes = ['CONTIGUITY_EDGES_ONLY', 'CONTIGUITY_EDGES_CORNERS']
        if self.spaceConcept in contTypes:
            #### Use Polygon Neighbor Tool ####
            ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84126))
            contTable = "in_memory\contTab"
            ANA.PolygonNeighbors(self.ssdo.inputFC, contTable, masterField,
                                 "AREA_OVERLAP", "NO_BOTH_SIDES")

            #### Keep Track of Contiguity ####
            contiguity = NUM.zeros((self.ssdo.numObs,), NUM.int32)
            rookType = self.spaceConcept == 'CONTIGUITY_EDGES_ONLY'

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
                    try:
                        orderID = self.ssdo.master2Order[masterID]
                        neighOrderID = self.ssdo.master2Order[neighID]
                        iVals = self.z[orderID]
                        jVals = self.z[neighOrderID]
                        dist = ((iVals - jVals)**2.0).sum()
                        links.append((neighOrderID, orderID))
                        weights.append(dist)

                        #### Update Contiguity for Islands ####
                        contiguity[orderID] = 1
                        contiguity[neighOrderID] = 1
                    except:
                        #### Bad Record From Data Object ####
                        pass

            #### Add Nearest Neighbor to Islands ####
            islandOrder = NUM.where(contiguity == 0)[0]
            islandsPresent = len(islandOrder) != 0
            if islandsPresent:
                if self.numNeighs:

                    #### Additional Message for Nearest Neighbor Search ####
                    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84128))

                    #### Get Unique Island IDs ####
                    islands = [self.ssdo.order2Master[i] for i in islandOrder]
                    islands = set(islands)

                    #### Create GA Data Structure ####
                    gaTable, gaInfo = WU.gaTable(self.ssdo.inputFC, [masterField],
                                                 spatRef = self.ssdo.spatialRefString)
                    N = gaInfo[0]

                    #### Assure k-Nearest is Less Than Number of Features ####
                    if self.numNeighs >= N:
                        ARCPY.AddIDMessage("ERROR", 975)
                        raise SystemExit()

                    #### Create Nearest Neighbor Search Type For Islands ####
                    gaSearch = GAPY.ga_nsearch(gaTable)
                    gaConcept = self.distConcept.lower()
                    gaSearch.init_nearest(0.0, self.numNeighs, gaConcept)
                    neighSearch = ARC._ss.NeighborSearch(gaTable, gaSearch)

                    #### Add Island Nearest Neighbor Links to Links for MST ####
                    for row in islandOrder:
                        nhs = neighSearch[row]
                        for nh in nhs:
                            #### Explicit Cast for Search ####
                            nhInt = int(nh)
                            if nhInt not in linkWatch[row]:
                                jVals = self.z[nh]
                                dist = ((iVals - jVals)**2.0).sum()
                                links.append((row, nhInt))
                                weights.append(dist)
                                linkWatch[row].add(nhInt)

                    del islandOrder, islands, gaTable
                    self.numFeatures = self.ssdo.numObs

                else:
                    #### Islands without Links ####
                    self.numFeatures = self.ssdo.numObs - len(islandOrder)
                    for orderID in islandOrder:
                        masterID = self.ssdo.order2Master[orderID]
                        self.addNoNeighbor(masterID, orderID)
            else:
                self.numFeatures = self.ssdo.numObs

            #### Clean Up ####
            del rows, contiguity 
            UTILS.passiveDelete(contTable)

        elif self.spaceConcept == "GET_SPATIAL_WEIGHTS_FROM_FILE":
            #### Using Weights File ####
            if self.swmFileBool:
                #### Open Spatial Weights and Obtain Chars ####
                swm = WU.SWMReader(weightsFile)
                N = swm.numObs
                rowStandard = swm.rowStandard
                self.swm = swm

                #### Check to Assure Complete Set of Weights ####
                if ssdo.numObs > N:
                    ARCPY.AddIDMessage("ERROR", 842, ssdo.numObs, N)
                    raise SystemExit()
                
                #### Check if Selection Set ####
                isSubSet = False
                if ssdo.numObs < N:
                    isSubSet = True
                iterVals = xrange(N)
            else:
                #### Warning for GWT with Bad Records/Selection ####
                if ssdo.selectionSet or ssdo.badRecords:
                    ARCPY.AddIDMessage("WARNING", 1029)

                #### Build Weights Dictionary ####
                weightDict = WU.buildTextWeightDict(weightsFile, master2Order)
                iterVals = master2Order.keys()        
                N = ssdo.numObs

            ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84322), 0, N, 1)
            for i in iterVals:
                if self.swmFileBool:
                    #### Using SWM File ####
                    info = swm.swm.readEntry()
                    masterID = info[0]
                    if master2Order.has_key(masterID):
                        rowInfo = WU.getWeightsValuesSWM(info, master2Order,
                                                         self.z, 
                                                         isSubSet = isSubSet) 
                        includeIt = True
                    else:
                        includeIt = False
                else:
                    #### Text Weights ####
                    masterID = i
                    includeIt = True
                    rowInfo = WU.getWeightsValuesText(masterID, master2Order,
                                                      weightDict, self.z)

                #### Subset Boolean for SWM File ####
                if includeIt:
                    #### Parse Row Info ####
                    orderID, iVals, nhIDs, nhVals, sWeights = rowInfo

                    #### Assure Neighbors Exist After Selection ####
                    nn = len(nhVals)

                    if nn:
                        self.numFeatures += 1
                        for neigh in xrange(nn):
                            nhInt = int(nhIDs[neigh])
                            if nhInt not in linkWatch[orderID]:
                                links.append((orderID, nhInt))
                                jVals = nhVals[neigh]
                                dist = ((iVals - jVals)**2.0).sum()
                                weights.append(dist)

                    else:
                        #### No Neighbors ####
                        self.addNoNeighbor(masterID, orderID)

                ARCPY.SetProgressorPosition()

            #### Clean Up ####
            if self.swmFileBool:
                swm.close()

        else:
            #### Using GA Table Neighbor Searching ####
            ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84143)) 
            gaTable = self.ssdo.gaTable
            concept = self.distConcept.lower()
            gaSearch = GAPY.ga_nsearch(gaTable)

            if self.spaceConcept == "K_NEAREST_NEIGHBORS":
                #### K-Nearest Neighbors ####

                #### Assure Positive Number ####
                if self.numNeighs <= 0:
                    ARCPY.AddIDMessage("ERROR", 976)
                    raise SystemExit()

                #### Assure k-Nearest is Less Than Number of Features ####
                if self.numNeighs >= self.ssdo.numObs:
                    ARCPY.AddIDMessage("ERROR", 975)
                    raise SystemExit()

                #### Create k-Nearest Neighbor Search Type ####
                gaSearch.init_nearest(0.0, self.numNeighs, concept)

            else:
                #### Delaunay Triangulation ####
                gaSearch.init_delaunay()

            #### Find Fixed Distance Neighbors ####
            neighSearch = ARC._ss.NeighborSearch(gaTable, gaSearch)
            ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84118), 
                                0, self.ssdo.numObs, 1)

            for row in xrange(self.ssdo.numObs):
                iVals = self.z[row]
                nhs = neighSearch[row]
                hasNeighs = len(nhs) > 0
                for nh in nhs:
                    #### Explicit Cast for Search ####
                    nhInt = int(nh)
                    if nhInt not in linkWatch[row]:
                        jVals = self.z[nh]
                        dist = ((iVals - jVals)**2.0).sum()
                        links.append((row, nhInt))
                        weights.append(dist)
                        linkWatch[row].add(nhInt)
                if not hasNeighs:
                    #### No Neighbors ####
                    self.addNoNeighbor(self.ssdo.order2Master[orderID], 
                                       orderID)
                else:
                    self.numFeatures += 1

                ARCPY.SetProgressorPosition()

        #### Report on Features with No Neighbors ####
        WU.reportNoNeighborsGeneral(numObs, self.idsNoNeighs, masterField)

        self.links = NUM.array(links)
        self.weights = NUM.array(weights)
        self.ssd = COLL.defaultdict(float)
        self.seeds = NUM.zeros(self.n, dtype = NUM.int32)
        self.createMST()

    def createMST(self):
        mst, weights, clusterMap, count = ARC._ss.min_span_tree(self.links,
                                                              self.weights,
                                                          self.ssdo.numObs)
        disconnected = (count != self.ssdo.numObs - 1)

        #### Construct Starting Groups ####
        self.part2IDs = COLL.defaultdict(list)
        self.id2Parts = COLL.defaultdict(NUM.int32)
        tree = {}
        clustConvert = {}
        clusterIDs = COLL.defaultdict(list)

        #### Finalize Tree/Part Info ####
        if disconnected:
            mst = mst[0:count,:]
            clustKeys = NUM.unique(clusterMap)
            startingK = len(clustKeys)
            ARCPY.AddIDMessage("WARNING", 1392, str(startingK))
            for ind, clust in enumerate(clustKeys):
                ids = list(NUM.where(clusterMap == clust)[0])
                self.part2IDs[ind] = ids
                for i in ids:
                    self.id2Parts[i] = ind
                tree[ind] = COLL.defaultdict(list)
                clustConvert[clust] = ind

        else:
            #### Fully Connected MST ####
            startingK = 1
            clust = clusterMap[0]
            self.part2IDs[0] = range(self.ssdo.numObs)
            clustConvert[clust] = 0
            tree[0] = COLL.defaultdict(list)

        if startingK > self.kPartitions:
            ARCPY.AddIDMessage("ERROR", 1393)
            raise SystemExit()

        #### Assign Starting Groups ####
        for link in mst:
            u,v = link
            oldClust = clusterMap[u]
            newClust = clustConvert[oldClust]
            tree[newClust][v].append(u)
            tree[newClust][u].append(v)
            self.id2Parts[v] = newClust
            self.id2Parts[u] = newClust

        #### Set Attributes ####
        self.tree = tree
        self.mst = mst

        #### Set Starting Stats ####
        self.centroids = NUM.zeros((self.kLimit, self.k), float)
        for group in xrange(startingK):
            self.updateSSD(group)

    def setNullValue(self, orderID):
        """Set no neighbor data for a given feature (1).
        
        INPUTS:
        orderID (int): order in corresponding numpy value arrays
        
        NOTES:
        (1)   The no neighbor result differs for shapefiles as it has no NULL
              value capabilities.  
        """

        self.partition[orderID] = -10000

    def addNoNeighbor(self, masterID, orderID):
        """Accounting for features with no neighbors.
        
        INPUTS:
        masterID (int): unique ID value that has no neighbors
        orderID (int): order in corresponding numpy value arrays
        """

        self.idsNoNeighs.append(masterID)
        self.setNullValue(orderID)

    def updateSSD(self, regionID):
        ids = self.part2IDs[regionID]
        centroid = getCentroid(self.z, ids)
        self.centroids[regionID] = centroid
        ssd = dist2Centroid(self.z, centroid, partIDs = ids)
        self.ssd[regionID] = ssd.sum()

    def returnHighestSSD(self):
        highestSSD = 0.0
        highestRegion = 0
        for region, ssd in self.ssd.iteritems():
            if ssd > highestSSD:
                highestRegion = region
                highestSSD = ssd
        return highestRegion

    def updateNodeInfo(self, node, oldPart, newPart, skip = None):
        neighs = self.tree[oldPart][node]
        if skip != None:
            #### Remove the Tail ####
            neighs.remove(skip)
            self.tree[oldPart][skip].remove(node)
        self.tree[newPart][node] = neighs
        del self.tree[oldPart][node]
        self.id2Parts[node] = newPart
        self.part2IDs[oldPart].remove(node)
        self.part2IDs[newPart].append(node)

        return neighs

    def splitMST(self, link):
        newPart = len(self.tree) 
        self.tree[newPart] = COLL.defaultdict(list)
        head, tail = link

        #### Change Head Info and Get Init Neighs ####
        oldPart = self.id2Parts[head]
        headNodes = self.updateNodeInfo(head, oldPart, newPart, skip = tail)

        #### Span Tree and Assign to New Region ####
        collectedNodes = set([head])
        nodes2Move = set(headNodes)
        while len(nodes2Move):
            nodes2Add = set([])
            for node in nodes2Move:
                if node not in collectedNodes:
                    collectedNodes.add(node)
                    neighNodes = self.updateNodeInfo(node, oldPart, newPart)
                    for neigh in neighNodes:
                        if neigh not in collectedNodes:
                            nodes2Add.add(neigh)
            nodes2Move = nodes2Add

        self.updateSSD(oldPart)
        self.updateSSD(newPart)
        if len(self.tree) < self.kLimit:
            self.getRegionInfo(oldPart)
            self.getRegionInfo(newPart)

    def assessSplit(self, link):
        head, tail = link
        headPart = self.id2Parts[head]
        partIDs = self.part2IDs[headPart]
        centroidT = getCentroid(self.z, partIDs)
        SSDT = dist2Centroid(self.z, centroidT, partIDs = partIDs).sum()
        collectedNodes = set([])
        nodes2Move = set([head])
        while len(nodes2Move):
            nodes2Add = set([])
            for node in nodes2Move:
                if node not in collectedNodes:
                    collectedNodes.add(node)
                    neighNodes = self.tree[headPart][node]
                    for neigh in neighNodes:
                        if neigh not in collectedNodes and neigh != tail:
                            nodes2Add.add(neigh)
            nodes2Move = nodes2Add

        collectedNodes = list(collectedNodes)
        centroidTa = getCentroid(self.z, collectedNodes)
        SSDTa = dist2Centroid(self.z, centroidTa, 
                              partIDs = collectedNodes).sum()
        nodesUnmoved = list(set(partIDs).difference(collectedNodes))
        centroidTb = getCentroid(self.z, nodesUnmoved)
        SSDTb = dist2Centroid(self.z, centroidTb, partIDs = nodesUnmoved).sum()
        f1 = SSDT - (SSDTa + SSDTb)
        f2 = min((SSDT - SSDTa), (SSDT - SSDTb))
        return f1, f2

    def expandLink(self, link, L):
        for node in link:
            L = self.findLinks(node, L)
        return L

    def findLinks(self, node, L):
        region = self.id2Parts[node]
        choiceNeighs = self.tree[region][node]
        for neigh in choiceNeighs:
            if (neigh, node) not in L:
                L.add((node, neigh))

        return L

    def centralVertex(self, region):
        ids = self.part2IDs[region]
        xyCoords = self.ssdo.xyCoords[ids]
        meanXY = xyCoords.mean(0)
        distXY = dist2Centroid(xyCoords, meanXY)
        central = ids[NUM.argmin(distXY)]
        return central

    def initialExpand(self, region, central):
        Sp = set([])
        choiceNeighs = self.tree[region][central]
        if len(choiceNeighs):
            central = (central, choiceNeighs[0])
            for node in central:
                Sp = self.findLinks(node, Sp)
        return Sp

    def getRegionInfo(self, region):
        #### Step 1 ####
        SC = 15
        self.f2Results = COLL.defaultdict(float)
        subTree = self.tree[region]
        if len(subTree) == 1:
            #### Singleton ####
            self.regionInfo[region] = (None, 0.0)
            return

        v = self.centralVertex(region)
        nStar = 0
        f1Star = 0.0
        L = self.initialExpand(region, v)

        #### Step 2 ####
        maxF1 = 0.0
        maxF1Link = None
        usedF2 = set([])
        flag = 1
        c = 0
        while flag:
            for link in L:
                if not self.f2Results.has_key(link):
                    f1, f2 = self.assessSplit(link)
                    if f1 > maxF1:
                        maxF1 = f1
                        maxF1Link = link
                    self.f2Results[link] = f2
            
            #### Step 3 ####
            if maxF1 > f1Star:
                f1Star = maxF1
                nStar = 0

            #### Step 4 ####
            nStar += 1
            sortedF2 = sorted(self.f2Results.iteritems(), 
                              key = OP.itemgetter(1), reverse = True)
            f2Flag = 1
            while f2Flag:
                for f2Link, f2Res in sortedF2:
                    if f2Link not in usedF2:
                        self.expandLink(f2Link, L)
                        usedF2.add(f2Link)
                        break
                f2Flag = 0

            #### Artificial Stop ####
            c += 1
            if c == 1000:
                n = 20
                nStar = 1

            #### Stopping Conditions ####
            #### No Change in 15 Expanding Searches ####
            if nStar > SC:
                flag = 0
            #### All Links Tried ####
            if len(self.f2Results) == len(subTree) - 1:
                flag = 0

        self.regionInfo[region] = (maxF1Link, maxF1)

    def spatialSolve(self, optimize = False):
        self.regionInfo = {}
        if optimize:
            self.fStatRes = []
            self.groupList = []

        #### Set Progressor ####
        ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84324), 
                            0, self.kLimit, 1)

        #### Get Initial Region Info ####
        for region in self.tree.keys():
            self.getRegionInfo(region)
            ARCPY.SetProgressorPosition()

        #### Finalize if Number of Disconnected == Num Groups ####
        startTree = len(self.tree)
        startStat = startTree == self.kPartitions
        if startStat:
            self.finalizeSpatial()

        #### Report Starting Disconnected FStat ####
        if (1 < startTree < maxNumGroups + 1) and optimize:
            if startStat:
                fStat = self.fStat
            else:
                fStat = self.getFStat(startTree)
            self.fStatRes.append(fStat)
            self.groupList.append(startTree)
            fOut = LOCALE.format("%0.4f", fStat)
            msg = ARCPY.GetIDMessage(84326).format(startTree, fOut)
            ARCPY.AddMessage(msg)

        #### Spatial Partition ####
        highestRegion = 0
        while len(self.tree) < self.kLimit:
            highestF1 = 0.0
            for region, info in self.regionInfo.iteritems():
                f1Link, f1 = info
                if f1 > highestF1:
                    highestRegion = region
                    highestF1 = f1
            
            f1Link, f1 = self.regionInfo[highestRegion]
            self.splitMST(f1Link)
            nc = len(self.tree)
            setStats = nc == self.kPartitions 
            if setStats:
                self.finalizeSpatial()
            reportFStat = (1 < nc < maxNumGroups + 1)
            if optimize and reportFStat:
                if setStats:
                    fStat = self.fStat
                else:
                    fStat = self.getFStat(nc)
                self.fStatRes.append(fStat)
                self.groupList.append(nc)
                fOut = LOCALE.format("%0.4f", fStat)
                msg = ARCPY.GetIDMessage(84326).format(nc, fOut)
                ARCPY.AddMessage(msg)
            ARCPY.SetProgressorPosition()

        if optimize:
            self.fStatRes = NUM.array(self.fStatRes)

    def finalizeSolution(self, solution):
        """Sets the final group numbers to the features."""
        #### Assign Partitions ####
        self.partition = solution
        self.partitionOutput = self.partition + 1
        self.setStatistics(self.partition)

        #### Warn of Disconnected Group(s) ####
        if NUM.any(self.partition == -10000):
            ARCPY.AddIDMessage("WARNING", 1329)
                
    def finalizeSpatial(self):
        """Sets the final group numbers to the features."""
        #### Assign Partitions ####
        for id, part in self.id2Parts.iteritems():
            self.partition[id] = part
        self.partitionOutput = self.partition + 1
        self.setStatistics(self.partition)

        #### Warn of Disconnected Group(s) ####
        if NUM.any(self.partition == -10000):
            ARCPY.AddIDMessage("WARNING", 1329)

    def getFStat(self, numGroups):
        SSE = 0.0
        SSR = 0.0
        nc = numGroups
        n = self.numFeatures
        for group in xrange(nc):
            ids = self.part2IDs[group]
            nGroup = len(ids)
            centroid = getCentroid(self.z, ids)
            flat = dist2Centroid(self.z, centroid, partIDs = ids)
            SSE += flat.sum()
            SSR += (nGroup * 1.0) * ((centroid - self.zMean)**2.0).sum()

        #### R2 and Pseudo f-Statistic ####
        R2 = (self.SST - SSE) / self.SST
        fStat = (R2 / (nc - 1)) / ((1 - R2) / (n - nc))
        return fStat

    def getFStatFromSolution(self, solution):

        #### Get Unique Region IDs and Number of Groups ####
        groups = NUM.unique(solution)
        numGroups = len(groups)

        SSE = 0.0
        SSR = 0.0
        nc = numGroups
        n = self.numFeatures
        for group in xrange(nc):
            ids = NUM.where(solution == group)
            nGroup = len(ids)
            centroid = getCentroid(self.z, ids)
            flat = dist2Centroid(self.z, centroid, partIDs = ids)
            SSE += flat.sum()
            SSR += (nGroup * 1.0) * ((centroid - self.zMean)**2.0).sum()

        #### R2 and Pseudo f-Statistic ####
        R2 = (self.SST - SSE) / self.SST
        fStat = (R2 / (nc - 1)) / ((1 - R2) / (n - nc))
        return fStat

    def setStatistics(self, solution):

        #### Get Unique Region IDs and Number of Groups ####
        groups = NUM.unique(solution)
        if groups[0] == -10000:
            groups = groups[1:]
        numGroups = len(groups)
        self.numGroups = numGroups

        #### Create Global Values ####
        self.meanVals = self.x.mean(0)
        self.stdVals = self.x.std(0)
        self.minVals = self.x.min(0)
        self.maxVals = self.x.max(0)
        self.globalXDist = dist2Centroid(self.x, self.meanVals)
        globalXSum = self.globalXDist.sum()
        self.globalSTD = NUM.sqrt(globalXSum / self.numFeatures)

        #### Create Group Means ####

        self.globalRange = self.maxVals - self.minVals
        self.groupMeans = NUM.empty((numGroups, self.k), float)
        self.groupMeansZ = NUM.empty((numGroups, self.k), float)
        self.groupSTD = NUM.empty((numGroups, self.k), float)
        self.groupSSDZ = NUM.empty((numGroups,), float)
        self.groupSSDX = NUM.empty((numGroups,), float)
        self.groupMin = NUM.empty((numGroups, self.k), float)
        self.groupMax = NUM.empty((numGroups, self.k), float)
        self.groupRange = NUM.empty((numGroups, self.k), float)
        self.groupProp = NUM.zeros((numGroups, self.k), float)
        self.groupCount = NUM.empty((numGroups,), int)
        self.groupSTDDiff = NUM.empty((numGroups,), float)
        SSE = 0.0
        SSR = 0.0
        nc = numGroups * 1.0
        n = self.numFeatures

        for group in xrange(numGroups):
            groupInd = NUM.where(solution == group)
            centroid = getCentroid(self.z, groupInd)
            groupX = self.x[groupInd]
            nGroup = len(groupInd[0])
            self.groupCount[group] = nGroup
            self.groupMeans[group] = groupX.mean(0)
            self.groupMeansZ[group] = centroid
            self.groupSTD[group] = groupX.std(0)
            gMin = groupX.min(0)
            gMax = groupX.max(0)
            gRange = gMax - gMin
            self.groupMin[group] = gMin
            self.groupMax[group] = gMax
            self.groupRange[group] = gRange
            nonZeroInds = gRange.nonzero() 
            for ind in nonZeroInds[0]:
                self.groupProp[group][ind] = gRange[ind]/self.globalRange[ind]

            distZ = dist2Centroid(self.z, centroid, partIDs = groupInd)
            distX = dist2Centroid(self.x, self.groupMeans[group], 
                                  partIDs = groupInd)
            fSSD = varDist2Centroid(self.z, centroid, partIDs = groupInd)
            distSum = distZ.sum()
            SSE += distSum
            SSR += (nGroup * 1.0) * ((centroid - self.zMean)**2.0).sum()
            distXSum = distX.sum()
            stdDist = NUM.sqrt((distXSum / nGroup))
            self.groupSTDDiff[group] = stdDist
            self.varSSE[group] = fSSD
            self.groupSSDZ[group] = distSum
            self.groupSSDX[group] = distXSum

        #### R2 and Pseudo f-Statistic ####
        self.withinSS = SSE
        self.betweenSS = SSR
        self.totalSS = self.SST
        self.R2 = (self.SST - SSE) / self.SST
        self.fStat = (self.R2 / (nc - 1)) / ((1 - self.R2) / (n - nc))

        #### Varwise R-Squared ####
        self.varR2 = (self.varSST - self.varSSE.sum(0)) / self.varSST
        self.globalZDistSum = self.groupSSDZ.sum()

    def report(self, fileName = None, optimal = False):

        #### Start Table Info ####
        header = ARCPY.GetIDMessage(84268)
        varLabel = ARCPY.GetIDMessage(84068)
        groupLabel = ARCPY.GetIDMessage(84398)
        meanLabel = ARCPY.GetIDMessage(84261)
        stdLabel = ARCPY.GetIDMessage(84262)
        minLabel = ARCPY.GetIDMessage(84271)
        maxLabel = ARCPY.GetIDMessage(84272)
        r2Label = ARCPY.GetIDMessage(84018)

        varWiseLabels = [varLabel, meanLabel, stdLabel, 
                         minLabel, maxLabel, r2Label]

        #### Sort by R2 ####
        sortedIndices = self.varR2.argsort()
        sortedIndices = list(reversed(sortedIndices))

        results = [ varWiseLabels ]
        for varInd in sortedIndices:
            rowRes = [self.meanVals[varInd], self.stdVals[varInd],
                      self.minVals[varInd], self.maxVals[varInd],
                      self.varR2[varInd]]
            rowRes = [ UTILS.formatValue(i) for i in rowRes ]
            varName = self.varNames[varInd]
            rowRes = [varName] + rowRes
            results.append(rowRes)

        self.resTable = UTILS.outputTextTable(results, header = header,
                                              justify = "right", pad = 1)
        ARCPY.AddMessage(self.resTable)

        #### Create Output Graphics ####
        if fileName:
            #### Set Progressor ####
            numPages = numberOfGroupPages(self.numGroups, self.k)
            writeMSG = ARCPY.GetIDMessage(84186)
            ARCPY.SetProgressor("step", writeMSG, 0, numPages, 1)
            ARCPY.AddMessage(writeMSG)

            #### Import Matplotlib ####
            pdfOutput = REPORT.openPDF(fileName)

            #### Partition-Wise Table ####
            groupTitle = ARCPY.GetIDMessage(84270)
            groupTitlePlus = groupTitle + " " + ARCPY.GetIDMessage(84274)
            report = REPORT.startNewReport(8, title = groupTitle,
                                           landscape = True,
                                           titleFont = REPORT.ssTitleFont)
            grid = report.grid

            #### Create BoxPlot Temp Grid ####
            grid.createEmptyRow()
            boxGrid = PLT.subplot2grid((numRows, 8), (1, 2), rowspan = 4, colspan = 4)

            #### Annotated Box-Plot ####
            xValues = NUM.linspace(1, 100, 1000)
            xValues = xValues**2.0
            xValues[-4:] = [-2000., 110., 125., 13500.]
            globalMean = xValues.mean()
            globalMax = xValues.max()
            bp = PLT.boxplot(xValues, vert = 0, widths = .5)
            PLT.setp(bp['boxes'], color='black')
            PLT.setp(bp['whiskers'], color='black', ls = 'solid')
            PLT.setp(bp['medians'], color='black') 
            PLT.setp(bp['fliers'], color='black')  
            PLT.setp(bp['caps'], color='black')  
            sortX = NUM.sort(xValues)
            groupX = sortX[550:800]
            meanVal = groupX.mean() + 10.0
            minVal = groupX.min()
            maxVal = groupX.max()

            #### Arrow Styles ####
            fancy = dict(arrowstyle="fancy", fc="0.2", ec="none", 
                         connectionstyle = "angle3,angleA=0,angleB=-90")

            #### Median ####
            median = bp['medians'][0].get_xdata()[0]
            boxGrid.annotate(ARCPY.GetIDMessage(84115), 
                             xy = (median+50, 1.25), 
                             xytext = (median-1200, 1.55),
                             fontproperties = REPORT.ssSmallFont, 
                             arrowprops=fancy)

            #### Quartiles ####
            qValues = bp['boxes'][0].get_xdata()
            lowerQ = qValues.min()
            upperQ = qValues.max()
            boxGrid.annotate(ARCPY.GetIDMessage(84345), xy = (lowerQ, 1.25), 
                             xytext = (lowerQ-6000, 1.45),
                             fontproperties = REPORT.ssSmallFont, 
                             size = 8, arrowprops=fancy)
            boxGrid.annotate(ARCPY.GetIDMessage(84346), xy = (upperQ, 1.25), 
                             xytext = (upperQ+1500, 1.45),
                             fontproperties = REPORT.ssSmallFont, 
                             size = 8, arrowprops=fancy)

            #### Whiskers ####
            lowerW = bp['whiskers'][0].get_xdata().min()
            upperW = bp['whiskers'][1].get_xdata().max()
            boxGrid.annotate(ARCPY.GetIDMessage(84347), xy = (lowerW, 1.125), 
                             xytext = (lowerW-6000, 1.25),
                             fontproperties = REPORT.ssSmallFont, 
                             size = 8, arrowprops=fancy)
            boxGrid.annotate(ARCPY.GetIDMessage(84348), xy = (upperW, 1.125), 
                             xytext = (upperW+1500, 1.25),
                             fontproperties = REPORT.ssSmallFont, 
                             size = 8, arrowprops=fancy)

            #### Outlier ####
            boxGrid.annotate(ARCPY.GetIDMessage(84351), xy = (globalMax, .95), 
                             xytext = (globalMax-2200, 0.7),
                             fontproperties = REPORT.ssSmallFont, 
                             size = 8, arrowprops=fancy)

            #### Group Mean ####
            PLT.plot(meanVal, 1., color = "r", marker = "o")
            boxGrid.annotate(ARCPY.GetIDMessage(84352), xy = (meanVal, .95), 
                             xytext = (meanVal-1200, 0.6),
                             fontproperties = REPORT.ssSmallFont, 
                             size = 8, arrowprops=fancy)

            #### Group Min and Max ####
            PLT.plot((minVal, minVal), (.8, 1.2), color = "r", linestyle = "-")
            PLT.plot((maxVal, maxVal), (.8, 1.2), color = "r", linestyle = "-")
            boxGrid.annotate(ARCPY.GetIDMessage(84353), xy = (minVal, .75), 
                             xytext = (minVal-1700, 0.4),
                             fontproperties = REPORT.ssSmallFont, 
                             size = 8, arrowprops=fancy)
            boxGrid.annotate(ARCPY.GetIDMessage(84354), xy = (maxVal, .75), 
                             xytext = (maxVal, 0.4),
                             fontproperties = REPORT.ssSmallFont, 
                             size = 8, arrowprops=fancy)
            
            #### Finalize ####
            REPORT.clearGrid(boxGrid)
            grid.rowCount = 5
            grid.createEmptyRow()

            #### Get Column Labels ####
            r2Label = ARCPY.GetIDMessage(84018)
            shareLabel = ARCPY.GetIDMessage(84273)
            colLabs = [varLabel, meanLabel, stdLabel, 
                       minLabel, maxLabel, r2Label]

            #### Add Global Group ####
            labVals = (self.numFeatures, numSep,
                       LOCALE.format("%0.4f", self.globalSTD), 
                       LOCALE.format("%0.4f", self.globalZDistSum))
            label = ARCPY.GetIDMessage(84357).format(*labVals)
            color = "black"
            newGroup(grid, label, color, colspan = 6)
            grid.createColumnLabels(colLabs, justify = "left")

            #### Make Group Rows ####
            for ind in sortedIndices:
                var = self.varNames[ind]
                if grid.rowCount >= 20:
                    #### Finalize Page ####
                    grid.finalizeTable()
                    report.write(pdfOutput)
                    ARCPY.SetProgressorPosition()

                    #### New Page ####
                    report = REPORT.startNewReport(8, title = groupTitlePlus, 
                                                   landscape = True,
                                                   titleFont = REPORT.ssTitleFont)
                    grid = report.grid

                    #### Create New Grid ####
                    grid.createColumnLabels(colLabs, justify = "left")

                values = self.x[:,ind]
                meanVal = self.meanVals[ind]
                stdVal = self.stdVals[ind]
                minVal = self.minVals[ind]
                maxVal = self.maxVals[ind]
                extraVal = self.varR2[ind]

                #### Maximum 12 Char Limit for Var Names ####
                var = var[0:12]
                outInfo = [var, meanVal, stdVal, minVal, maxVal, extraVal]
                createRow(grid, outInfo, values, addGroup = False)

            #### Add Group Tables ####
            colLabs[-1] = shareLabel

            for group in xrange(self.numGroups):
                color = colors[group]
                if grid.rowCount >= 17:
                    #### Finalize Page ####
                    grid.finalizeTable()
                    report.write(pdfOutput)
                    ARCPY.SetProgressorPosition()

                    #### New Page ####
                    report = REPORT.startNewReport(8, title = groupTitlePlus, 
                                                            landscape = True,
                                              titleFont = REPORT.ssTitleFont)
                    grid = report.grid

                #### Create Group Header ####
                count = self.groupCount[group]
                stdDist = self.groupSTDDiff[group]
                ssdVal = self.groupSSDZ[group]
                labVals = (group + 1, count, numSep, 
                           LOCALE.format("%0.4f", stdDist), 
                           LOCALE.format("%0.4f", ssdVal))
                label = ARCPY.GetIDMessage(84276).format(*labVals)
                newGroup(grid, label, color)

                #### Add Column Labels ####
                grid.createColumnLabels(colLabs, justify = "left")
                for ind in sortedIndices:
                    var = self.varNames[ind]
                    if grid.rowCount >= 20:
                        #### Finalize Page ####
                        grid.finalizeTable()
                        report.write(pdfOutput)
                        ARCPY.SetProgressorPosition()

                        #### New Page ####
                        report = REPORT.startNewReport(8, title = groupTitlePlus, 
                                                                landscape = True,
                                                  titleFont = REPORT.ssTitleFont)
                        grid = report.grid

                        #### Group Label Happens to be First ####
                        if ind == 0:
                            newGroup(grid, label, color)

                        #### Reload Column Labels ####
                        grid.createColumnLabels(colLabs, justify = "left")

                    values = self.x[:,ind]
                    meanVal = self.groupMeans[group, ind]
                    stdVal = self.groupSTD[group, ind]
                    minVal = self.groupMin[group, ind]
                    maxVal = self.groupMax[group, ind]
                    extraVal = self.groupProp[group, ind]

                    #### Maximum 12 Char Limit for Var Names ####
                    var = var[0:12]
                    outInfo = [var, meanVal, stdVal, minVal, maxVal, extraVal]
                    createRow(grid, outInfo, values, color = color)

            #### Finalize Page ####
            grid.finalizeTable()
            report.write(pdfOutput)
            ARCPY.SetProgressorPosition()

            #### Variable-Wise Table ####
            varTitle = ARCPY.GetIDMessage(84268)
            varTitlePlus = varTitle + " " + ARCPY.GetIDMessage(84274)
            report = REPORT.startNewReport(8, title = varTitle, 
                                           landscape = True,
                                           titleFont = REPORT.ssTitleFont)
            grid = report.grid
            colLabs = [groupLabel, meanLabel, stdLabel, 
                       minLabel, maxLabel, shareLabel]

            #### Add Variable Tables ####
            for ind in sortedIndices:
                var = self.varNames[ind]
                #### Global Info ####
                values = self.x[:,ind]
                meanVal = self.meanVals[ind]
                stdVal = self.stdVals[ind]
                minVal = self.minVals[ind]
                maxVal = self.maxVals[ind]
                extraVal = 1.0
                R2 = self.varR2[ind]
                totalStr = ARCPY.GetIDMessage(84355)
                gOutInfo = [totalStr, meanVal, stdVal, 
                            minVal, maxVal, extraVal]

                if grid.rowCount >= 17:
                    #### Finalize Page ####
                    grid.finalizeTable()
                    report.write(pdfOutput)
                    ARCPY.SetProgressorPosition()

                    #### New Page ####
                    report = REPORT.startNewReport(8, title = varTitlePlus, 
                                                   landscape = True,
                                                   titleFont = REPORT.ssTitleFont)
                    grid = report.grid

                #### Add Header and Column Labels ####
                formatR2 = LOCALE.format("%0.2f", R2)
                R2Vals = (var[0:12], formatR2)
                R2String = ARCPY.GetIDMessage(84356).format(*R2Vals)
                newVarGroup(grid, R2String)
                grid.createColumnLabels(colLabs, justify = "left")

                #### Add Groups ####
                for group in xrange(self.numGroups):
                    color = colors[group]
                    groupID = "%i" % (group + 1)
                    if grid.rowCount >= 19:
                        #### Finalize Page ####
                        grid.finalizeTable()
                        report.write(pdfOutput)
                        ARCPY.SetProgressorPosition()

                        #### New Page ####
                        report = REPORT.startNewReport(8, title = varTitlePlus, 
                                                              landscape = True,
                                                titleFont = REPORT.ssTitleFont)
                        grid = report.grid
                        grid.createColumnLabels(colLabs, justify = "left")

                    meanVal = self.groupMeans[group, ind]
                    stdVal = self.groupSTD[group, ind]
                    minVal = self.groupMin[group, ind]
                    maxVal = self.groupMax[group, ind]
                    extraVal = self.groupProp[group, ind]
                    outInfo = [groupID, meanVal, stdVal, minVal, maxVal, extraVal]
                    createRow(grid, outInfo, values, color = color)

                #### Add Total Row ####
                createRow(grid, gOutInfo, values)

            #### Finalize Var-Wise Table ####
            grid.finalizeTable()
            report.write(pdfOutput)
            ARCPY.SetProgressorPosition()

            #### Parallel Box Plot ####
            title = ARCPY.GetIDMessage(84277)
            report = REPORT.startNewReport(8, title = title, landscape = True,
                                           titleFont = REPORT.ssTitleFont)
            ax = report.fig.add_subplot(111)

            #### Sort Variables to Minimize Crossing/Deviations ####
            maxVarVar = self.groupMeansZ.var(0).argmax()
            varIndOut = [maxVarVar]
            row2Comp = maxVarVar
            notUsed = range(0, self.k)
            notUsed.remove(maxVarVar)
            sumSquares = NUM.float64(1.7976931348623158e+308)
            newCand = None
            while len(notUsed):
                for col in notUsed:
                    cData0 = self.groupMeansZ[:,row2Comp]
                    cData1 = self.groupMeansZ[:,col]
                    diff = ((cData0 - cData1)**2.0).sum()
                    if diff < sumSquares:
                        sumSquares = diff
                        newCand = col
                notUsed.remove(newCand)
                varIndOut.append(newCand)
                row2Comp = newCand
                sumSquares = NUM.float64(1.7976931348623158e+308)
                newCand = None
            
            #### Construct Box Plot ####
            sortedZ =  self.z[:,varIndOut]
            sortedZMeans = self.groupMeansZ[:,varIndOut]
            bp = PLT.boxplot(sortedZ, vert = 0)
            PLT.setp(bp['boxes'], color='black')
            PLT.setp(bp['whiskers'], color='black')
            PLT.setp(bp['medians'], color='black') 
            PLT.setp(bp['fliers'], color='black') 
            PYLAB.xlabel(ARCPY.GetIDMessage(84269), 
                         fontproperties = REPORT.ssLabFont)
            rowLabels = []

            #### Add Group Means ####
            for i in xrange(self.k):
                varInd = varIndOut[i]
                varName = self.varNames[varInd]
                med = bp['medians'][i]
                yVal = i + 1
                for group in xrange(self.numGroups):
                    xVal = sortedZMeans[group, i]
                    cVal = colors[group]
                    pnt = PLT.plot(xVal, yVal, color=cVal, marker='o', 
                                   markeredgecolor='k')
                    if i < self.k-1:
                        xVal1 = sortedZMeans[group, i+1]
                        PLT.plot([xVal, xVal1], [yVal, yVal+1], 
                                 color=cVal, linestyle='-', markeredgecolor='k')

                rowLabels.append(varName)
            
            #### Max 11 Char Limit on Var Names ####
            yLabs = [ i[0:11] for i in rowLabels ]
            yticks = PLT.setp(ax, yticklabels = yLabs)

            #### Finalize Page ####
            report.write(pdfOutput)
            ARCPY.SetProgressorPosition()

            #### Add Dataset/Parameter Info ####
            paramLabels = [84253, 84359, 84360]
            paramLabels = [ ARCPY.GetIDMessage(i) for i in paramLabels ]
            paramValues = [self.ssdo.inputFC, self.ssdo.masterField,
                           self.ssdo.templateFC]

            #### Set Analysis Field Names ####
            countRows = len(paramLabels) + 1
            maxVarLen = 100
            varLines = [ i[0:(maxVarLen - 1)] for i in self.varNames ]
            for ind, varLine in enumerate(varLines):
                if ind == 0:
                    paramLabels.append(ARCPY.GetIDMessage(84399))
                elif countRows >= 20:
                    paramLabels.append(ARCPY.GetIDMessage(84399))
                    countRows = 1
                else:
                    paramLabels.append("")
                countRows += 1
                paramValues.append(varLine)

            #### Complete Param Info ####
            addLabels = [84361, 84235, 84362, 84238, 84363, 84364, 84418]
            paramLabels += [ ARCPY.GetIDMessage(i) for i in addLabels ]
            paramValues += [self.spaceConcept, self.distConcept,
                            self.numNeighs, self.weightsFile,
                            self.initMethod, self.initField,
                            str(self.ssdo.selectionSet)]

            title = ARCPY.GetIDMessage(84365)
            REPORT.createParameterPage(paramLabels, paramValues, 
                                       title = title,
                                       pdfOutput = pdfOutput,
                                       titleFont = REPORT.ssTitleFont)
            ARCPY.SetProgressorPosition()

            #### Finish Up ####
            ARCPY.AddMessage(fileName)
            if not optimal:
                pdfOutput.close()
                return None
            else:
                return pdfOutput
        else:
            return None

    def createOutput(self, outputFC):

        #### Prepare Derived Variables for Output Feature Class ####
        outPath, outName = OS.path.split(outputFC)
        fn = UTILS.getFieldNames(gaFieldNames, outPath)
        partFieldName, seedFieldName = fn
        appendFields = self.varNames + self.badVarNames

        if self.spaceConcept == "NO_SPATIAL_CONSTRAINT":
            #### Aspatial Concepts, Includes Seed Info ####
            fieldOrder = [seedFieldName, partFieldName]
            fieldData = [self.seeds, self.partitionOutput]
            if self.initMethod == "GET_SEEDS_FROM_FIELD":
                appendFields += [self.initField]
        else:
            #### Spatial Concepts, No Seeds ####
            fieldOrder = [partFieldName]
            fieldData = [self.partitionOutput]

        #### Create/Populate Dictionary of Candidate Fields ####
        candidateFields = {}
        for fieldInd, fieldName in enumerate(fieldOrder):
            candidateField = SSDO.CandidateField(fieldName, "LONG", 
                                                 fieldData[fieldInd])
            candidateFields[fieldName] = candidateField

        #### Add Date-Time Field If Applicable ####
        if self.swmFileBool:
            if self.swm.wType == 9:
                if self.ssdo.allFields.has_key(self.swm.timeField.upper()):
                    appendFields.insert(0, self.swm.timeField.upper())

        #### Write Data to Output Feature Class ####
        self.ssdo.output2NewFC(outputFC, candidateFields, 
                               appendFields = appendFields,
                               fieldOrder = fieldOrder)

        #### Set the Default Symbology ####
        params = ARCPY.gp.GetParameterInfo()
        try:
            renderType = UTILS.renderType[self.ssdo.shapeType.upper()]
            if renderType == 0:
                renderLayerFile = "GroupPoints.lyr"
            elif renderType == 1:
                renderLayerFile = "GroupPolylines.lyr"
            else:
                renderLayerFile = "GroupPolygons.lyr"
            templateDir = OS.path.dirname(OS.path.dirname(SYS.argv[0]))
            fullRLF = OS.path.join(templateDir, "Templates", 
                                   "Layers", renderLayerFile)
            params[2].Symbology = fullRLF 
        except:
            ARCPY.AddIDMessage("WARNING", 973)

def plotFStatsSpatial(pdfOutput, groupList, fStatRes, maxInd = None):

    #### Add Message and Progress ####
    writeMSG = ARCPY.GetIDMessage(84327)
    ARCPY.SetProgressor("default", writeMSG)
    ARCPY.AddMessage(writeMSG)

    #### Set Base Figure ####
    title = ARCPY.GetIDMessage(84328)
    report = REPORT.startNewReport(22, title = title, landscape = True,
                                   titleFont = REPORT.ssTitleFont)
    grid = report.grid
    startRow = 1
    gridPlot = PLT.subplot2grid(grid.gridInfo, (startRow, 0), 
                                colspan = 19, rowspan = 16)
            
    #### Add Series and Max Point ####
    if maxInd != None:
        #### Max Peak ####
        maxPoint = PLT.plot(groupList[maxInd], fStatRes[maxInd], 
                            color='#00FFFF', marker='o', alpha = 0.7,
                            markeredgecolor='k', markersize = 14)

    #### Full Series ####
    for ind, group in enumerate(groupList):
        PLT.plot(group, fStatRes[ind], color='b', marker='o', 
                 alpha = 0.7, markeredgecolor='k', 
                 markersize = 8)

    #### Set Axis Labels ####
    PYLAB.ylabel(ARCPY.GetIDMessage(84330), fontproperties = REPORT.ssLabFont, 
                 labelpad = 20)
    PYLAB.xlabel(ARCPY.GetIDMessage(84329), fontproperties = REPORT.ssLabFont, 
                 labelpad = 20)
    gridPlot.yaxis.grid(True, linestyle='-', which='major', color='lightgrey',
                        alpha=0.5)
    REPORT.setTickFontSize(gridPlot)

    #### Scoot Max/Min F and Groups ####
    minF, maxF = UTILS.increaseMinMax(fStatRes, multiplier = .15)
    minG, maxG = UTILS.increaseMinMax(groupList, multiplier = .15)
    PYLAB.ylim(ymin = minF, ymax = maxF)
    PYLAB.xlim(xmin = minG, xmax = maxG)

    #### Create Legend ####
    legLab = ARCPY.GetIDMessage(84415)
    grid.writeCell((startRow, 20), legLab,  fontObj = REPORT.ssBoldFont, 
                   justify = "left")
    labels = [ARCPY.GetIDMessage(84024)]

    gridCount = 0
    colors = ['b']
    markers = ['o']
    for ind, lab in enumerate(labels):
        color = colors[ind]
        marker = markers[ind]
        row = ind + 1 + startRow
        gridCount += 1

        #### Add Points ####
        gridLegend = PLT.subplot2grid(grid.gridInfo, (row, 20))
        PLT.plot(0.0, 0.0, color = color, marker = marker, alpha = .7)
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
    peakLab = ARCPY.GetIDMessage(84416).format(ARCPY.GetIDMessage(84024))
    gridLegend = PLT.subplot2grid(grid.gridInfo, (currentRow, 21))
    PLT.text(0.0, 0.3, peakLab, fontproperties = REPORT.ssFont, 
             horizontalalignment = "left")
    REPORT.clearGrid(gridLegend)

    #### Add To PDF ####
    report.write(pdfOutput)

    #### Create Table ####
    title = ARCPY.GetIDMessage(84411)
    report = REPORT.startNewReport(4, title = title, landscape = True,
                                   titleFont = REPORT.ssTitleFont)
    grid = report.grid

    #### Add Labels ####
    colLabs = [ARCPY.GetIDMessage(84329), ARCPY.GetIDMessage(84330)] 
    for ind, label in enumerate(colLabs):
        if ind == 0:
            justify = "left"
        else:
            justify = "right"
        grid.writeCell((grid.rowCount, ind+1), label, 
                        fontObj = REPORT.ssBoldFont, justify = justify)
    grid.stepRow()

    #### Add Values ####
    for ind, group in enumerate(groupList):
        maxFOut = UTILS.formatValue(fStatRes[ind], "%0.4f")
        grid.writeCell((grid.rowCount, 1), str(group), 
                        justify = "left")
        grid.writeCell((grid.rowCount, 2), maxFOut, 
                        justify = "right")
        grid.stepRow()
    grid.finalizeTable()
    report.write(pdfOutput)

    #### Finish Up ####
    pdfOutput.close()

def plotFStats(pdfOutput, groupList, fStatRes, maxInd = None):

    #### Add Message and Progress ####
    writeMSG = ARCPY.GetIDMessage(84327)
    ARCPY.SetProgressor("default", writeMSG)
    ARCPY.AddMessage(writeMSG)

    #### Set Base Figure ####
    title = ARCPY.GetIDMessage(84328)
    report = REPORT.startNewReport(22, title = title, landscape = True,
                                   titleFont = REPORT.ssTitleFont)
    grid = report.grid
    startRow = 1
    gridPlot = PLT.subplot2grid(grid.gridInfo, (startRow, 0), 
                                colspan = 19, rowspan = 16)

    #### Mean Line ####
    meanFVals = fStatRes.mean(1)

    #### Min Line ####
    minFVals = fStatRes.min(1)

    #### Max Line ####
    maxFVals = fStatRes.max(1)

    #### Median Line ####
    medians = [STATS.median(i) for i in fStatRes]

    #### Add Series and Max Point ####
    if maxInd != None:
        #### Max Peak ####
        maxPoint = PLT.plot(groupList[maxInd], meanFVals[maxInd], 
                            color='#00FFFF', marker='o', alpha = 0.7,
                            markeredgecolor='k', markersize = 14)

    #### Full Series ####
    for ind, group in enumerate(groupList):
        #### Mean ####
        PLT.plot(group, meanFVals[ind], color='b', marker='o', 
                 alpha = 0.7, markeredgecolor='k', 
                 markersize = 8)

        #### Median ####
        PLT.plot(group, medians[ind], color='r', marker='D', 
                 alpha = 0.7, markeredgecolor='k', 
                 markersize = 6)

        #### Vlines ####
        minVal = minFVals[ind]
        maxVal = maxFVals[ind]
        PLT.vlines(group, minVal, maxVal, color = '0.75')

        #### Whiskers ####
        PLT.plot([group-.1, group+.1], [minVal, minVal], color='0.75', linestyle='-')
        PLT.plot([group-.1, group+.1], [maxVal, maxVal], color='0.75', linestyle='-')


    #### Set Axis Labels ####
    PYLAB.ylabel(ARCPY.GetIDMessage(84330), fontproperties = REPORT.ssLabFont, 
                 labelpad = 20)
    PYLAB.xlabel(ARCPY.GetIDMessage(84329), fontproperties = REPORT.ssLabFont, 
                 labelpad = 20)
    gridPlot.yaxis.grid(True, linestyle='-', which='major', color='lightgrey',
                        alpha=0.5)
    REPORT.setTickFontSize(gridPlot)

    #### Scoot Max/Min F and Groups ####
    minMaxF = list(minFVals) + list(maxFVals)
    minF, maxF = UTILS.increaseMinMax(minMaxF, multiplier = .15)
    minG, maxG = UTILS.increaseMinMax(groupList, multiplier = .15)
    PYLAB.ylim(ymin = minF, ymax = maxF)
    PYLAB.xlim(xmin = minG, xmax = maxG)

    #### Create Legend ####
    legLab = ARCPY.GetIDMessage(84415)
    grid.writeCell((startRow, 20), legLab,  fontObj = REPORT.ssBoldFont, 
                   justify = "left")
    labels = [ARCPY.GetIDMessage(84413), ARCPY.GetIDMessage(84261),
              ARCPY.GetIDMessage(84414), ARCPY.GetIDMessage(84412)]

    gridCount = 0
    colors = ['0.75', 'b', 'r', '0.75']
    markers = ['-', 'o', 'D', '-']
    for ind, lab in enumerate(labels):
        color = colors[ind]
        marker = markers[ind]
        row = ind + 1 + startRow
        gridCount += 1
        gridLegend = PLT.subplot2grid(grid.gridInfo, (row, 20))
        if ind in [1,2]:
            x = 0.0
            y = 0.0
            PLT.plot(x, y, color = color, marker = marker, alpha = .7)
        else:
            x = [0.0, 1.0]
            y = [0.0, 0.0]
            PLT.plot(x, y, color = color, linestyle = marker, alpha = .7)

        #### Add Points/Lines ####
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
    peakLab = ARCPY.GetIDMessage(84416).format(ARCPY.GetIDMessage(84261))
    gridLegend = PLT.subplot2grid(grid.gridInfo, (currentRow, 21))
    PLT.text(0.0, 0.3, peakLab, fontproperties = REPORT.ssFont, 
             horizontalalignment = "left")
    REPORT.clearGrid(gridLegend)

    #### Add To PDF ####
    report.write(pdfOutput)

    #### Create Table ####
    title = ARCPY.GetIDMessage(84411)
    report = REPORT.startNewReport(5, title = title, landscape = True,
                                   titleFont = REPORT.ssTitleFont)
    grid = report.grid

    #### Add Labels ####
    colLabs = [ARCPY.GetIDMessage(84329), ARCPY.GetIDMessage(84261),
               ARCPY.GetIDMessage(84412), ARCPY.GetIDMessage(84413),
               ARCPY.GetIDMessage(84414)] 
    for ind, label in enumerate(colLabs):
        if ind == 0:
            justify = "left"
        else:
            justify = "right"
        grid.writeCell((grid.rowCount, ind), label, 
                        fontObj = REPORT.ssBoldFont, justify = justify)
    grid.stepRow()

    #### Add Values ####
    for ind, group in enumerate(groupList):
        meanVal = UTILS.formatValue(meanFVals[ind], "%0.4f")
        minVal = UTILS.formatValue(minFVals[ind], "%0.4f")
        maxVal = UTILS.formatValue(maxFVals[ind], "%0.4f")
        medVal = UTILS.formatValue(medians[ind], "%0.4f")
        grid.writeCell((grid.rowCount, 0), str(group), 
                        justify = "left")
        grid.writeCell((grid.rowCount, 1), meanVal, 
                        justify = "right")
        grid.writeCell((grid.rowCount, 2), minVal, 
                        justify = "right")
        grid.writeCell((grid.rowCount, 3), maxVal, 
                        justify = "right")
        grid.writeCell((grid.rowCount, 4), medVal, 
                        justify = "right")
        grid.stepRow()

    grid.finalizeTable()
    report.write(pdfOutput)

    #### Finish Up ####
    pdfOutput.close()

def summarizeFStatsSpatial(fStatRes, groupList):
    maxInd = fStatRes.argmax()
    maxFStat = fStatRes[maxInd]
    maxGroup = groupList[maxInd]
    maxFOut = UTILS.formatValue(maxFStat, "%0.4f")
    maxVals = (numSep, maxGroup, maxFOut)
    ARCPY.AddMessage("\n"+ARCPY.GetIDMessage(84405).format(*maxVals))

    return maxInd, maxGroup, maxFStat

def summarizeFStats(fStatRes, groupList):
    #### Get Message ####
    msg = ARCPY.GetIDMessage(84408)

    #### Maximum Mean ####
    meanFVals = fStatRes.mean(1)
    maxInd = meanFVals.argmax()
    maxFStat = meanFVals[maxInd]
    maxMeanValOut = UTILS.formatValue(maxFStat, "%0.4f")
    maxGroup = groupList[maxInd]
    rowRes = (ARCPY.GetIDMessage(84261), numSep, maxGroup, maxMeanValOut)
    ARCPY.AddMessage("\n"+msg.format(*rowRes))

    #### Maximum Min ####
    minFVals = fStatRes.min(1)
    maxMinInd = minFVals.argmax()
    maxMinVal = minFVals[maxMinInd]
    maxMinValOut = UTILS.formatValue(maxMinVal, "%0.4f")
    rowRes = (ARCPY.GetIDMessage(84412), numSep, groupList[maxMinInd], maxMinValOut)
    ARCPY.AddMessage(msg.format(*rowRes))

    #### Maximum Max ####
    maxFVals = fStatRes.max(1)
    maxMaxInd = maxFVals.argmax()
    maxMaxVal = maxFVals[maxMaxInd]
    maxMaxValOut = UTILS.formatValue(maxMaxVal, "%0.4f")
    rowRes = (ARCPY.GetIDMessage(84413), numSep, groupList[maxMaxInd], maxMaxValOut)
    ARCPY.AddMessage(msg.format(*rowRes))

    #### Maximum Median ####
    medianList = [ STATS.median(i) for i in fStatRes ]
    maxMedInd = NUM.argmax(medianList)
    maxMedVal = medianList[maxMedInd]
    maxMedValOut = UTILS.formatValue(maxMedVal, "%0.4f")
    rowRes = (ARCPY.GetIDMessage(84414), numSep, groupList[maxMedInd], maxMedValOut)
    ARCPY.AddMessage(msg.format(*rowRes))

    return maxInd, maxGroup, maxFStat

if __name__ == "__main__":
    setupPartition()


