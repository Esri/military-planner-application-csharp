"""
Source Name:   SSUtilities.py
Version:       ArcGIS 10.1
Author:        Environmental Systems Research Institute Inc.
Description:   Utility Functions for ESRI Script Tools as well as users for their own
               scripts.
"""

################### Imports ########################
import os as OS
import sys as SYS
import numpy as NUM
import numpy.random as RAND
import math as MATH
import arcgisscripting as ARC
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.da as DA
import arcpy.sa as SA
import arcpy.analysis as ANA
import ErrorUtils as ERROR
import SSDataObject as SSDO
import WeightsUtilities as WU
import Stats as STATS
import locale as LOCALE
import gapy as GAPY
LOCALE.setlocale(LOCALE.LC_ALL, '')

###### Dictionary Mappings For Various Scripts ######

convertType = {'SmallInteger': 'SHORT',
                'Integer': 'LONG',
                'String': 'TEXT',
                'Single': 'FLOAT',
                'Double': 'FLOAT',
                'Date': 'DATE'}

convertTypeOut = {'SmallInteger': 'SHORT',
                'Integer': 'LONG',
                'String': 'TEXT',
                'Single': 'FLOAT',
                'Double': 'DOUBLE',
                'Date': 'DATE'}

numpyConvert = {'SmallInteger': int,
                'Integer': int,
                'Single': float,
                'Double': float,
                'Date': float,
                'String': 'U%i'}

nullTypes = [ "", None ]

renderType = {'POINT': 0, 'MULTIPOINT': 0,
              'POLYLINE': 1, 'LINE': 1,
              'POLYGON': 2}

distUnitTypes = {'UNKNOWN': 0, 'INCHES': 1, 'POINTS': 2, 'FEET': 3,
                 'YARDS': 4, 'MILES': 5, 'NAUTICAL MILES': 6,
                 'MILLIMETERS': 7, 'CENTIMETERS': 8, 'METERS': 9,
                 'KILOMETERS': 10, 'DECIMAL DEGREES': 11, 'DECIMETERS': 12}

###### NULL Value for Shapefiles Set to -DBL_MAX ######
shpFileNull = {'FLOAT': NUM.float32(-3.4028235e+38),
               'DOUBLE': NUM.float64(-1.7976931348623158e+308),
               'LONG': NUM.int(-(SYS.maxint+1)),
               'SHORT': NUM.int(-32768),
               'TEXT': "",
               'DATE': ""}

######################### General Functions ###########################

def returnDecimalChar():
    """Returns the decimal character based on the locale settings.
    """
    s = LOCALE.localeconv()
    return s['decimal_point']

def standardDistanceCutoff(xyCoords, stdDeviations = 1.0):
    """Returns the unweighted standard distance for a set of points.

    INPUTS:
    xyCoords (array) nx2 set of xy coordinates
    stdDeviations {float, 1.0}: number of standard devs around center
    """

    meanCenter = xyCoords.mean(0)
    devXY = xyCoords - meanCenter
    sigXY = (devXY**2.0).mean(0)
    return MATH.sqrt(sigXY.sum())

def maxDistanceCutoff(ssdo):
    """Returns the unweighted standard distance for a set of points.

    INPUTS:
    ssdo (class) instance of SSDataObject (Data Obtained)
    """

    nRatio = ssdo.numObs * .68
    maxNumNeighs = WU.maxDefaultNumNeighs
    if nRatio < maxNumNeighs:
        #### If 68% of N is Less than 500, Use One Standard Distance ####
        maxDist = standardDistanceCutoff(ssdo.xyCoords)
    else:
        #### Use Near Tool to Find Distance that Contains 500 from MC ####
        xyCoords = ssdo.xyCoords
        meanCenter = xyCoords.mean(0)
        x,y = meanCenter
        outArray = NUM.array([(1, (x, y))],
                             NUM.dtype([('idfield', NUM.int32),
                                        ('XY', '<f8', 2)]))
        meanFC = "in_memory/meanCenterTemp"
        DA.NumPyArrayToFeatureClass(outArray, meanFC, ['XY'])

        nearTab = "in_memory/nearTabTemp"
        ANA.GenerateNearTable(meanFC, ssdo.inputFC, nearTab, "#",
                              "NO_LOCATION", "NO_ANGLE", "ALL",
                              maxNumNeighs)

        fieldNames = ['NEAR_DIST']
        distArray = DA.TableToNumPyArray(nearTab, fieldNames)
        maxDist = distArray['NEAR_DIST'].max()

        #### Clean Up ####
        passiveDelete(meanFC)
        passiveDelete(nearTab)

    return maxDist

def numCells(fullLength, cellLength):
    """Returns the number of rows/columns for a fishnet grid.

    INPUTS:
    fullLength (float): height/width of extent
    cellLength (float): length of a cell segment
    """

    return int(fullLength / cellLength) + 1

def createCutoffsStep(minDist, incDist, numInc):
    """Returns distance cutoffs for analysis based on starting distance.

    INPUTS:
    minDist (float): starting distance
    incDist (float): distance increment
    numInc (int): number of increments
    """

    cuts = [ ( (inc * incDist) + minDist ) for inc in xrange(numInc) ]
    return NUM.array(cuts)

def createCutoffsMaxDist(minDist, maxDist, numInc):
    """Returns distance cutoffs for analysis based on ending distance.

    INPUTS:
    maxDist (float): ending distance
    numInc (int): number of increments
    """

    spanDist = maxDist - minDist
    incDist = spanDist / (numInc * 1.0)
    return NUM.arange(minDist, maxDist, incDist)

def returnRasterName(path2Raster):
    """Returns a valid raster dataset path."""

    #### Validate Output Workspace ####
    ERROR.checkOutputPath(path2Raster)

    #### Create Path for Output FC ####
    outPath, outName = OS.path.split(path2Raster)
    outShortName, outExt = OS.path.splitext(outName)

    #### Get Output Name for SDE if Necessary ####
    baseType = getBaseWorkspaceType(outPath).upper()
    if baseType == 'REMOTEDATABASE':
        outName = outName.split(".")[-1]
    elif baseType == 'FILESYSTEM':
        outName = outShortName + ".tif"
    else:
        outName = outShortName

    return OS.path.join(outPath, outName)

def fc2DensityRaster(inputFC, outputRaster, varName = None,
                     boundaryFC = None, searchRadius = None):
    """Creates a IDW Raster Surface using HotSpot Results.

    INPUTS:
    hotSpotFC (str): path to hot spot results
    outputRaster (str): path to output raster
    boundaryFC {str}: path to masked polygon features
    searchRadius {float}: must be in map spatial ref units
    """

    envMask = ARCPY.env.mask
    if envMask:
        try:
            #### Make Sure Mask Exists in Data Frame ####
            descMask = ARCPY.Describe(envMask)
            boundaryFC = envMask
        except:
            pass

    #### Get Valid Output Raster Path ####
    outputRaster = returnRasterName(outputRaster)
    outPath, outName = OS.path.split(outputRaster)
    ScratchWSKernelDensity = funWithScratchWS(SA.KernelDensity, outPath)
    ScratchWSExtract = funWithScratchWS(SA.ExtractByMask, outPath)

    desc = ARCPY.Describe(inputFC)
    oldExtent = ARCPY.env.extent
    renderTypeOut = renderType[desc.ShapeType.upper()]
    if renderTypeOut:
        #### Polygon or Line ####
        createTempFC = returnScratchName("Point_TempFC")
        DM.FeatureToPoint(inputFC, createTempFC)
        ARCPY.env.extent = desc.extent
        outRastFull = ScratchWSKernelDensity(createTempFC, varName,
                                             "", searchRadius)
        if boundaryFC:
            maskFC = boundaryFC
        else:
            maskFC = inputFC
        outRast = ScratchWSExtract(outRastFull, maskFC)
        DM.Delete(createTempFC)
        ARCPY.env.extent = oldExtent
    else:
        outRast = ScratchWSKernelDensity(inputFC, varName, "", searchRadius)
        if boundaryFC:
            outRast = ScratchWSExtract(outRast, boundaryFC)
    outRast.save(outputRaster)

def funWithXYTolerance(functionName, distanceInfo):
    """Sets the spatial ref env setting for the given function.

    INPUTS:
    functionName (obj): function to call with given args and extent cleared
    distanceInfo (class): distance information object
    """

    def innerFunction(*args, **kw):
        xyTolerance2Set = distanceInfo.joinXYTolerance()
        xyTolerance2SetBack = ARCPY.env.XYTolerance
        ARCPY.env.XYTolerance = xyTolerance2Set
        returnValue = functionName(*args, **kw)
        ARCPY.env.XYTolerance = xyTolerance2SetBack
        return returnValue

    return innerFunction

def funWithSpatialRef(functionName, spatialRef, outputFC = None):
    """Sets the spatial ref env setting for the given function.

    INPUTS:
    functionName (obj): function to call with given args and extent cleared
    spatialRef (class): spatial reference object
    """

    def innerFunction(*args, **kw):
        spatialRef2Set = returnOutputSpatialRef(spatialRef,
                                             outputFC = outputFC)
        spatialRef2SetBack = ARCPY.env.outputCoordinateSystem
        ARCPY.env.outputCoordinateSystem = spatialRef2Set
        returnValue = functionName(*args, **kw)
        ARCPY.env.outputCoordinateSystem = spatialRef2SetBack
        return returnValue

    return innerFunction

