"""
Tool Name:     Calculate Distance Band from Neighbor Count 
Source Name:   CalculateDistanceBand.py
Version:       ArcGIS 10.1
Author:        Environmental Systems Research Institute Inc.
Description:   Provides the minimum, maximum and average distance from a
               set of features based on a given neighbor count.
"""

################### Imports ########################

import os as OS
import sys as SYS
import numpy as NUM
import arcgisscripting as ARC
import arcpy as ARCPY
import ErrorUtils as ERROR
import SSUtilities as UTILS
import SSDataObject as SSDO 
import WeightsUtilities as WU
import gapy as GAPY
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

################### GUI Interface ######################

def setupCalcDistBand():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    inputFC = ARCPY.GetParameterAsText(0)
    kNeighs = UTILS.getNumericParameter(1)
    if not kNeighs:
        kNeighs = 0

    distanceConcept = ARCPY.GetParameterAsText(2).upper().replace(" ", "_")
    concept = distanceConcept.split("_")[0]
    cdb = calculateDistanceBand(inputFC, kNeighs, concept)

def calculateDistanceBand(inputFC, kNeighs, concept = "EUCLIDEAN"):
    """Provides the minimum, maximum and average distance from a
    set of features based on a given neighbor count.

    INPUTS: 
    inputFC (str): path to the input feature class
    kNeighs (int): number of neighbors to return
    concept {str, EUCLIDEAN}: EUCLIDEAN or MANHATTAN distance
    """    

    #### Assure that kNeighs is Non-Zero ####
    if kNeighs <= 0:
        ARCPY.AddIDMessage("ERROR", 976)
        raise SystemExit()

    #### Set Default Progressor for Neigborhood Structure ####
    ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84143))

    #### Create SSDataObject ####
    ssdo = SSDO.SSDataObject(inputFC, useChordal = True)
    cnt = UTILS.getCount(inputFC)
    ERROR.errorNumberOfObs(cnt, minNumObs = 2)

    #### Create GA Data Structure ####
    gaTable, gaInfo = WU.gaTable(inputFC, spatRef = ssdo.spatialRefString)

    #### Assure Enough Observations ####
    N = gaInfo[0]
    ERROR.errorNumberOfObs(N, minNumObs = 2)

    #### Process Any Bad Records Encountered ####
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
    gaConcept = concept.lower()
    gaSearch.init_nearest(0.0, kNeighs, gaConcept)
    neighDist = ARC._ss.NeighborDistances(gaTable, gaSearch)

    #### Set Progressor for Weights Writing ####
    ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84007), 0, N, 1)
    distances = NUM.empty((N,), float)

    for row in xrange(N):
        distances[row] = neighDist[row][-1].max()
        ARCPY.SetProgressorPosition()

    #### Calculate and Report ####
    minDist = distances.min()
    avgDist = distances.mean()
    maxDist = distances.max()
    if ssdo.useChordal:
        hardMaxExtent = ARC._ss.get_max_gcs_distance(ssdo.spatialRef)
        if maxDist > hardMaxExtent:
            ARCPY.AddIDMessage("ERROR", 1609)
            raise SystemExit()

    minDistOut = LOCALE.format("%0.6f", minDist)
    avgDistOut = LOCALE.format("%0.6f", avgDist)
    maxDistOut = LOCALE.format("%0.6f", maxDist)

    #### Create Output Text Table ####
    header = ARCPY.GetIDMessage(84171)
    row1 = [ ARCPY.GetIDMessage(84165).format(kNeighs), minDistOut ]
    row2 = [ ARCPY.GetIDMessage(84166).format(kNeighs), avgDistOut ]
    row3 = [ ARCPY.GetIDMessage(84167).format(kNeighs), maxDistOut ]
    total = [row1,row2,row3]
    tableOut = UTILS.outputTextTable(total,header=header,pad=1)

    #### Add Linear/Angular Unit ####
    distanceOut = ssdo.distanceInfo.outputString
    distanceMeasuredStr = ARCPY.GetIDMessage(84344).format(distanceOut)
    tableOut += "\n%s\n" % distanceMeasuredStr

    #### Report Text Output ####
    ARCPY.AddMessage(tableOut)

    #### Set Derived Output ####
    ARCPY.SetParameterAsText(3, minDist)
    ARCPY.SetParameterAsText(4, avgDist)
    ARCPY.SetParameterAsText(5, maxDist)

    #### Clean Up ####
    del gaTable

if __name__ == '__main__':
    setupCalcDistBand()
