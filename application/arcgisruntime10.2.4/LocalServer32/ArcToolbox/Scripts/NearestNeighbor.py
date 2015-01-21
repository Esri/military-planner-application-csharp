"""
Tool Name:  Average Nearest Neighbor
Source Name: NearestNeighbor.py
Version: ArcGIS 10.1
Author: ESRI

This tool performs the nearest neighbor measure of spatial clustering.
Given a set of features, it evaluates whether these features are more
or less clustered than we might expect by chance.  The nearest neighbor
approach involves:
(1) Measuring the distance between each feature and its nearest neighbor
(2) Calculating the mean nearest neighbor distance (observed)
(3) Calculating the mean nearest neighbor distance for theoretical random
    distribution (expected)
(4) Comparing the observed and expected by calculating a Z score for 
    their difference.
(5) Displaying the results of whether or not the Z Score is significant.
"""

################### Imports ########################

import os as OS
import sys as SYS
import numpy as NUM
import xml.etree.ElementTree as ET
import arcgisscripting as ARC
import arcpy as ARCPY
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO 
import gapy as GAPY
import Stats as STATS
import WeightsUtilities as WU
import SSReport as REPORT
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

def setupNearestNeighbor():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)
    distanceConcept = ARCPY.GetParameterAsText(1).upper().replace(" ", "_")
    displayIt = ARCPY.GetParameter(2)                   
    studyArea = UTILS.getNumericParameter(3)                  
    concept = WU.conceptDispatch[distanceConcept]

    #### Create a Spatial Stats Data Object (SSDO) ####
    ssdo = SSDO.SSDataObject(inputFC, useChordal = True)

    #### Populate SSDO with Data ####
    ssdo.obtainDataGA(ssdo.oidName, minNumObs = 2)

    #### Calculate ####
    nn = NearestNeighbor(ssdo, concept = concept, studyArea = studyArea)

    #### Report and Set Parameters ####
    nn.report()

    try:
        ARCPY.SetParameterAsText(4, nn.ratioString)
        ARCPY.SetParameterAsText(5, nn.znString)
        ARCPY.SetParameterAsText(6, nn.pvString)
        ARCPY.SetParameterAsText(7, nn.enString)
        ARCPY.SetParameterAsText(8, nn.nnString)
    except:
        ARCPY.AddIDMessage("WARNING", 902)

    #### Create HTML Output ####
    if displayIt:
        htmlOutFile = nn.reportHTML(htmlFile = None)
        ARCPY.SetParameterAsText(9, htmlOutFile)