def funWithScratchWS(functionName, workspace):
    """Sets the spatial ref env setting for the given function.

    INPUTS:
    functionName (obj): function to call with given args and extent cleared
    workspace (class): path to scratch workspace
    """

    def innerFunction(*args, **kw):
        userWS2SetBack = ARCPY.env.scratchWorkspace
        ARCPY.env.scratchWorkspace = workspace
        returnValue = functionName(*args, **kw)
        ARCPY.env.scratchWorkspace = userWS2SetBack
        return returnValue

    return innerFunction

def getNumericParameter(paramNum):
    """Obtains "optional" Float and Int parameters.

    INPUTS:
    paramNum (int): parameter number

    RETURN (float/int, None): parameter value if set, None otherwise.
    """

    value = ARCPY.GetParameter(paramNum)
    if compareFloat(value, 0.0):
        strValue = ARCPY.GetParameterAsText(paramNum)
        if strValue == "#" or strValue == "":
            value = None

    return value

def getTextParameter(paramNum, fieldName = False):
    """Obtains "optional" Field Parameters.

    INPUTS:
    paramNum (int): parameter number

    RETURN (float/int, None): parameter value if set, None otherwise.
    """

    value = ARCPY.GetParameterAsText(paramNum)
    if fieldName:
        value = value.upper()
    if value == "#" or value == "":
        value = None

    return value

def openFile(fileName, ioString = "r"):
    """Wraps Python's File IO Pointer with ArcGIS Errors.

    INPUTS:
    fileName (str): path to the file
    ioSTring (str): io descriptor, e.g. "r", "rb", "wb"...

    RETURN:
    f (object): Python's IO File Pointer
    """

    try:
        return open(fileName, ioString)
    except:
        if ioString[0] == "r":
            ARCPY.AddIDMessage("ERROR", 110, fileName)
            raise SystemExit()
        else:
            ARCPY.AddIDMessage("ERROR", 210, fileName)
            raise SystemExit()

def setRandomSeed():
    """Sets the random number generator seed based on environment settings."""

    randomObj = ARCPY.env.randomGenerator.exportToString()
    seedInt = int(randomObj.split()[0])
    if seedInt:
        RAND.seed(seedInt)

def getZMInfo():
    """Returns the info for Z and M values from the environment settings.

    return (tuple): (mEnabledBool, zEnabledBool, zDefaultValue)
    """

    zEnabled = ARCPY.env.outputZFlag.upper()
    mEnabled = ARCPY.env.outputMFlag.upper()
    zDefault = ARCPY.env.outputZValue

    return (zEnabled, mEnabled, zDefault)

def setZMFlagInfo(hasM, hasZ, spatialRef):
    """Sets the flags for output M and Z and allows reset of default Z.

    INPUTS:
    hasM (bool): whether input has Z
    hasM (bool): whether input has M
    resetZ {float, None}: value to reset default Z environment variable

    OUTPUT:
    zFlag (str): either ENABLED or ""
    mFlag (str): either ENABLED or ""
    defaultZ (float): default Z value
    defaultM (float): default M value
    """

    #### Set Initial to DISABLED ####
    mFlag = "DISABLED"
    zFlag = "DISABLED"

    #### Get Env Settings ####
    zEnabled, mEnabled, zDefault = getZMInfo()

    #### Set MFlag ####
    if mEnabled == "SAME AS INPUT":
        if hasM:
            mFlag = "ENABLED"
    if mEnabled == "ENABLED":
        mFlag = mEnabled

    #### Set ZFlag ####
    if zEnabled == "SAME AS INPUT":
        if hasZ:
            zFlag = "ENABLED"
    if zEnabled == "ENABLED":
        zFlag = zEnabled

    #### Reset Default Z Value ####
    if hasattr(spatialRef, 'zdomain'):
        try:
            zDomain = spatialRef.zdomain
            if isinstance(zDomain, unicode):
                zDomain = str(zDomain)
            zMin, zMax = [LOCALE.atof(i) for i in zDomain.split()]
            defaultZ = setDefaultValue(zDefault, zMin, zMax)
        except:
            defaultZ = 0.0
    else:
        defaultZ = 0.0

    return zFlag, mFlag, defaultZ

def setDefaultValue(defaultValue, minValue, maxValue):
    """Used to assign default Z and M values.

    INPUTS:
    defaultValue (float): default value to set
    minValue (float): minimum value allowed
    maxValue (float): maximum value allowed

    RETURN (float): default value if between min/max, else min value
    """

    if defaultValue in ["", "#", None]:
        defaultValue = 0.0
    if (minValue < defaultValue <= maxValue):
        return defaultValue
    else:
        return minValue

def clearExtent(functionName):
    """Clears the extent env setting for the given function.

    INPUTS:
    functionName (obj): function to call with given args and extent cleared
    """

    def innerFunction(*args, **kw):
        oldExtent = ARCPY.env.extent
        ARCPY.env.extent = ""
        returnValue = functionName(*args, **kw)
        ARCPY.env.extent = oldExtent
        return returnValue

    return innerFunction

def createSeriesStr(xFields, yFields, outputTable):
    """Creates Graphing String for Line Series.

    INPUTS:
    xFields (list): list of fields names for x-axis
    yFields (list): list of fields names for y-axis
    outputTable (str): path to the data source

    OUTPUT:
    dataStr (str): series description string for DM.MakeGraph()
    """

    seriesStr = "SERIES=line:vertical"
    tabStr = "DATA=" + outputTable
    dataStr = []
    for ind, xField in enumerate(xFields):
        yField = yFields[ind]
        fieldStr = "X=" + xField + " " + "Y=" + yField
        lineStr = " ".join([ seriesStr, tabStr, fieldStr ])
        dataStr.append(lineStr)
    dataStr = ";".join(dataStr)
    return dataStr

def getImageDir():
    curdir = OS.path.dirname(__file__)
    imageDir = OS.path.join(curdir, "Images")
    return imageDir

def compareFloat(a, b, rTol = .00001, aTol = .00000001):
    """Uses the same formula numpy's allclose function:

    INPUTS:
    a (float): float to be compared
    b (float): float to be compared
    rTol (float): relative tolerance
    aTol (float): absolute tolerance

    OUTPUT:
    return (boolean): true if |a - b| < aTol + (rTol * |b|)
    """

    if abs(a - b) < aTol + (rTol * abs(b)):
        return True
    else:
        return False

def getExtent(extent, allValues = False):
    """Returns a list of coordinates for the given extent object.

    INPUTS:
    extent (object): instance of an extent object for ARCPY.Describe()
    allValues {bool, False}: when set to True returns M and Z values

    OUTPUT:
    extentList (list): [ xmin, ymin, xmax, ymax, {zmin, zmax, mmin, mmax} ]
    """

    extentList = [ extent.XMin, extent.YMin, extent.XMax, extent.YMax ]
    if allValues:
        mAndZ = [ extent.ZMin, extent.ZMax, extent.MMin, extent.MMax ]
        extentList = extentList + mAndZ

    return extentList

def increaseExtent(extent, multiplier = .4):
    """Increases the extent by the given multiplier.

    INPUTS:
    extent (object): instance of an extent object for ARCPY.Describe()
    multiplier {float, .4}: factor to increase extent

    OUTPUT:
    extentList (list): [ xmin, ymin, xmax, ymax,
                        {zmin, zmax, mmin, mmax} ]
    """

    xRange = extent.XMax - extent.XMin
    xRangeAmount = (xRange * multiplier) / 2.
    yRange = extent.YMax - extent.YMin
    yRangeAmount = (yRange * multiplier) / 2.
    XMin = extent.XMin - xRangeAmount
    YMin = extent.YMin - yRangeAmount
    XMax = extent.XMax + xRangeAmount
    YMax = extent.YMax + yRangeAmount

    return [ XMin, YMin, XMax, YMax ]

def increaseMinMax(values, multiplier = .05):
    """Increases the min/max of the values for plotting space.

    INPUTS:
    values (object): list/array of values
    multiplier {float, .05}: factor to increase by

    OUTPUT:
    minValuePlus, maxValuePlus
    """

    minValue = min(values)
    maxValue = max(values)
    valRange = maxValue - minValue
    rangeAmount = (valRange * multiplier) / 2.
    minValueMinus = minValue - rangeAmount
    maxValuePlus = maxValue + rangeAmount

    return minValueMinus, maxValuePlus

def increaseExtentByConstant(extent, constant):
    """Increases the extent by the given multiplier.

    INPUTS:
    extent (object): instance of an extent object for ARCPY.Describe()
    constant (float): number to increase the size of the extent

    OUTPUT:
    extentList (list): [ xmin, ymin, xmax, ymax, {zmin, zmax, mmin, mmax} ]
    """

    XMin = extent.XMin - constant
    YMin = extent.YMin - constant
    XMax = extent.XMax + constant
    YMax = extent.YMax + constant

    return [ XMin, YMin, XMax, YMax ]

def get92Extent(extent):
    """Returns a string representation of an extent (9.2 Version).

    INPUTS:
    extent (object): instance of an extent object for ARCPY.Describe()

    OUTPUT:
    return (str): "minX minY maxX maxY"
    """

    extent = getExtent(extent)
    extent = [ LOCALE.str(i) for i in extent ]

    return " ".join(extent)

