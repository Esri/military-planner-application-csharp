"""
Tool Name:     Global Moran's I
Source Name:   GlobalI.py
Version:       ArcGIS 10.0
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
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

class GlobalI_Step(object):
    """Calculates Global Morans I, Step-Wise Version (Array Based):
    """

    def __init__(self, ssdo, y, weightsMatrix, weightsType = "SWM",
                 silent = True):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())

        #### Construct Based on SWM File or On The Fly ####
        self.construct()

        #### Calculate Moran's I ####
        self.calculate()

    def construct(self):
        """Constructs the neighborhood structure for each feature and
        dispatches the appropriate values for the calculation of the
        statistic."""

        #### Shorthand Attributes ####
        ssdo = self.ssdo
        masterField = ssdo.masterField
        numObs = len(self.y)
        master2Order = self.ssdo.master2Order

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

        #### Open Spatial Weights and Obtain Chars ####
        if self.weightsType == "SWM":
            swm = WU.SWMReader(self.weightsMatrix)
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

        elif self.weightsType == "GWT":
            #### Warning for GWT with Bad Records/Selection ####
            if ssdo.selectionSet or ssdo.badRecords:
                ARCPY.AddIDMessage("WARNING", 1029)

            #### Build Weights Dictionary ####
            iterVals = master2Order.keys() 
            N = numObs

        else:
            #### Use GA Table, 8 Nearest Neighbors ####
            iterVals = range(numObs)
            N = numObs
            neighWeights = ARC._ss.NeighborWeights(ssdo.gaTable, 
                                                   self.weightsMatrix)

        #### Create Neighbor Info Class ####
        ni = WU.NeighborInfo(masterField, silent = self.silent)

        #### Calculation For Each Feature ####
        for i in iterVals:
            if self.weightsType == "SWM":
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
            elif self.weightsType == "GWT":
                #### Text Weights ####
                masterID = i
                includeIt = True
                rowInfo = WU.getWeightsValuesText(masterID, master2Order,
                                                  self.weightsMatrix, 
                                                  self.yDev)

            else:
                #### Distance Based ####
                masterID = ssdo.gaTable[i][0]
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

        #### Clean Up ####
        if self.weightsType == "SWM":
            swm.close()
            
        if not self.silent:
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

if __name__ == "__main__":
    setupGlobalI()