class NearestNeighbor(object):
    """Calculates the Nearest Neighbor Test Statistic for complete spatial
    randomness.

    INPUTS:
    ssdo (obj): instance of SSDataObject
    concept: {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN 
    studyArea {float, None}: Optional study area to use in calculation.

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

    def __init__(self, ssdo, concept = "EUCLIDEAN", studyArea = None):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())

        #### Set Study Area ####
        self.setStudyArea()

        #### Calculate ####
        self.calculate()

    def setStudyArea(self):
        """Sets the study area for the nearest neighbor stat."""

        #### Attribute Shortcuts ####
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84248))
        ssdo = self.ssdo

        if self.studyArea == None:
            #### Create Min Enc Rect ####
            studyAreaFC = UTILS.returnScratchName("regularBound_FC")
            clearedMinBoundGeom = UTILS.clearExtent(UTILS.minBoundGeomPoints)
            clearedMinBoundGeom(ssdo.xyCoords, studyAreaFC, 
                                geomType = "RECTANGLE_BY_AREA",
                                spatialRef = ssdo.spatialRef)
            polyInfo = UTILS.returnPolygon(studyAreaFC, 
                                           spatialRef = ssdo.spatialRefString,
                                           useGeodesic = ssdo.useChordal)
            studyAreaPoly, studyArea = polyInfo
            UTILS.passiveDelete(studyAreaFC)

            if studyArea == None:
                #### Invalid Study Area ####
                ARCPY.AddIDMessage("Error", 932)
                raise SystemExit()

            self.studyArea = studyArea 

    def calculate(self):
        """Calculates the nearest neighbor statistic."""

        #### Attribute Shortcuts ####
        ssdo = self.ssdo
        gaTable = ssdo.gaTable
        N = ssdo.numObs
        studyArea = self.studyArea
        ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84007), 0, N, 1)

        #### Create k-Nearest Neighbor Search Type ####
        gaSearch = GAPY.ga_nsearch(gaTable)
        gaConcept = self.concept.lower()
        gaSearch.init_nearest(0.0, 1, gaConcept)
        neighDist = ARC._ss.NeighborDistances(gaTable, gaSearch)
        distances = NUM.empty((N,), float)

        #### Add All NN Distances ####
        for row in xrange(N):
            distances[row] = neighDist[row][-1][0]
            ARCPY.SetProgressorPosition()
        
        maxDist = distances.max()
        if ssdo.useChordal:
            hardMaxExtent = ARC._ss.get_max_gcs_distance(ssdo.spatialRef)
            if maxDist > hardMaxExtent:
                ARCPY.AddIDMessage("ERROR", 1609)
                raise SystemExit()
        
        #### Calculate Mean Nearest Neighbor Distance ####
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84007))
        observedMeanDist = distances.mean()

        #### Calculate Expected Mean Nearest Neighbor Distance ####
        expectedMeanDist = 1.0 / (2.0 * ((N / studyArea)**0.5))

        #### Calculate the Z-Score #### 
        standardError = 0.26136 / ((N**2.0 / studyArea)**0.5)

        #### Verify Results ####
        check1 = abs(expectedMeanDist) > 0.0
        check2 = abs(standardError) > 0.0
        if not (check1 and check2):
            ARCPY.AddIDMessage("Error", 907)
            raise SystemExit()

        #### Calculate Statistic ####
        ratio = observedMeanDist / expectedMeanDist
        zScore = (observedMeanDist - expectedMeanDist) / standardError
        pVal = STATS.zProb(zScore, type = 2)

        #### Set Attributes ####
        self.nn = observedMeanDist
        self.en = expectedMeanDist
        self.ratio = ratio
        self.zn = zScore
        self.pVal = pVal

    def report(self, fileName = None):
        """Reports the General G results as a message or to a file.  If
        self.displayIt is set to True, then an html graphical report is
        generated to your default temp directory.

        INPUTS:
        fileName {str, None}: path to a text file to populate with results.
        """

        #### Format Output ####
        observedOut = LOCALE.format("%0.6f", self.nn)
        expectedOut = LOCALE.format("%0.6f", self.en)
        ratioOut = LOCALE.format("%0.6f", self.ratio)
        zValueOut = LOCALE.format("%0.6f", self.zn)
        pValOut = LOCALE.format("%0.6f", self.pVal)

        #### Create Output Text Table ####
        header = ARCPY.GetIDMessage(84161)
        row1 = [ ARCPY.GetIDMessage(84162), observedOut ]
        row2 = [ ARCPY.GetIDMessage(84163), expectedOut ]
        row3 = [ ARCPY.GetIDMessage(84164), ratioOut ]
        row4 = [ ARCPY.GetIDMessage(84151), zValueOut ]
        row5 = [ ARCPY.GetIDMessage(84152), pValOut ]
        total = [row1,row2,row3,row4,row5]
        outputTable = UTILS.outputTextTable(total, header = header, pad = 1)
        distanceOut = self.ssdo.distanceInfo.outputString
        dmsg = ARCPY.GetIDMessage(84344)
        distanceMeasuredStr = dmsg.format(distanceOut)
        outputTable += "\n%s\n" % distanceMeasuredStr

        if fileName:
            f = UTILS.openFile(fileName, "w")
            f.write(outputTable)
            f.close()
        else:
            ARCPY.AddMessage(outputTable)

        #### Set Formatted Floats ####
        self.nnString = observedOut
        self.enString = expectedOut
        self.ratioString = ratioOut
        self.znString = zValueOut
        self.pvString = pValOut
        self.nnStringD = self.ssdo.distanceInfo.printDistance(self.nn)
        self.enStringD = self.ssdo.distanceInfo.printDistance(self.en)

    def reportHTML(self, htmlFile = None):
        """Generates a graphical html report for Nearest Neighbor Stat."""

        #### Shorthand Attributes ####
        zScore = self.zn

        #### Progress and Create HTML File Name ####
        writeMSG = ARCPY.GetIDMessage(84228)
        ARCPY.SetProgressor("default", writeMSG)
        ARCPY.AddMessage(writeMSG)
        if not htmlFile:
            prefix = ARCPY.GetIDMessage(84240)
            outputDir = UTILS.returnScratchWorkSpace()
            baseDir = UTILS.getBaseFolder(outputDir)
            htmlFile = UTILS.returnScratchName(prefix, fileType = "TEXT", 
                                               scratchWS = baseDir,
                                               extension = "html")

        #### Obtain Correct Images ####
        imageDir = UTILS.getImageDir()
        clustStr = ARCPY.GetIDMessage(84243)
        dispStr = ARCPY.GetIDMessage(84244)
        if zScore <= -2.58:
            imageFile = OS.path.join(imageDir, "clusteredPoints01.png")
            info = ("1%", clustStr)
            imageBox = OS.path.join(imageDir, "dispersedBox01.png")
        elif (-2.58 < zScore <= -1.96):
            imageFile = OS.path.join(imageDir, "clusteredPoints05.png")
            info = ("5%", clustStr)
            imageBox = OS.path.join(imageDir, "dispersedBox05.png")
        elif (-1.96 < zScore <= -1.65):
            imageFile = OS.path.join(imageDir, "clusteredPoints10.png")
            info = ("10%", clustStr)
            imageBox = OS.path.join(imageDir, "dispersedBox10.png")
        elif (-1.65 < zScore < 1.65):
            imageFile = OS.path.join(imageDir, "randomPoints.png")
            imageBox = OS.path.join(imageDir, "randomBox.png")
        elif (1.65 <= zScore < 1.96):
            imageFile = OS.path.join(imageDir, "dispersedPoints10.png")
            info = ("10%", dispStr)
            imageBox = OS.path.join(imageDir, "clusteredBox10.png")
        elif (1.96 <= zScore < 2.58):
            imageFile = OS.path.join(imageDir, "dispersedPoints05.png")
            info = ("5%", dispStr)
            imageBox = OS.path.join(imageDir, "clusteredBox05.png")
        else:
            imageFile = OS.path.join(imageDir, "dispersedPoints01.png")
            info = ("1%", dispStr)
            imageBox = OS.path.join(imageDir, "clusteredBox01.png")

        #### Footnote ####
        footStart = ARCPY.GetIDMessage(84230).format(zScore)
        if abs(zScore) >= 1.65:
            footEnd = ARCPY.GetIDMessage(84231)
            footEnd = footEnd.format(*info)
            footerText = footStart + footEnd 
        else:
            footEnd = ARCPY.GetIDMessage(84232)
            footerText = footStart + footEnd

        #### Root Element ####
        title = ARCPY.GetIDMessage(84161)
        reportElement, reportTree = REPORT.xmlReport(title = title)

        #### Begin Graphic SubElement ####
        graphicElement = REPORT.xmlGraphic(reportElement, imageFile, 
                                           footerText = footerText)

        #### Floating Table ####
        rowVals = [ [ARCPY.GetIDMessage(84164), self.ratioString, ""],
                    [ARCPY.GetIDMessage(84151), self.znString, imageBox],
                    [ARCPY.GetIDMessage(84152), self.pvString, ""] ]

        fTable = REPORT.xmlTable(graphicElement, rowVals, 
                                 tType = "ssFloat")

        #### NN Table ####
        rowVals = [ [ARCPY.GetIDMessage(84162), self.nnStringD],
                    [ARCPY.GetIDMessage(84163), self.enStringD],
                    [ARCPY.GetIDMessage(84164), self.ratioString],
                    [ARCPY.GetIDMessage(84151), self.znString],
                    [ARCPY.GetIDMessage(84152), self.pvString] ]

        nnTable = REPORT.xmlTable(reportElement, rowVals,
                                  title = ARCPY.GetIDMessage(84161))

        #### Dataset Table ####
        rowVals = [ [UTILS.addColon(ARCPY.GetIDMessage(84233)), 
                     self.ssdo.inputFC],
                    [UTILS.addColon(ARCPY.GetIDMessage(84235)),
                     self.concept],
                    [UTILS.addColon(ARCPY.GetIDMessage(84241)), 
                     LOCALE.format("%0.6f", self.studyArea)],
                    [UTILS.addColon(ARCPY.GetIDMessage(84418)),
                     str(self.ssdo.selectionSet)] ]

        dTable = REPORT.xmlTable(reportElement, rowVals,
                         title = ARCPY.GetIDMessage(84239))

        #### Create HTML ####
        html = REPORT.report2html(reportTree, htmlFile)
        ARCPY.AddMessage(htmlFile)

        return htmlFile

if __name__ == '__main__':
    setupNearestNeighbor()