def resetExtent(xyCoords, zCoords = None, mCoords = None):
    """Returns the extent of a feature class that honors both the
    environment settings and subselection as it is calculated after the
    read.

    INPUTS:
    xCoords (array): list of xCoords
    yCoords (array): list of yCoords
    zCoords {array, None}: list of zCoords
    mCoords {array, None}: list of mCoords

    OUTPUT:
    extent (object) instance of an extent object
    """

    XMin, YMin = xyCoords.min(0)
    XMax, YMax = xyCoords.max(0)
    ZMin = None
    ZMax = None
    MMin = None
    MMax = None
    if zCoords:
        ZMin = zCoords.min()
        ZMax = zCoords.max()
    if mCoords:
        MMin = mCoords.min()
        MMax = mCoords.max()

    extent = ARCPY.Extent(XMin, YMin, XMax, YMax, ZMin, ZMax, MMin, MMax)

    return extent

def compareSpatialRefNames(inRefName, outRefName):
    """Compares the names of two spatial reference names to warn the
    user if spatial references different for input and output
    coordinate system.

    INPUTS:
    inRefName (str): name of input spatial reference
    outRefName (str): name of output spatial reference
    """

    if inRefName != outRefName:
        ARCPY.AddIDMessage("WARNING", 984, inRefName, outRefName)

def returnOutputSpatialRef(inputSpatialRef, outputFC = None):
    """Returns a spatial reference object for output and analysis based
    on the hierarchical setting. (1)

    INPUTS:
    inputSpatialRef (obj): input spatial reference object
    outputFC (str): catalog path to the output feature class (2)

    OUTPUT:
    spatialRef (class): spatial reference object

    NOTES:
    (1) Hierarchy for Spatial Reference:
        Feature Data Set --> Environment Settings --> Input Feature Class
    (2) The outputFC can be an input feature for models with no feature
        class output.
    """

    if outputFC == None:
        spatialRef = setEnvSpatialReference(inputSpatialRef)
    else:
        dirName = OS.path.dirname(outputFC)
        descDir = ARCPY.Describe(dirName)
        dirType = descDir.DataType
        if dirType == "FeatureDataset":
            #### Set to FeatureDataset if True ####
            spatialRef = descDir.SpatialReference
        else:
            spatialRef = setEnvSpatialReference(inputSpatialRef)

    return spatialRef

def setEnvSpatialReference(inputSpatialRef):
    """Returns a spatial reference object of Env Setting if exists.

    INPUTS:
    inputSpatialRef (obj): input spatial reference object

    OUTPUT:
    spatialRef (class): spatial reference object
    """

    envSetting = ARCPY.env.outputCoordinateSystem
    if envSetting != None:
        #### Set to Environment Setting ####
        spatialRef = envSetting
    else:
        spatialRef = inputSpatialRef

    return spatialRef

def returnOutputSpatialString(spatialReference = None):
    """Returns the spatial reference string used in a Search Cursor or
    in a GA Table.

    INPUTS:
    spatialReference {obj, None}: spatial reference object

    OUTPUT:
    return (str): string version of spatial reference.
    """

    if spatialReference == None:
        return None
    else:
        return spatialReference.exportToString()

def getBasenamePrefix(fileName):
    """Returns the prefix for a filename based on the full path.

    INPUTS:
    fileName (str) full path to a file
    """

    baseName = OS.path.basename(fileName)
    try:
        baseName = baseName.split(".")[0]
    except:
        pass

    return baseName

def getCount(inputFC):
    """Wrapper function for returning the number of features in a
    feature class.

    INPUTS:
    inputFC (str): path to the input feature class

    OUTPUT:
    return (int): number of features in inputFC
    """

    clearObject = clearExtent(DM.GetCount)
    countObject = clearObject(inputFC)

    return int(countObject.getOutput(0))

def addColon(st):
    """Appends a colon and space to the specified string.

    INPUTS:
    st (str): string to append ': ' to
    """

    return st + ": "

def padValue(nonPVal, significant = False):
    """Appends empty space on value if p-values in column are significant.

    INPUTS:
    nonPVal (str): value already formatted to be placed in text table.
    significant {bool, False}: significant p-values in column?
    """

    if significant:
        nonPVal += " "
    return nonPVal

def writePVal(pVal, cutoff = 0.05, significant = "*",
              formatStr = "%0.6f", padNonSig = False):
    """Localizes a probability value from a floating point number
    and appends a * if the value is less than or equal to 0.05.

    INPUTS:
    pVal (float): probability value
    cutoff {float, 0.05}: significance cutoff
    significant {str, *}: symbol used to indicate significance
    formatStr {str, "%0.6f"}: format string, E.g. "%0.6f"
    padNonSig {bool, False}: pad empty space if not significant?
    """

    if NUM.isnan(pVal):
        strPVal = "NaN"
    else:
        strPVal = formatValue(pVal, formatStr = formatStr)
        if pVal <= cutoff:
            strPVal += significant
        else:
            if padNonSig:
                strPVal += " "

    return strPVal

def formatValue(value, formatStr = "%0.6f"):
    """Returns a NaN or formatted string for a given value.

    INPUTS:
    value (float): value to format
    formatStr (str): format string, E.g. "%0.6f"
    """

    if NUM.isnan(value):
        return "NaN"
    else:
        return LOCALE.format(formatStr, value)

def returnPeakIndices(values, levelFilter = None):
    """Returns the indices of first and maximum peak of a given set of
    values.

    INPUTS:
    values (list): values to be analyzed.
    levelFilter (float): filter values below this.

    RETURN:
    firstPeakIndex, maxPeakIndex
    """

    aVals = NUM.array(values)
    diff = aVals[1:] - aVals[0:-1]
    peakVals = []
    peakInds = []
    firstInd = None
    maxInd = None
    c = 0
    goneUp = False
    for d in diff:
        if d > 0:
            goneUp = True
        upBool = (d < 0 and goneUp)
        if levelFilter != None:
            upBool = (upBool and aVals[c] > levelFilter)
        if upBool:
            peakVals.append(aVals[c])
            peakInds.append(c)
        c += 1

    if len(peakVals):
        firstInd = peakInds[0]
        maxPeakIndTemp = NUM.argmax(peakVals)
        maxInd = peakInds[maxPeakIndTemp]

    return firstInd, maxInd

def returnMoranBin(zScore, featureVal, globalMean, localMean):
    """Returns a string representation of Local Moran's I
    Cluster-Outlier classification bins.

    INPUTS:
    zScore (float): standard z-score for specific feature.
    featureVal (float): the value for the specific feature.
    globalMean (float): mean value for all features.
    localMean (float): mean value for specific feature's neighbors.

    OUTPUT:
    moranBin (str): HH = Cluster of Highs, L = Cluster of Lows,
                    HL = High Outlier, LH = Low Outlier.
    """

    if abs(zScore) < 1.96:
        moranBin = ""
    else:
        if zScore > 1.96:
            if localMean >= globalMean:
                moranBin = "HH"
            else:
                moranBin = "LL"
        else:
            if featureVal >= globalMean and localMean <= globalMean:
                moranBin = "HL"
            elif featureVal <= globalMean and localMean >= globalMean:
                moranBin = "LH"
            else:
                moranBin = ""

    return moranBin

def returnScratchWorkSpace():
    """Returns the Scratch Temp Workspace for Intermediate Computation.

    OUTPUT:
    scratchWS (str): path to the scratch workspace
    """

    scratchWS = ARCPY.env.scratchWorkspace
    if not scratchWS:
        scratchWS = ARCPY.GetSystemEnvironment("TEMP")

    scratchExists = ARCPY.Exists(scratchWS)
    if not scratchExists:
        scratchWS = ARCPY.GetSystemEnvironment("TEMP")
        tempExists = ARCPY.Exists(scratchWS)
        if not tempExists:
            scratchWS = ARCPY.GetSystemEnvironment("CWD")

    return scratchWS

def returnScratchName(prefix, fileType = "FEATURECLASS",
                      scratchWS = None, extension = None):
    """Returns a Scratch File Name for Intermediate Computation. (1)

    INPUTS:
    prefix (str): file prefix
    fileType {str, FEATURECLASS}: type of scratch file
    scratchWS {str, NONE}: path to the scratch workspace desired
    extension {str, None}: extension for the file

    OUTPUT:
    scratchName (str): path to the scratch file

    NOTES:
    (1) This method supports all the file types (dataType) set out by
        ARCPY.CreateScratchName().  The '.dbf' or 'shp' extensions are
        resolved based on the location.  The "TEXT" option has been
        added and uses the ARCPY.CreateUniqueName() method.  The extension
        option is ignored for all dataTypes except for "TEXT";  It will
        be dropped as well if the workspace is not a "Folder".
    """

    #### Set Workspace ####
    if not scratchWS:
        scratchWS = returnScratchWorkSpace()
    descWS = ARCPY.Describe(scratchWS)
    baseType = descWS.DataType

    #### Remove Any Extension From Prefix ####
    prefix = OS.path.splitext(prefix)[0]

    #### Solve Based on File Type ####
    fileType = fileType.upper()
    if fileType == "TEXT":
        if baseType.upper() == "FOLDER":
            if extension:
                extension = "." + extension.strip(".")
                scratchName = prefix + extension.lower()
                scratchName = ARCPY.CreateUniqueName(scratchName,
                                                   scratchWS)
            else:
                scratchName = ARCPY.CreateUniqueName(prefix, scratchWS)
        else:
            scratchName = ARCPY.CreateUniqueName(prefix, scratchWS)

    else:
        scratchName = ARCPY.CreateScratchName(prefix, "", fileType, scratchWS)
        if baseType.upper() == "FOLDER":
            if fileType == "TABLE":
                scratchName += ".dbf"
        else:
            scratchName = scratchName.strip(".shp")

    return scratchName

def getBaseWorkspaceType(dirName, workType = None,
                         isBottom = True):
    """
    Returns the workspace type of the given directory. (1)

    INPUTS:
    dirName (str): base directory for input feature class.
    workType {str, None}: Set to None until a value is found.
    isBottom {bool, True}: Set to True for the first call.

    OUTPUT:
    dirType (str): FileSystem, LocalDatabase or RemoteDatabase.

    NOTES:
    (1) This function should be called with 'workType' and 'isBottom'
        set to their defaults.

        The recursive nature of the function makes it robust to feature
        data sets, where a describe on the workspace type will not
        be valid.
    """

    if dirName.upper().count(".SDE") > 0:
        return "RemoteDatabase"
    if workType:
        return workType
    else:
        if not isBottom:
            dirName = OS.path.dirname(dirName)
        desc = ARCPY.Describe(dirName)
        try:
            workType = desc.WorkspaceType
        except:
            workType = None
        return getBaseWorkspaceType(dirName, workType = workType,
                                    isBottom = False)

def getBaseFolder(dirName):
    """
    Walks up the file system until a folder is found. (1)

    INPUTS:
    dirName (str): base directory for input feature class.

    OUTPUT:
    folderPath (str): path to the first folder found in walk.

    NOTES:
    (1) This method will walk up a directory structure until a FOLDER is
        encountered.  It is used for files that should NOT be written to
        geodatabases and feature datasets... I.e. image and text files.
    """

    flag = True
    while flag:
        descWS = ARCPY.Describe(dirName)
        if descWS.DataType.upper() == "FOLDER":
            flag = False
        else:
            dirName = OS.path.dirname(dirName)
    return dirName

###### Functions for Creating/Adding Fields and Feature Classes #####

def addEmptyField(outputFC, field, type, alias = None, nullable = True,
                  precision = None, scale = None, length = None,
                  required = False, domain = None):
    """Adds an empty field to a FC with the approporiate defaults.

    INPUTS:
    outputFC (str): catalogue path to the output feature class.
    field (str): name of the field to be added.
    type (str): {LONG, SHORT, TEXT, FLOAT etc...}.
    length {float, None}: length of output field
    alias {str, None}: alias to be used for the field (Optional).
    """
    if nullable:
        nullString = "NULLABLE"
    else:
        nullString = "NON_NULLABLE"

    if required:
        requiredString = "REQUIRED"
    else:
        requiredString = "NON_REQUIRED"

    try:
        DM.AddField(outputFC, field, type, precision, scale, length,
                    alias, nullString, requiredString, domain)
    except:
        ARCPY.AddIDMessage("ERROR", 852, field, outputFC)

def returnTableName(tableName, extension = ".dbf"):
    """Assesses the filesystem assoctiaed with the table.  This enables the
    table to be overwritten.  A DBF extension is added if the file system is
    merely a folder.

    INPUTS:
    tableName (str): catalogue path to output table
    extension {str, .dbf}: file extension
    """

    #### Assure Output Workspace Exists ####
    ERROR.checkOutputPath(tableName)

    #### Assess Table Extension ####
    dbf = 0
    if extension not in OS.path.basename(tableName):
        tableDirInfo = ARCPY.Describe(OS.path.dirname(tableName))
        try:
            workType = tableDirInfo.WorkspaceType == "FileSystem"
            if workType:
                tableName = tableName + extension
                dbf = 1
        except:
            pass

    return tableName, dbf

def createOutputTable(tableName, fields, types, data, aliases = None):
    """Creates output data tables (E.g. dbf).

    INPUTS:
    tableName (str): catalogue path to output table
    fields (list): list of field names
    types (list): list of data types
    data (list of lists): column data in list form (1)

    NOTES:
    (1) Each list contains the data for the corresponding column
        represented by its index in fields.
    """

    #### Finalize Table Name ####
    tableName, dbf = returnTableName(tableName)
    try:
        OS.remove(tableName)
    except:
        pass

    path, base = OS.path.split(tableName)
    DM.CreateTable(path, base)

    #### Add Empty Fields ####
    checkNulls = OS.path.splitext(tableName)[-1].upper() == ".DBF"
    nullFieldsToCheck = {}
    for fieldInd, fieldName in enumerate(fields):
        fieldType = types[fieldInd]
        try:
            alias = aliases[fieldInd]
        except:
            alias = None
        if fieldType != "TEXT":
            nullFieldsToCheck[fieldInd] = shpFileNull[fieldType]
        addEmptyField(tableName, fieldName, fieldType, alias = alias)

    #### Add Data ####
    insert = DA.InsertCursor(tableName, fields)
    for row in data:
        #### Account for Nulls ####
        if checkNulls:
            if isinstance(row, tuple):
                rowResults = list(row)
            else:
                rowResults = row
            for ind, value in nullFieldsToCheck.iteritems():
                if NUM.isnan(rowResults[ind]):
                    rowResults[ind] = value
            insert.insertRow(rowResults)
        else:
            insert.insertRow(row)

    #### Clean Up ####
    ARCPY.AddMessage(tableName)
    del insert

def isShapeFile(inputFC):
    """Returns whether the input feature class is a shapefile.

    INPUTS:
    inputFC (str): catalogue path to the feature class

    OUTPUT:
    return (bool): is the inputFC a shapefile?
    """

    shpFileBool = False
    baseFile = OS.path.basename(inputFC)
    try:
        splitBase = baseFile.split(".")
        if splitBase[-1].upper() == "SHP":
            shpFileBool = True
    except:
        pass

    return shpFileBool

def isNullable(inputFC):
    """Returns whether fields from input can be Nullable. (1)

    INPUTS:
    inputFC (str): catalogue path to the feature class or table

    OUTPUT:
    return (bool): do added fields honor nullable flag?
    """

    inPath, inFile = OS.path.split(inputFC)
    wsType = getBaseWorkspaceType(inPath)
    return wsType.upper() in ["LOCALDATABASE", "REMOTEDATABASE"]

def setToNullable(inputFC, outputFC):
    """Returns whether fields copied from input should be set to Nullable. (1)

    INPUTS:
    inputFC (str): catalogue path from the input feature class
    outputFC (str): catalogue path to the output feature class

    OUTPUT:
    return (bool): should copied fields be set to nullable?

    NOTES:
    (1) When copied fields come from a feature class that is inherently
        non-nullable (E.g. shapefile, coverage), then they should be set to
        nullable when going to fgdb, pgdb or sde.  More importantly, when
        copying the fields from one nullable FC to another, you should honor
        the field specific nullable flag.  Return
    """

    inPath, inFile = OS.path.split(inputFC)
    inType = getBaseWorkspaceType(inPath)
    inBool = inType.upper() in ["LOCALDATABASE", "REMOTEDATABASE"]

    outPath, outFile = OS.path.split(outputFC)
    outType = getBaseWorkspaceType(outPath)
    outBool = outType.upper() in ["LOCALDATABASE", "REMOTEDATABASE"]

    return (inBool and outBool) == False

def returnOutputFieldName(inFCField):
    """Returns a valid output field name from a given input field object. (1)

    INPUTS:
    inFCField (obj): instance of SSDO.FCField()

    OUTPUT:
    outFieldName (str): output field name

    NOTES:
    (1) Honors Fully Qualified Field Names Env Setting in the case of joins.
    If the Env Setting is True, then returns the field name, else it returns
    the baseName.
    """

    if ARCPY.env.qualifiedFieldNames:
        outFieldName = inFCField.name
    else:
        outFieldName = inFCField.baseName

    return outFieldName

def validQFieldName(inFCField, outPath):
    """Returns a valid and qualified field name.

    INPUTS:
    inFCField (obj): instance of SSDO.FCField()
    outPath (str): path to the output feature class

    OUTPUT:
    outFieldName (str): output field name
    """

    if ARCPY.env.qualifiedFieldNames:
        outFieldName = ARCPY.ValidateFieldName(inFCField.name, outPath)
    else:
        outFieldName = ARCPY.ValidateFieldName(inFCField.baseName, outPath)

    return outFieldName

def getFieldNames(fieldNames, outPath):
    """Returns a valid and qualified field names from a list of strings.

    INPUTS:
    fieldNames (list): field names to validate
    outPath (str): path to the output feature class

    RETURN: (list): validated field names
    """

    return [ARCPY.ValidateFieldName(i, outPath) for i in fieldNames]

def caseValue2Print(caseValue, caseFieldIsString):
    """Returns a version of the case value that can be printed.

    INPUTS:
    caseValue (int, str, datetime): value from a case field
    caseFieldIsString (bool): whether the case field is of type str

    RETURN: (str): string rep of a case value
    """

    if not caseFieldIsString:
        caseValue = str(caseValue)

    return caseValue

def createAppendFieldNames(fieldNames, outPath):
    """Creates unique field names for appended fields from input. (1)

    INPUTS:
    fieldNames (list): name of input fields that are to be appended
    outPath (str): path to the output feature class

    OUTPUT:
    appendNames (list): output field names for appended fields from input

    NOTES:
    (1) Honors Fully Qualified Field Names Env Setting in the case of joins.
    """

    #### Assess Whether Output is ShapeFile ####
    descWS = ARCPY.Describe(outPath)
    baseType = descWS.DataType
    if outPath == "in_memory":
        maxLen = 64
    else:
        isShapeFile = baseType.upper() == "FOLDER"
        if isShapeFile:
            maxLen = 10
        else:
            maxLen = 32

    #### Validate Field Names ####
    fieldNames = [ ARCPY.ValidateFieldName(i, outPath) for i in fieldNames ]

    #### Create Output Field Names ####
    appendNames = []

    #### Creates Unique Field Names ####
    for fieldName in fieldNames:
        fixedName = fieldName[:maxLen]
        idx = 1
        while fixedName in appendNames:
            suffix = "_%i" % idx
            lenSuff = len(suffix)
            fixedName = fixedName[:(maxLen - lenSuff)] + suffix
            idx += 1
        appendNames.append(fixedName)

    return appendNames

def createOutputFieldMap(inputFC, inFieldName, outFieldCandidate = None,
                         setNullable = False):
    """Creates a field map for use in feature class to feature class.

    INPUTS:
    inputFC (str): input feature class
    inFieldName (str): name of the field from inputFC to add
    outFieldCandidate {class, None}: instance of SSDO.CandiateField
    setNullable {bool, False}: set fields to nullable?

    OUTPUT:
    outFieldMap (obj): instance of ARCPY.FieldMap
    """

    #### Create Field Map from Input Feature Class ####
    outFieldMap = ARCPY.FieldMap()
    outFieldMap.addInputField(inputFC, inFieldName)

    #### Get Field Object ####
    outSource = outFieldMap.outputField

    #### Adjust Name, Alias and Type Based On Candidate Field ####
    if outFieldCandidate:
        outSource.name = outFieldCandidate.name
        outSource.aliasName = outFieldCandidate.alias
        try:
            outSource.type = convertTypeOut[outFieldCandidate.type]
        except:
            outSource.type = outFieldCandidate.type
        if outFieldCandidate.length:
            outSource.length = outFieldCandidate.length
        if outFieldCandidate.precision:
            outSource.precision = outFieldCandidate.precision

    #### Set Fields to Nullable if not from Database ####
    if setNullable:
        outSource.isNullable = True

    #### Resfresh the Field Object ####
    outFieldMap.outputField = outSource

    return outFieldMap

def passiveDelete(inputFC):
    """Passively tries to delete feature classes and layers.

    INPUTS:
    inputFC (str): path to the feature class or layer
    """

    try:
        DM.Delete(inputFC)
    except:
        pass

def readPolygonFC(inputFC, spatialRef = None, useGeodesic = False):
    """Reads a polygon feature class into a python dict.

    INPUTS:
    inputFC (str): catalogue path to the feature class
    spatialRef {str/obj, None}: output coordinate system projection
    useGeodesic (bool): return areas in geodesic meters?

    OUTPUT:
    polyDict (dict): [oid = list of xy-coordinates]
    polyArea (dict): [oid = area of polygon]
    """

    info = ARCPY.Describe(inputFC)
    oidName = info.oidFieldName
    fieldList = [oidName, "SHAPE@"]

    #### Process Field Values ####
    try:
        rows = DA.SearchCursor(inputFC, fieldList, "", spatialRef)
    except:
        ARCPY.AddIDMessage("ERROR", 204)
        raise SystemExit()

    polyDict = {}
    polyArea = {}
    for row in rows:
        oid, feature = row
        partCount = feature.partCount
        partNum = 0

        poly = []
        while partNum < partCount:
            part = feature.getPart(partNum)
            point = part.next()
            pointCount = 0

            while point:
                poly.append( (point.X, point.Y) )
                point = part.next()
                pointCount += 1

            partNum += 1

        polyDict[oid] = poly
        if useGeodesic:
            polyArea[oid] = feature.getArea('PRESERVE_SHAPE')
        else:
            polyArea[oid] = feature.area

    del rows

    return polyDict, polyArea

def createPolygonFC(outputFC, points, spatialRef = None):
    """Creates a polygon feature class from a set of points.

    INPUTS:
    outputFC (str): catalogue path to the feature class
    points (array): nx2 array of x,y coordinates
    spatialRef {str/obj, None}: output coordinate system projection
    """

    ARCPY.env.overwriteOutput = 1
    outPath, outName = OS.path.split(outputFC)
    outPolyFC = DM.CreateFeatureclass(outPath, outName, "POLYGON",
                                      "", "", "", spatialRef)
    outCursor = DA.InsertCursor(outputFC, ["SHAPE@"])
    polyArray = ARCPY.Array()
    for point in points:
        x, y = point
        pointOut = ARCPY.Point(x, y)
        polyArray.add(pointOut)
    addPoly = ARCPY.Polygon(polyArray)
    outCursor.insertRow([addPoly])

    del outCursor

def createLineFC(outputFC, points, spatialRef = None):
    """Creates a polygon feature class from a set of points.

    INPUTS:
    outputFC (str): catalogue path to the feature class
    points (array): nx2 array of x,y coordinates
    spatialRef {str/obj, None}: output coordinate system projection
    """

    ARCPY.env.overwriteOutput = 1
    outPath, outName = OS.path.split(outputFC)
    outPolyFC = DM.CreateFeatureclass(outPath, outName, "POLYLINE",
                                      "", "", "", spatialRef)
    outCursor = DA.InsertCursor(outputFC, ["SHAPE@"])
    c = 1
    for point in points[0:-1]:
        lineArray = ARCPY.Array()
        x0, y0 = point
        pointFrom = ARCPY.Point(x0, y0)
        x1,y1 = points[c]
        pointTo = ARCPY.Point(x1, y1)
        lineArray.add(pointFrom)
        lineArray.add(pointTo)
        addLine = ARCPY.Polyline(lineArray)
        outCursor.insertRow([addLine])
        c += 1

    del outCursor

def createPointFC(outputFC, points, spatialRef = None):
    """Creates a polygon feature class from a set of points.

    INPUTS:
    outputFC (str): catalogue path to the feature class
    points (array): nx2 array of x,y coordinates
    spatialRef {str/obj, None}: output coordinate system projection
    """

    ARCPY.env.overwriteOutput = 1
    outPath, outName = OS.path.split(outputFC)
    outPolyFC = DM.CreateFeatureclass(outPath, outName, "POINT",
                                      "", "", "", spatialRef)
    outCursor = DA.InsertCursor(outputFC, ["SHAPE@XY"])
    for point in points:
        outCursor.insertRow([point])

    del outCursor

def returnPolygon(polygonFC, spatialRef = None, useGeodesic = False):
    """Reads a polygon feature class and returns first geometry.

    INPUTS:
    polygonFC (str): catalogue path to the feature class
    spatialRef {str/obj, None}: output coordinate system projection
    useGeodesic (bool): return areas in geodesic meters?
    """

    polyInfo = readPolygonFC(polygonFC, spatialRef = spatialRef, 
                             useGeodesic = useGeodesic)
    polyDict, polyArea = polyInfo
    if not len(polyDict):
        return None, None
    else:
        oidPoly = polyDict.keys()[0]
        return polyDict[oidPoly], polyArea[oidPoly]

def chunk(values, chunkSize):
    """Groups a sequence into chunks of a given size.

    INPUTS:
    values (list): list of values
    chunkSize (int): number of values per chunk

    OUTPUT:
    contents (list): [ [chunk_1 of values] ... [chunk_k of values] ]
    """

    contents = []
    for value in values:
        contents.append(value)
        if len(contents) == chunkSize:
            yield contents
            contents = []
    if contents:
        yield contents

def sqlChunkStrings(inputFC, fieldName, chunks):
    """Creates a series of sql strings for selecting features in a
    feature class.

    INPUTS:
    inputFC (str): path to the input feature class.
    fieldName (str): field in the inputFC used for selection.
    chunks (list): [ [chunk_1 of values] ... [chunk_k of values] ] (1)

    OUTPUT:
    sqlStrings (list): list of sql strings for feature selection.

    NOTES:
    (1) The "chunks" argument is the result of the chunk function.
        In order for this function to work properly the input values for
        the chunk function must be sorted... however, it is OK to have
        missing values in the original sequence.
    """

    sqlStrings = []
    fieldString = ARCPY.AddFieldDelimiters(inputFC, fieldName)
    for chunk in chunks:
        minChunk = fieldString + " >= " + str(min(chunk))
        maxChunk = fieldString + " <= " + str(max(chunk))
        sqlValue = minChunk + " And " + maxChunk
        sqlStrings.append(sqlValue)

    return sqlStrings

######################## Table Printing ######################

def outputTextTable(x, justify = "left", header = "NULL", pad = 0):
    """Provides a table as a string for pretty printing. (1)

    INPUTS:
    x (list of lists): rows in tables
    justify {list/str, left}: justification of columns (2, 3)
    header {str, NULL}: header for your table
    pad {int, 0}: pads empty space between columns

    OUTPUT:
    result (str): table string to be printed to either ARCPY or the
                  interpreter.

    NOTES:
    (1) All rows must have the smae number of columns.
    (2) Choices: left, right, center
    (3) E.g. "right" = right justify all columns;
             ["left", "right"] left the first, right the second.
    """

    if type(x[0]) != list:
        x = [x]
    nRows = len(x)
    nCols = len(x[0])
    rangeCol = xrange(nCols)
    if type(justify) != list:
        justify = [ justify for i in rangeCol ]
    cLengths = [ 0 for i in rangeCol ]
    strList = []
    for l in x:
        stemp = [ str(item)
                  if not isinstance(item, basestring)
                  else item for item in l ]
        ltemp = [ len(item) for item in stemp]
        strList.append(stemp)
        c = 0
        for place in ltemp:
            if place > cLengths[c]:
                cLengths[c] = place
            c+=1
    final = []
    headerLength = sum(cLengths)
    for l in strList:
        newRow = []
        c = 0
        for item in l:
            ls = cLengths[c]
            frmt = justify[c]
            newString = returnAdjustedString(item,ls,frmt)
            newRow.append(newString)
            c+=1
        final.append(" ".join(newRow))
    table = "\n".join(final)
    if header != "NULL":
        header = returnAdjustedString(header,headerLength,"center")
        table = header + "\n" + table
    if pad == 1:
        table = "\n" + table + "\n"

    return table

def returnAdjustedString(xString, length, justify = "left"):
    """Returns string justifed with the appropriate amount of pad and to the
    correct anchor.

    INPUTS:
    xString (str): string to be formatted
    length (int): total length used to format and anchor
    justify {str, left}: location of anchor

    OUTPUT: res (str): formatted xString
    """

    if justify == "right":
        res = xString.rjust(length)
    elif justify == "center":
        res = xString.center(length)
    else:
        res = xString.ljust(length)

    return res

#################### Class Helper Functions ##################

def assignClassAttr(instanceOfClass, attributes):
    """Assigns self.attributes to given class.

    INPUTS:
    instanceOfClass (class): instance of a class
    attributes (dict): usually locals()
    """

    for key, value in attributes.iteritems():
        if key != 'self':
            setattr(instanceOfClass, key, value)

##################### Geometry Functions ######################

class Envelope(object):
    """Creates and study area envelope based on the given extent.

    INPUTS:
    extent (obj): instance of an extent object.

    ATTRIBUTES:
    envelope (list): [minX, minY, maxX, maxY]
    maxExtent (float): max length of extent
    minExtent (float): min length of extent
    extArea (float): area of envelope
    """

    def __init__(self, extent):
        self.envelope = getExtent(extent)
        lenX = abs(self.envelope[2] - self.envelope[0])
        lenY = abs(self.envelope[3] - self.envelope[1])
        self.minExtent, self.maxExtent = NUM.sort([lenX, lenY])
        self.extArea = self.minExtent * self.maxExtent
        sumExtent = self.maxExtent + self.minExtent
        self.tolerance = sumExtent * MATH.exp(-10.0)
        self.lenX = lenX
        self.lenY = lenY

class SpheroidSlice(object):
    """Creates and study area envelope based on the given extent.

    INPUTS:
    extent (obj): instance of an extent object.

    ATTRIBUTES:
    envelope (list): [minX, minY, maxX, maxY]
    maxExtent (float): max length of extent
    minExtent (float): min length of extent
    extArea (float): area of envelope
    """
    
    def __init__(self, extent, spatialRef):
        xMin, yMin, xMax, yMax = getExtent(extent)
        topX =  ARC._ss.chordal_dist(xMin, xMax, yMax, yMax, spatialRef)
        bottomX =  ARC._ss.chordal_dist(xMin, xMax, yMin, yMin, spatialRef)
        leftY =  ARC._ss.chordal_dist(xMin, xMin, yMin, yMax, spatialRef)
        rightY =  ARC._ss.chordal_dist(xMax, xMax, yMin, yMax, spatialRef)
        sortX = max(topX, bottomX)
        sortY = max(leftY, rightY)
        self.minExtent, self.maxExtent = NUM.sort([sortX, sortY])
        sumExtent = self.maxExtent + self.minExtent
        self.tolerance = sumExtent * MATH.exp(-10.0)
        self.topX = topX
        self.bottomX = bottomX
        self.leftY = leftY
        self.rightY = rightY

        #### Create Rough Estimate of Degrees to Meters ####
        diagChordal = ARC._ss.chordal_dist(xMin, xMax, yMax, yMin, spatialRef)
        diagEuc = ARC._ss.euclidean_dist(xMin, xMax, yMax, yMin)
        self.meters2DegreeRatio = diagEuc / diagChordal
        self.degrees2MeterRatio = diagChordal / diagEuc

        #### Max Neighborhood Search ####

class MinRect(object):
    """Creates and study area envelope based on the given extent.

    INPUTS:
    extent (obj): instance of an extent object.

    ATTRIBUTES:
    envelope (list): [minX, minY, maxX, maxY]
    maxExtent (float): max length of extent
    minExtent (float): min length of extent
    extArea (float): area of envelope
    """

    def __init__(self, minRectFC, spatialRef = None):
        self.minRectFC = minRectFC
        self.spatialRef = spatialRef
        self.parseInfo()

    def parseInfo(self):
        lf = ARCPY.ListFields(self.minRectFC, "MBG_Orientation")
        if len(lf):
            fieldList = ["SHAPE@", "MBG_Width",
                         "MBG_Length", "MBG_Orientation"]
        else:
            fieldList = ["SHAPE@", "MBG_Width",
                         "MBG_Length", "MBG_Orient"]
        rows = DA.SearchCursor(self.minRectFC, fieldList, "", self.spatialRef)
        polygon, width, length, orientation = rows.next()
        del rows
        self.width = width
        self.length = length
        self.orientation = orientation
        self.polygon = polygon
        self.area = polygon.area
        self.minLength, self.maxLength = NUM.sort([width, length])
        sumExtent = self.maxLength + self.minLength
        self.tolerance = sumExtent * MATH.exp(-10.0)

def convert2Radians(degree):
    """Converts degree to radians.

    INPUTS:
    degree (float): degree of angle

    RETURN (float): radians of angle
    """

    return NUM.pi / 180.0 * degree

def convert2Degree(radians):
    """Converts radians to degree.

    INPUTS:
    radians (float): radians of angle

    RETURN (float): degree of angle
    """

    return radians * (180.0 / NUM.pi)

def getAngle(numer, denom):
    """Calculates the angle for Used in the
    Linear Directional Mean Tool.

    INPUTS:
    numer (float): numerator
    denom (float): denominator
    """

    if denom == 0.0:
        #### 90 Degrees in Radians ####
        ratio = NUM.pi / 2.0
    elif numer == 0.0:
        #### 180 Degrees in Radians ####
        ratio = NUM.pi
    else:
        ratio = abs(NUM.arctan(numer / denom))

    #### Quadrant Adjustment ####
    if numer >= 0:
        if denom >= 0:
            #### X and Y Positive (First Quadrant) ####
            angle = ratio
        else:
            #### Special Case of Single Up Arrow ####
            if denom == -1.0:
                angle = ratio
            else:
                #### Y is Negative (Second Quadrant) ####
                angle = NUM.pi - ratio
    else:
        if denom < 0:
            #### X and Y Negative (Third Quadrant) ####
            angle = NUM.pi + ratio
        else:
            #### Y is Positive (Fourth Quadrant) ####
            angle = (2.0 * NUM.pi) - ratio

    return angle

def nearestPoint(studyAreaPoly, gaTable):
    """Code to perform NEAR functionality (1).

    INPUTS:
    studyAreaPoly (array): polygon boundary array
    gaTable (obj): GA Table containing feature centroids

    OUTPUT:
    nearDict (dict): [id = distance to nearest feature]
    nearXY (dict): [id = xy-coordinates to nearest feature]
    nextDict (dict): [id = distance to next nearest feature]

    NOTES:
    (1) Given a set of points and also points defining a study area, this tool
        returns for each point the shortest distance to the study area and the
        X/Y coordinate where that distance intersects the study area.
    """

    nearDict = {}
    nearXY = {}
    nextDict = {}
    N = len(gaTable)

    for i in xrange(N):
        row = gaTable[i]
        id = row[0]
        point = row[1]
        poly0 = studyAreaPoly[0]
        dist = []
        for poly1 in studyAreaPoly[1:]:
            deltaX = poly1[0] - poly0[0]
            deltaY = poly1[1] - poly0[1]
            delta1X = point[0] - poly0[0]
            delta1Y = point[1] - poly0[1]

            lenSq = ((poly0[0] - poly1[0])**2.0 + \
                    (poly0[1] - poly1[1])**2.0)

            if (lenSq == 0 or point == poly0):
                nearDict[id] = 0.0
                nearXY[id] = poly0
                distSq = 0.0

            else:
                #### Not Normalized ####
                dT = (deltaX * delta1X) + (deltaY * delta1Y)

                #### Nearest Relative to poly1 ####
                nearPointX = dT * deltaX
                nearPointY = dT * deltaY

                delta1X = (delta1X * lenSq - nearPointX)/lenSq
                delta1Y = (delta1Y * lenSq - nearPointY)/lenSq

                dT = dT / lenSq

                if dT <= 0.0:
                    nearPointX = poly0[0]
                    nearPointY = poly0[1]
                elif dT >= 1.0:
                    nearPointX = poly1[0]
                    nearPointY = poly1[1]
                else:
                    nearPointX = poly0[0] + (nearPointX / lenSq)
                    nearPointY = poly0[1] + (nearPointY / lenSq)

                #### Calculate Distance ####
                distSq = (nearPointX - point[0])**2.0 \
                         + (nearPointY - point[1])**2.0
                try:
                    if distSq < nearDict[id]:
                        nearDict[id] = distSq
                        nearXY[id] = (nearPointX, nearPointY)
                except:
                    nearDict[id] = distSq
                    nearXY[id] = (nearPointX, nearPointY)
            poly0 = poly1
            dist.append(distSq)

        nearDict[id] = MATH.sqrt(nearDict[id])
        dist.sort()
        nextDict[id] = MATH.sqrt(dist[1])

    return nearDict, nearXY, nextDict

def minBoundGeomPoints(xyCoords, outputFC,
                       geomType = "RECTANGLE_BY_AREA",
                       spatialRef = None):
    """Wraps the Minimum Bounding Geometry Tool for xy-coordinates. (1)

    INPUTS:
    xyCoords (array): xy-coordinates
    outputFC (str): path to the output feature class
    geomType {str, RECTANGLE_BY_AREA}: type of bounding geometry (2, 3)
    spatialRef {obj, None}: instance of a spatial reference object

    NOTES:
    (1) This tool is designed to always use the centroids of features for
        the minimum bounding geometry.  As such, the tool takes point
        coordinates that you have already read in, or points you have
        specified on the fly.
    (2) geomType {RECTANGLE_BY_AREA, RECTANGLE_BY_WIDTH, CONVEX_HULL,
                  CIRCLE, ELLIPSE, ENVELOPE}
    (3) You must have a professional license for all geomTypes except
        RECTANGLE_BY_AREA
    """

    pointList = []
    for x,y in xyCoords:
        newPoint = ARCPY.Point(x, y)
        geom = ARCPY.PointGeometry(newPoint, spatialRef)
        pointList.append(geom)

    DM.MinimumBoundingGeometry(pointList, outputFC, geomType, "ALL",
                               "", "MBG_FIELDS")

def minBoundGeomFC(inputFC, outputFC, geomType = "RECTANGLE_BY_AREA",
                   spatialRef = None):
    """Wraps the Minimum Bounding Geometry Tool for xy-coordinates.

    INPUTS:
    inputFC (array): input feature class
    outputFC (str): path to the output feature class
    geomType {str, RECTANGLE_BY_AREA}: type of bounding geometry (1, 2)
    spatialRef {obj, None}: instance of a spatial reference object

    NOTES:
    (1) geomType {RECTANGLE_BY_AREA, RECTANGLE_BY_WIDTH, CONVEX_HULL,
                  CIRCLE, ELLIPSE, ENVELOPE}
    (2) You must have a professional license for all geomTypes except
        RECTANGLE_BY_AREA
    """

    rows = DA.SearchCursor(inputFC, ["SHAPE@"], "", spatialRef)
    shapeList = []
    for row in rows:
        shapeList.append(row[0])

    del rows
    DM.MinimumBoundingGeometry(shapeList, outputFC, geomType, "ALL",
                               "", "MBG_FIELDS")

def setUniqueIDField(ssdo, weightsFile = None):
    """Sets the Unique ID Field for Global and Local Stats. (1)

    INPUTS:
    ssdo (class): instance of the SSDataObject
    weightsFile {str, None}: path to a spatial weights matrix file

    OUTPUT:
    masterField (str): name of the unique ID field

    NOTES:
    (1) If a spatial weights matrix file is used, then a warning will be
        provided if the spatial reference for the weights is different
        from the analysis dataset; an error will arise if the unique ID
        field for the weights matrix is not in the dataset.
    """

    if weightsFile:
        #### SWM or Text Formatted Spatial Weights ####
        weightSuffix = weightsFile.split(".")[-1].lower()
        swmFileBool = (weightSuffix == "swm")

        #### Validate Unique ID Field ####
        masterField, spatialRefName = WU.returnHeader(ssdo,
                                                      weightsFile,
                                                      swmFileBool)

        #### Warn if Different Spatial References Used ####
        if swmFileBool:
            WU.compareSpatialRefWeights(spatialRefName,
                                  ssdo.spatialRef.name)
    else:
        masterField = ssdo.oidName

    return masterField

######################## Other Classes #########################

class LocationInfo(object):
    """Returns Location Info such as Nearest Neighbor Distance and Outliers.

    INPUTS:
    ssdo (class): instance of SSDataObject
    concept {str, EUCLIDEAN}: EUCLIDEAN or MANHATTEN distance
    silentThreshold {bool, True}: whether to print warnings/errors
    stdDeviations {int, 3}: number of std dist deviations
    includeCoincident {bool, False}: whether to include zero NN distances
    """

    def __init__(self, ssdo, concept = "EUCLIDEAN", silentThreshold = False,
                 stdDeviations = 3, includeCoincident = False):

        #### Set Initial Attributes ####
        assignClassAttr(self, locals())
        self.initialize()

    def initialize(self):
        #### Set Progressor for Search ####
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84144))
        ssdo = self.ssdo

        #### Create k-Nearest Neighbor Search Type ####
        gaTable = ssdo.gaTable
        gaSearch = GAPY.ga_nsearch(gaTable)
        concept, gaConcept = WU.validateDistanceMethod(self.concept,
                                                    ssdo.spatialRef)
        gaSearch.init_nearest(0.0, 1, gaConcept)
        neighDist = ARC._ss.NeighborDistances(gaTable, gaSearch)
        N = len(gaTable)
        distances = NUM.empty((N, ), float)

        #### Find All Nearest Neighbor Distance ####
        for row in xrange(N):
            distances[row] = neighDist[row][1][0]
            ARCPY.SetProgressorPosition()

        #### Get Only Non-Zero Distances ####
        nonZeroDistanceInds = NUM.where(distances != 0.0)
        nonZeroDistances = distances[nonZeroDistanceInds]
        nonZeroMeanD = nonZeroDistances.mean()
        nonZeroStdD = nonZeroDistances.std()
        nonZeroMedD = STATS.median(nonZeroDistances)
        meanD = distances.mean()
        stdD = distances.std()
        medD = STATS.median(distances)
        if not self.includeCoincident:
            devDistances = (distances - nonZeroMeanD) / nonZeroStdD
            stdTest = nonZeroStdD
        else:
            devDistances = (distances - meanD) / stdD
            stdTest = stdD

        #### Calculate Threshold Distance with Spatial Outliers ####
        if self.stdDeviations and stdTest:
            #### Locational Outliers ####
            distances2Include = NUM.where(devDistances < self.stdDeviations)
            outliers = NUM.where(devDistances >= self.stdDeviations)[0]
            avgDist = distances[distances2Include].mean()
            threshold = distances[distances2Include].max()
            numOutliers = N - len(distances2Include[0])
            if not numOutliers:
                outliers = None

        else:
            avgDist = meanD
            threshold = distances.max()
            outliers = None
            numOutliers = 0
            distances2Include = None

        #### Increase For Rounding Error ####
        threshold = threshold * 1.0001

        #### Report Default Threshold ####
        thresholdStr = ssdo.distanceInfo.printDistance(threshold)

        #### Print Threshold Distance ####
        if not self.silentThreshold:
            ARCPY.AddIDMessage("WARNING", 853, thresholdStr)

        #### Clean Up ####
        del gaSearch

        self.threshold = threshold
        self.avgDist = avgDist
        self.medDist = medD
        self.nonZeroAvgDist = nonZeroMeanD
        self.nonZeroMedDist = nonZeroMedD
        self.distances = distances
        self.numOutliers = numOutliers
        self.outliers = outliers
        self.distances2Include = distances2Include
        self.devDistances = devDistances
        self.nonZeroDistances = nonZeroDistances

    def printOutlierInfo(self):
        msg = ARCPY.GetIDMessage(84435)
        ARCPY.AddMessage(msg.format(self.numOutliers, self.stdDeviations))
        if self.numOutliers != 0:
            msg = ARCPY.GetIDMessage(84436)
            outlierIDs = [str(self.ssdo.order2Master[i]) for i in self.outliers]
            outlierIDs = ", ".join(outlierIDs)
            ARCPY.AddMessage(msg.format(outlierIDs))

    def returnAvgDist(self, percentile = .1):
        numDist = len(self.distances2Include)
        cutoff = int(numDist * percentile)
        sortedDistances = NUM.sort(self.distances2Include)
        return sortedDistances[0:cutoff+1].mean()

    def convexHull(self, outputFC):
        xyCoords = self.ssdo.xyCoords
        if self.distances2Include:
            xyCoords = xyCoords[self.distances2Include]

        clearedMinBoundGeom = clearExtent(minBoundGeomPoints)
        minBoundGeomPoints(xyCoords, outputFC,
                           geomType = "CONVEX_HULL",
                           spatialRef = self.ssdo.spatialRef)


class FishnetInfo(object):
    """Creates information for the construction of a fishnet grid.

    INPUTS:
    ssdo (obj): instance of a SSDataIObject
    area (float): total area used for input
    boundaryExtent {obj, None}: optional extent for fishnet grid

    ATTRIBUTES:
    length (float): total width of extent
    height (float): total height of extent
    extent (obj): extent for analysis
    numCols (int): number of columns in fishnet
    numRows (int): number of rows in fishnet
    origin (str): origin string for Fishnet GP Tool
    rotate (str): rotate string for Fishnet GP Tool
    corner (str): corner string for Fishnet GP Tool
    quadLength (float): length/height of a cell
    """
    def __init__(self, ssdo, area, boundaryExtent = None,
                 explicitCellSize = None, nonZeroN = None,
                 explicitProjection = None):
        #### Set Initial Attributes ####
        assignClassAttr(self, locals())
        self.initialize()

    def initialize(self):
        if self.boundaryExtent:
            extent = self.boundaryExtent
        else:
            extent = self.ssdo.extent

        length = extent.XMax - extent.XMin
        height = extent.YMax - extent.YMin

        if self.explicitCellSize:
            self.quadLength = self.explicitCellSize
        else:
            if self.nonZeroN:
                N = self.nonZeroN
            else:
                N = self.ssdo.numObs
            self.quadLength = NUM.sqrt( (2. * (self.area / N)) )

        self.length = length
        self.height = height
        self.numCols = numCells(self.length, self.quadLength)
        self.numRows = numCells(self.height, self.quadLength)
        self.origin = str(extent.XMin) + " " + str(extent.YMin)
        self.rotate = str(extent.XMin) + " " + str(extent.YMin + 1)
        self.corner = str(extent.XMax) + " " + str(extent.YMax)
        self.extent = extent

class DistanceInfo(object):
    """Creates and study area envelope based on the given extent.

    INPUTS:
    spatialRef (obj): instance of a spatial reference object

    ATTRIBUTES:
    name (str): linear/angular unit name
    type (str): {PROJECTED, GEOGRAPHIC, UNKNOWN}
    unitType (str): {LINEAR, ANGULAR, UNKNOWN}
    convertType (str): {METERS or DECIMAL_DEGREES}
    convertFactor (float): conversion factor to meters or decimal degrees
    outputString (str): plural string representation
    """

    def __init__(self, spatialRef, useChordalDistances = True):
        self.spatialRef = spatialRef
        self.useChordalDistances = useChordalDistances
        self.setInfo()

    def setInfo(self):
        """Sets the attributes for the DistanceInfo Class."""
        if self.spatialRef == None:
            self.setUnknown()
        else:
            self.type = self.spatialRef.type.upper()
            if self.type == "PROJECTED":
                self.name = self.spatialRef.linearUnitName.upper()
                self.unitType = "LINEAR"
                self.convertType = "METERS"
                self.convertFactor = self.spatialRef.metersPerUnit
            elif self.type == "GEOGRAPHIC":
                if self.useChordalDistances:
                    self.name = "METER"
                    self.unitType = "CHORDAL"
                    self.convertType = "METERS"
                    self.convertFactor = 1.0
                else:
                    self.name = self.spatialRef.angularUnitName.upper()
                    self.unitType = "ANGULAR"
                    self.convertType = "DECIMALDEGREES"
                    self.convertFactor = self.spatialRef.radiansPerUnit
            else:
                self.setUnknown()
        info = distanceUnitInfo[self.name]
        self.outputString = info[0]

    def linearUnitString(self, distance, convert = False):
        """Returns a linear unit distance string for use in tools like
        Buffer."""

        if convert:
            distance = distance * self.convertFactor
            return str(distance) + " " + self.convertType
        else:
            return str(distance) + " " + self.name

    def printDistance(self, distance, formatStr = "%0.4f"):
        return LOCALE.format(formatStr, distance) + " " + self.outputString

    def setUnknown(self):
        """Sets Distance Info to Unknown."""
        self.name = "UNKNOWN"
        self.type = "UNKNOWN"
        self.unitType = "UNKNOWN"
        self.convertType = "UNKNOWN"
        info = distanceUnitInfo[self.name]
        self.outputString, self.convertFactor = info

    def joinXYTolerance(self):
        if self.type == "GEOGRAPHIC":
            maxTol = 0.000000008983153 
        else:
            maxTol = .001 
        joinTol = self.spatialRef.XYTolerance * self.convertFactor
        if joinTol > maxTol:
            joinTol = maxTol

        return str(joinTol) + " " + self.convertType


distanceUnitInfo = {
"METER": ("Meters", 1.0),
"FOOT": ("Feet", 0.3048),
"FOOT_US": ("US_Feet", 0.3048006096012192),
"FOOT_CLARKE": ("Clarke Feet", 0.304797265),
"FATHOM": ("Fathoms", 1.8288),
"NAUTICAL_MILE": ("Nautical Miles", 1852.0),
"METER_GERMAN": ("German Meters", 1.00000135965),
"CHAIN_US": ("US Chains", 20.11684023368047),
"LINK_US": ("US Links", 0.2011684023368047),
"MILE_US": ("US Miles", 1609.347218694438),
"KILOMETER": ("Kilometers", 1000.0),
"YARD_CLARKE": ("Clarke Yards", 0.914391795),
"CHAIN_CLARKE": ("Clarke Chains", 20.11661949),
"LINK_CLARKE": ("Clarke Links", 0.2011661949),
"YARD_SEARS": ("Sears Yards", 0.9143984146160287),
"FOOT_SEARS": ("Sears Feet", 0.3047994715386762),
"CHAIN_SEARS": ("Sears Chains", 20.11676512155263),
"LINK_SEARS": ("Sears Links", 0.2011676512155263),
"YARD_BENOIT_1895_A": ("Benoit Yards (1895 A)", 0.9143992),
"FOOT_BENOIT_1895_A": ("Benoit Feet (1895 A)", 0.3047997333333333),
"CHAIN_BENOIT_1895_A": ("Benoit Chains (1895 A)", 20.1167824),
"LINK_BENOIT_1895_A": ("Benoit Links (1895 A)", 0.201167824),
"YARD_BENOIT_1895_B": ("Benoit Yards (1895 B)", 0.9143992042898124),
"FOOT_BENOIT_1895_B": ("Benoit Feet (1895 B)", 0.3047997347632708),
"CHAIN_BENOIT_1895_B": ("Benoit Chains (1895 B)", 20.11678249437587),
"LINK_BENOIT_1895_B": ("Benoit Links (1895 B)", 0.2011678249437587),
"FOOT_1865": ("Feet (1865)", 0.3048008333333334),
"FOOT_INDIAN": ("Indian Feet", 0.3047995102481469),
"FOOT_INDIAN_1937": ("Indian Feet (1937)", 0.30479841),
"FOOT_INDIAN_1962": ("Indian Feet (1962)", 0.3047996),
"FOOT_INDIAN_1975": ("Indian Feet (1975)", 0.3047995),
"YARD_INDIAN": ("Indian Yards", 0.9143985307444408),
"YARD_INDIAN_1937": ("Indian Yards (1937)", 0.91439523),
"YARD_INDIAN_1962": ("Indian Yards (1962)", 0.9143988),
"YARD_INDIAN_1975": ("Indian Yards (1975)", 0.9143985),
"STATUTE_MILE": ("Statute Miles", 1609.344),
"FOOT_GOLD_COAST": ("Gold Coast Feet", 0.3047997101815088),
"FOOT_BRITISH_1936": ("British Feet (1936)", 0.3048007491),
"YARD": ("Yards", 0.9144),
"YARD_US": ("US Yards", 0.9144018288036576),
"CHAIN": ("Chains", 20.1168),
"LINK": ("Links", 0.201168),
"DECIMETER": ("Decimeters", 0.1),
"CENTIMETER": ("Centimeters", 0.01),
"MILLIMETER": ("Millimeters", 0.001),
"INCH": ("Inches", 0.0254),
"INCH_US": ("US Inches", 0.0254000508001016),
"ROD": ("Rods", 5.0292),
"ROD_US": ("US Rods", 5.029210058420118),
"NAUTICAL_MILE_US": ("US Nautical Miles", 1853.248),
"NAUTICAL_MILE_UK": ("UK Nautical Miles", 1853.184),
"50_KILOMETERS": ("50 Kilometers", 50000.0),
"150_KILOMETERS": ("150 Kilometers", 150000.0),
"UNKNOWN": ("Unknown Units", 1.0),
"RADIAN": ("Radians", 1.0),
"RADIANS": ("Radians", 1.0),
"DEGREE": ("Degrees", 0.0174532925199433),
"MINUTE": ("Minutes", 0.0002908882086657216),
"SECOND": ("Seconds", 0.00000484813681109536),
"GRAD": ("Grads", 0.01570796326794897),
"GON": ("Gons", 0.01570796326794897),
"MICRORADIAN": ("Microradians", 0.000001),
"MINUTE_CENTESIMAL": ("Centesimal Minutes", 0.0001570796326794897),
"SECOND_CENTESIMAL": ("Centesimal Seconds", 0.000001570796326794897),
"MIL_6400": ("MIL_6400", 0.0009817477042468104)
}
