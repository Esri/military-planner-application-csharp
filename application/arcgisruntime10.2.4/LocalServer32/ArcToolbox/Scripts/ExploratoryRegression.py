"""
Tool Name:     Exploratory Regression
Source Name:   ExploratoryRegression.py
Version:       ArcGIS 10.0
Author:        Environmental Systems Research Institute Inc.
"""

################ Imports ####################
import sys as SYS
import copy as COPY
import os as OS
import collections as COLL
import operator as OP
import locale as LOCALE
import numpy as NUM
import math as MATH
import numpy.linalg as LA
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.da as DA
import ErrorUtils as ERROR
import SSDataObject as SSDO
import SSUtilities as UTILS
import Stats as STATS
import MoransI_Step as GI
import WeightsUtilities as WU
import gapy as GAPY
import itertools as ITER
import locale as LOCALE
LOCALE.setlocale(LOCALE.LC_ALL, '')

################ Output Field Names #################
erFieldNames = ["RunID", "AdjR2", "AICc", "JB",
                "K_BP", "MaxVIF", "SA", "NumVars"]

############## Helper Functions ##############

masterJustify = ["right"] * 6 + ["left"]

def returnPerc(numer, denom):
    if numer == 0:
        return 0.0
    else:
        return ( (numer * 1.0) / denom) * 100.

def runMoransI(ssdo, residuals, weightsMatrix, weightsType = "SWM",
               silent = True):
    mi = GI.GlobalI_Step(ssdo, residuals, weightsMatrix,
                         weightsType = weightsType,
                         silent = silent)
    return mi

def nChooseK(n, k):
    top = MATH.factorial(n)
    left = MATH.factorial(k)
    right = MATH.factorial(n - k)
    return (top * 1.0) / (left * right)

def inSameCombo(n, k):
    top = MATH.factorial(n - 2)
    left = MATH.factorial(k - 2)
    right = MATH.factorial(n - k)
    return (top * 1.0) / (left * right)

################ Interfaces ##################

def runExploratoryRegression():
    """Retrieves the parameters from the User Interface and executes the
    appropriate commands."""

    #### Get User Provided Inputs ####
    ARCPY.env.overwriteOutput = True
    inputFC = ARCPY.GetParameterAsText(0)
    dependentVar = ARCPY.GetParameterAsText(1).upper()
    independentVarsReg = ARCPY.GetParameterAsText(2)
    independentVars = independentVarsReg.upper().split(";")
    weightsFile = UTILS.getTextParameter(3)

    #### Optional Output ####
    outputReportFile = UTILS.getTextParameter(4)
    outputTable = UTILS.getTextParameter(5)

    #### Search Criterion ####
    maxIndVars = UTILS.getNumericParameter(6)
    minIndVars = UTILS.getNumericParameter(7)
    minR2 = UTILS.getNumericParameter(8)
    maxCoef = UTILS.getNumericParameter(9)
    maxVIF = UTILS.getNumericParameter(10)
    minJB = UTILS.getNumericParameter(11)
    minMI = UTILS.getNumericParameter(12)

    #### Create a Spatial Stats Data Object (SSDO) ####
    ssdo = SSDO.SSDataObject(inputFC)

    #### Set Unique ID Field ####
    masterField = UTILS.setUniqueIDField(ssdo, weightsFile = weightsFile)

    #### MasterField Can Not Be The Dependent Variable ####
    if masterField == dependentVar:
        ARCPY.AddIDMessage("ERROR", 945, masterField,
                           ARCPY.GetIDMessage(84112))
        raise SystemExit()

    #### Remove the MasterField from Independent Vars ####
    if masterField in independentVars:
        independentVars.remove(masterField)
        ARCPY.AddIDMessage("WARNING", 736, masterField)

    #### Remove the Dependent Variable from Independent Vars ####
    if dependentVar in independentVars:
        independentVars.remove(dependentVar)
        ARCPY.AddIDMessage("WARNING", 850, dependentVar)

    #### Raise Error If No Independent Vars ####
    if not len(independentVars):
        ARCPY.AddIDMessage("ERROR", 737)
        raise SystemExit()

    #### Obtain Data ####
    allVars = [dependentVar] + independentVars

    #### Populate SSDO with Data ####
    if not weightsFile:
        ssdo.obtainDataGA(masterField, allVars, minNumObs = 5,
                          warnNumObs = 30)
    else:
        ssdo.obtainData(masterField, allVars, minNumObs = 5,
                        warnNumObs = 30)

    exploreRegress = ExploratoryRegression(ssdo, dependentVar,
                                              independentVars,
                                    weightsFile = weightsFile,
                          outputReportFile = outputReportFile,
                                    outputTable = outputTable,
                                      maxIndVars = maxIndVars,
                                      minIndVars = minIndVars,
                             minR2 = minR2, maxCoef = maxCoef,
                               maxVIF = maxVIF, minJB = minJB,
                                                minMI = minMI)

    #### Assure Table is Added to TOC ####
    if outputTable:
        if exploreRegress.dbf:
            ARCPY.SetParameterAsText(5, exploreRegress.outputTable)

################## Classes ###################

class ResultHandler(object):
    """Handles result information for Exploratory Regression."""

    def __init__(self, allVarNames, numChoose, ssdo,
                 weightMatrix, weightsType = "SWM",
                 minR2 = .5, maxCoef = .01, maxVIF = 5.0,
                 minJB = .1, minMI = .1, silent = False):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())

        #### Set Label ####
        self.numVars = len(self.allVarNames)

        self.label = ARCPY.GetIDMessage(84283).format(numChoose, self.numVars)
        if numChoose <= 2:
            self.eachAppears = 1
        else:
            self.eachAppears = nChooseK(self.numVars - 2, numChoose - 2)

        #### Set Result Structures ####
        self.varSignDict = {}
        self.signDict = {}
        self.vifDict = {}
        for varName in self.allVarNames:
            self.varSignDict[varName] = [0, 0]
            self.signDict[varName] = [0, 0]
            self.vifDict[varName] = [0, []]

        self.olsResults = {}
        self.bestR2Vals = []
        self.bestR2Res = []
        self.passTable = []
        self.passBools = []
        self.r2Residuals = NUM.empty((self.ssdo.numObs, 3), dtype = float)
        self.allJBPass = UTILS.compareFloat(0.0, self.minJB, rTol = .00000001)
        self.allMIPass = UTILS.compareFloat(0.0, self.minMI, rTol = .00000001)
        self.miVals = []

    def returnSilentBool(self):
        """Returns whether SWM neighbor warnings should be printed."""
        if not self.silent and not len(self.miVals):
            #### Only Return Neighbor Warnings Once ####
            self.silent = True
            return False
        else:
            return True

    def runR2Moran(self):
        """Runs Moran's I for highest R2 Models."""
        resultList = []
        for ind, olsID in enumerate(self.bestR2Res):
            olsRes = self.olsResults[olsID]
            if olsRes.miPVal == None:
                silentBool = self.returnSilentBool()
                residuals = self.r2Residuals[:,ind].flatten()
                if not self.allMIPass:
                    mi = runMoransI(self.ssdo, residuals,
                                    self.weightMatrix,
                                    weightsType = self.weightsType,
                                    silent = silentBool)
                    miPVal = mi.pVal
                else:
                    miPVal = 1.0

                olsRes.setMoransI(miPVal)
                self.miVals.append(miPVal)

            #### Allows the Update of Output Table ####
            resultList.append( (olsID, olsRes.miPVal) )

        return resultList

    def evaluateResult(self, olsResult, residuals, keep = False):
        """Evaluates an OLS result in the context of search criteria."""

        #### Evaluate R2 ####
        r2Value = olsResult.r2
        lenR2 = len(self.bestR2Vals)
        inR2 = False
        if lenR2 < 3:
            self.bestR2Vals.append(r2Value)
            self.bestR2Res.append(olsResult.id)
            self.r2Residuals[:,lenR2] = residuals
            inR2 = True
        else:
            minIndex = NUM.argsort(self.bestR2Vals)[0]
            minValue = self.bestR2Vals[minIndex]
            if r2Value > minValue:
                self.bestR2Vals[minIndex] = r2Value
                self.bestR2Res[minIndex] = olsResult.id
                self.r2Residuals[:,minIndex] = residuals
                inR2 = True

        #### Add to Master List of OLS Results ####
        keepBool = (keep or inR2)
        if keepBool:
            self.olsResults[olsResult.id] = olsResult

        #### Evaluate p-values ####
        pValVars = olsResult.evaluatePVals(maxCoef = self.maxCoef)

        #### Evaluate VIF ####
        vifVars = olsResult.evaluateVIF(maxVIF = self.maxVIF)

        #### Populate Result Structures ####
        for ind, varName in enumerate(olsResult.varNames):
            self.signDict[varName][0] += 1
            if olsResult.coef[ind] < 0.0:
                self.varSignDict[varName][0] += 1
            else:
                self.varSignDict[varName][1] += 1
        for varName in pValVars:
            self.signDict[varName][1] += 1
        for varName in vifVars:
            self.vifDict[varName][0] += 1
            self.vifDict[varName][1] += list(vifVars)

        #### Obtain Bools ####
        pvBool = len(pValVars) == self.numChoose
        vifBool = len(vifVars) == 0
        r2Bool = olsResult.r2 >= self.minR2
        if not self.allJBPass:
            jbBool = olsResult.jb > self.minJB
        else:
            jbBool = True

        #### Decision Based on Bools ####
        tableBool = pvBool and vifBool
        if tableBool:
            self.passTable.append(olsResult.id)

        allBool = pvBool and vifBool and r2Bool and jbBool
        miBool = False
        if allBool:
            silentBool = self.returnSilentBool()
            if not self.allMIPass:
                mi = runMoransI(self.ssdo, residuals, self.weightMatrix,
                                weightsType = self.weightsType,
                                silent = silentBool)
                miPVal = mi.pVal
            else:
                miPVal = 1.0

            olsResult.setMoransI(miPVal)
            self.miVals.append(miPVal)
            if miPVal > self.minMI:
                self.passBools.append(olsResult.id)
                self.olsResults[olsResult.id] = olsResult
                miBool = True

        return r2Bool, pvBool, vifBool, jbBool, miBool, keepBool

    def report(self):
        """Reports the results from exploratory regression analysis."""

        #### Set Title ####
        title = self.label

        #### Column Labels ####
        labs = [ARCPY.GetIDMessage(84021), ARCPY.GetIDMessage(84249),
                ARCPY.GetIDMessage(84042), ARCPY.GetIDMessage(84036),
                ARCPY.GetIDMessage(84284), ARCPY.GetIDMessage(84292),
                ARCPY.GetIDMessage(84286)]
        r2Info = [ labs ]

        #### Adjusted R2, Sorted Highest to Lowest with ID Tie Breaks ####
        header = ARCPY.GetIDMessage(84287)
        numRes = xrange(len(self.bestR2Res))
        r2Data = []
        for i in numRes:
            r2Val = self.bestR2Vals[i]
            idVal = int(self.bestR2Res[i].split(":")[-1])
            r2Data.append((r2Val, idVal))
        r2Data = NUM.array(r2Data, dtype = [('r2', float), ('ids', int)])
        r2SortedInds = r2Data.argsort(order = ('r2', 'ids'))
        sortIndex = reversed(r2SortedInds)
        for ind in sortIndex:
            olsID = self.bestR2Res[ind]
            olsRes = self.olsResults[olsID]
            olsOut = olsRes.report(formatStr = "%0.2f")
            r2Info.append(olsOut)

        r2Report = UTILS.outputTextTable(r2Info, header = header,
                                         justify = masterJustify)

        #### Passing Models ####
        header = ARCPY.GetIDMessage(84288)
        passList = [ labs ]
        r2Values = []
        olsIDs = []
        for olsID in self.passBools:
            olsRes = self.olsResults[olsID]
            r2Values.append(olsRes.r2)
            olsIDs.append(olsID)
        sortIndex = NUM.argsort(r2Values).tolist()
        sortIndex.reverse()
        for ind in sortIndex:
            olsID = olsIDs[ind]
            olsRes = self.olsResults[olsID]
            olsOut = olsRes.report(formatStr = "%0.6f")
            passList.append(olsOut)

        passingReport = UTILS.outputTextTable(passList, header = header)

        #### Print Report ####
        starMess = ARCPY.GetIDMessage(84289) * 78
        finalReport = [starMess, title, r2Report, passingReport]
        finalReport = "\n".join(finalReport)
        finalReport = finalReport + "\n"
        ARCPY.AddMessage(finalReport)

        return finalReport

class OLSResult(object):
    """Holds OLS Result Info for Exploratory Regression."""
    def __init__(self, id, varNames, coef, pVals, vifVals,
                 r2, aic, jb, bp, allMIPass = False):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())
        self.pVals = NUM.array(pVals)
        self.varNameArray = NUM.array(self.varNames)
        self.miPVal = None
        self.k = len(varNames)

        #### Create Model to Print ####
        self.createModel()

    def evaluateVIF(self, maxVIF = 5.0):
        """Evaluates VIF values."""

        if self.k >= 2:
            self.maxVIFValue = self.vifVals.max()
            overIndices = NUM.where(self.vifVals >= maxVIF)
            return self.varNameArray[overIndices]
        else:
            self.maxVIFValue = 1.0
            return NUM.array([])

    def evaluatePVals(self, maxCoef = .01):
        """Evaluates coefficient p-values."""

        overIndices = NUM.where(self.pVals <= maxCoef)
        return self.varNameArray[overIndices]

    def createModel(self):
        model = []
        for ind, varName in enumerate(self.varNames):
            pVal = self.pVals[ind]
            coefVal = self.coef[ind]

            #### Determine Variable Sign ####
            if coefVal < 0:
                vRes = " -"
            else:
                vRes = " +"

            #### Determine Significance Level ####
            if pVal <= .1 and pVal > .05:
                vRes += varName + "*"
            elif pVal <= .05 and pVal > .01:
                vRes += varName + "**"
            elif pVal <= .01:
                vRes += varName + "***"
            else:
                vRes += varName

            #### Add to Model ####
            model.append(vRes)

        #### Set Attribute ####
        self.model = " ".join(model)

    def setMoransI(self, value):
        self.miPVal = value

    def report(self, orderType = 0, formatStr = "%0.6f", addModel = True):
        """Reports the results of the OLS run.

        INPUTS:
        orderType {int, 0}: Sort by - 0:R2, 1:Jarque-Bera, 2:Moran
        formatStr (str): format string, E.g. "%0.6f"
        addModel {bool, True}: Add model to report?
        """

        #### Set Output Moran's I p-value ####
        if self.allMIPass:
            #### Make p-value NA ####
            miVal = ARCPY.GetIDMessage(84499)
        else:
            if self.miPVal == None:
                miVal = ""
            else:
                miVal = self.miPVal

        vifInd = -2
        if orderType == 0:
            resultList = [ self.r2, self.aic, self.jb, self.bp,
                           self.maxVIFValue, miVal ]
        elif orderType == 1:
            resultList = [ self.jb, self.r2, self.aic, self.bp,
                           self.maxVIFValue, miVal ]
        else:
            resultList = [ miVal, self.r2, self.aic, self.jb, self.bp,
                           self.maxVIFValue ]
            vifInd = -1

        resultListVals = []
        for val in resultList:
            try:
                outValue = UTILS.formatValue(val, formatStr)
            except:
                outValue = val
            resultListVals.append(outValue)

        if self.maxVIFValue >= 1000:
            resultListVals[vifInd] = ">" + LOCALE.format("%0.2f", 1000.)
        if addModel:
            resultListVals.append(self.model)

        return resultListVals


class ExploratoryRegression(object):
    """Computes linear regression via Ordinary Least Squares,
    Psuedo-Step-Wise
    """

    def __init__(self, ssdo, dependentVar, independentVars, weightsFile,
                 outputReportFile = None, outputTable = None,
                 maxIndVars = 5, minIndVars = 1, minR2 = .5,
                 maxCoef = .01, maxVIF = 5.0, minJB = .1, minMI = .1):

        ARCPY.env.overwriteOutput = True

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())
        self.masterField = self.ssdo.masterField
        self.warnedTProb = False

        #### Set Boolean For Passing All Moran's I ####
        self.allMIPass = UTILS.compareFloat(0.0, self.minMI, rTol = .00000001)

        #### Assess Whether SWM File Being Used ####
        if weightsFile:
            weightSuffix = weightsFile.split(".")[-1].lower()
            if weightSuffix == "swm":
                self.weightsType = "SWM"
                self.weightsMatrix = self.weightsFile
            else:
                self.weightsType = "GWT"
                self.weightsMatrix = WU.buildTextWeightDict(weightsFile,
                                                 self.ssdo.master2Order)
        else:
            #### If No Weightsfile Provided, Use 8 Nearest Neighbors ####
            if ssdo.numObs <= 9:
                nn = ssdo.numObs - 2
                ARCPY.AddIDMessage("WARNING", 1500, 8, nn)
            else:
                nn = 8
            self.weightsType = "GA"
            gaSearch = GAPY.ga_nsearch(self.ssdo.gaTable)
            gaSearch.init_nearest(0.0, nn, "euclidean")
            self.weightsMatrix = gaSearch

        #### Initialize Data ####
        self.runModels()

    def runModels(self):
        """Performs additional validation and populates the
        SSDataObject."""

        #### Shorthand Attributes ####
        ssdo = self.ssdo

        #### Create Dependent Variable ####
        self.y = ssdo.fields[self.dependentVar].returnDouble()
        self.n = ssdo.numObs
        self.y.shape = (self.n, 1)

        #### Assure that Variance is Larger than Zero ####
        yVar = NUM.var(self.y)
        if NUM.isnan(yVar) or yVar <= 0.0:
            ARCPY.AddIDMessage("Error", 906)
            raise SystemExit()

        #### Validate Chosen Number of Combos ####
        k = len(ssdo.fields)
        if self.maxIndVars > (k - 1):
            ARCPY.AddIDMessage("WARNING", 1171, self.maxIndVars)
            self.maxIndVars = k - 1
            ARCPY.AddIDMessage("WARNING", 1172, self.maxIndVars)

        #### Assure Degrees of Freedom ####
        withIntercept = self.maxIndVars + 1
        dof = self.n - withIntercept
        if dof <= 2:
            ARCPY.AddIDMessage("WARNING", 1128, 2)
            dofLimit = self.n - 4
            ARCPY.AddIDMessage("WARNING", 1419, dofLimit)
            self.maxIndVars = dofLimit

        if self.maxIndVars < 1:
            ARCPY.AddIDMessage("WARNING", 1173)

        #### Assure Min Vars is less than or equal to Max Vars ####
        if self.maxIndVars < self.minIndVars:
            ARCPY.AddIDMessage("WARNING", 1174)
            ARCPY.AddIDMessage("WARNING", 1175)
            self.minIndVars = self.maxIndVars

        #### Gen Range Combos ####
        rangeVars = range(1, k)
        rangeCombos = NUM.arange(self.minIndVars, self.maxIndVars+1)

        #### Create Base Design Matrix ####
        self.x = NUM.ones((self.n, k), dtype = float)
        for column, variable in enumerate(self.independentVars):
            self.x[:,column + 1] = ssdo.fields[variable].data

        #### Calculate Global VIF ####
        self.globalVifVals = COLL.defaultdict(float)
        if k > 2:
            #### Values Less Than One Were Forced by Psuedo-Inverse ####
            self.printVIF = True
        else:
            self.printVIF = False

        #### Create Output Table Info ####
        if self.outputTable:

            #### List of Results ####
            self.tableResults = []

            #### Valid Table Name and Type ####
            self.outputTable, dbf = UTILS.returnTableName(self.outputTable)
            outPath, outName = OS.path.split(self.outputTable)

            #### Set Field Names (Base) ####
            self.outFieldNames = UTILS.getFieldNames(erFieldNames, outPath)
            self.outFieldTypes = ["LONG", "DOUBLE", "DOUBLE", "DOUBLE",
                                  "DOUBLE", "DOUBLE", "DOUBLE", "LONG"]

            #### Add Field Names (Independent Vars as X#) ####
            maxRange = range(1, self.maxIndVars+1)
            self.outFieldNames += [ "X" + str(j) for j in maxRange ]
            self.outFieldTypes += ["TEXT"] * self.maxIndVars

            #### Calculate Max Text Length for Output Fields ####
            fieldLens = [ len(i) for i in self.independentVars ]
            self.maxFieldLen = max(fieldLens) + 5
            tableReportCount = 0

            #### Set NULL Values and Flag to Reset Table Name ####
            isNullable = UTILS.isNullable(self.outputTable)
            if isNullable:
                self.nullValue = NUM.nan
            else:
                self.nullValue = UTILS.shpFileNull["DOUBLE"]
            self.dbf = dbf

        #### Create Output Report File ####
        if self.outputReportFile:
            fo = UTILS.openFile(self.outputReportFile, "w")

        #### Hold Results for Every Choose Combo ####
        self.resultDict = {}
        self.vifVarCount = COLL.defaultdict(int)
        self.model2Table = {}
        self.sumRuns = 0
        self.sumGI = 0
        self.boolGI = 0
        self.boolResults = NUM.zeros(4, dtype = int)
        self.jbModels = []
        self.jbValues = []
        self.jbResiduals = NUM.empty((self.n, 3), dtype = float)
        self.perfectMultiWarnBool = False
        self.neighborWarn = False

        for choose in rangeCombos:
            #### Generate Index Combos ####
            comboGenerator = ITER.combinations(rangeVars, choose)

            #### Set Progressor ####
            message = ARCPY.GetIDMessage(84293).format(k-1, choose)
            ARCPY.SetProgressor("default", message)

            #### Set Result Structure ####
            rh = ResultHandler(self.independentVars, choose,
                               self.ssdo, self.weightsMatrix,
                               weightsType = self.weightsType,
                               minR2 = self.minR2, maxCoef = self.maxCoef,
                               maxVIF = self.maxVIF, minJB = self.minJB,
                               minMI = self.minMI, silent = self.neighborWarn)

            #### Loop Through All Combinations ####
            modelCount = 0
            emptyTabValues = [""] * ( self.maxIndVars - choose )
            perfectMultiModels = []
            for combo in comboGenerator:
                #### Create Design Matrix for Given Combination ####
                columns = [0] + list(combo)
                comboX = self.x[0:,columns]

                #### Get Model Info for given Combination ####
                N, K = comboX.shape
                varNameList = [ self.independentVars[j-1] for j in combo ]
                varNameListInt = ["Intercept"] + varNameList
                modelAll = self.dependentVar + " ~ "
                modelAll += " + ".join(varNameListInt)
                modelID = str(K) + ":" + str(modelCount)

                #### Run Linear Regression ####
                runModel = self.calculate(comboX)

                #### Set Near/Perfect Multicoll Bool ####
                nearPerfectBool = False
                if K > 2 and runModel:
                    nearPerfectBool = NUM.any(abs(self.vifVal) >= 1000)

                if (not runModel) or nearPerfectBool:
                    #### Perfect Multicollinearity ####
                    #### Unable to Invert the Matrix ####
                    perfectMultiModels.append(modelAll)

                else:
                    #### Keep Track of Total Number of Models Ran ####
                    modelCount += 1
                    self.sumRuns += 1
                    residuals = self.residuals.flatten()

                    #### Evaluate p-values ####
                    if self.BPProb < .1:
                        #### Use Robust Coefficients ####
                        pValsOut = self.pValsRob[1:]
                    else:
                        pValsOut = self.pVals[1:]
                    coefOut = self.coef[1:]

                    #### Process Largest VIF Values ####
                    if K > 2:
                        for ind, varName in enumerate(varNameList):
                            vif = self.vifVal[ind]
                            previousVIF = self.globalVifVals[varName]
                            if vif > previousVIF:
                                self.globalVifVals[varName] = vif

                    #### Set OLS Result ####
                    res = OLSResult(modelID, varNameList, coefOut, pValsOut,
                                    self.vifVal, self.r2Adj, self.aicc,
                                    self.JBProb, self.BPProb,
                                    allMIPass = self.allMIPass)

                    #### Evaluate Jarque-Bera Stat ####
                    keep = self.pushPopJB(res, self.residuals.flatten())

                    boolReport = rh.evaluateResult(res, residuals, keep = keep)
                    r2Bool, pvBool, vifBool, jbBool, giBool, keepBool = boolReport

                    #### Populate Output Table ####
                    if self.outputTable:
                        lesserKeepModel = pvBool and vifBool
                        if lesserKeepModel:
                            #### Set VIF/Moran's I for Table ####
                            maxVIFValue = res.maxVIFValue
                            giPVal = res.miPVal
                            if giPVal == None or self.allMIPass:
                                giPVal = self.nullValue

                            #### Create List of Results ####
                            countPlus = tableReportCount + 1
                            resultValues = [countPlus, self.r2Adj,
                                            self.aicc, self.JBProb,
                                            self.BPProb, maxVIFValue,
                                            giPVal, choose]
                            resultValues += varNameList
                            resultValues += emptyTabValues
                            self.tableResults.append(resultValues)
                            self.model2Table[modelID] = tableReportCount
                            tableReportCount += 1

                    #### Add Booleans for End Total Summary ####
                    boolResult = [r2Bool, pvBool, vifBool, jbBool]
                    self.boolResults += boolResult

                    #### Delete OLS Instance if Not Necessary For Summary ####
                    if not keepBool:
                        del res


            #### Run Moran's I for Highest Adj. R2 ####
            r2ResultList = rh.runR2Moran()
            self.neighborWarn = True

            #### Update Output Table Moran Value ####
            if self.outputTable and not self.allMIPass:
                for id, pvalue in r2ResultList:
                    try:
                        tableIndex = self.model2Table[id]
                        self.tableResults[tableIndex][6] = pvalue
                    except:
                        pass

            #### Add Results to Report File ####
            result2Print = rh.report()
            if self.outputReportFile:
                fo.write(result2Print.encode('utf-8'))
            if len(perfectMultiModels):
                self.perfectMultiWarnBool = True
                ARCPY.AddIDMessage("WARNING", 1304)
                for modelStr in perfectMultiModels:
                    ARCPY.AddIDMessage("WARNING", 1176, modelStr)

            #### Add Choose Run to Result Dictionary ####
            self.resultDict[choose] = rh

        #### Run Moran's I on Best Jarque-Bera ####
        self.createJBReport()

        #### Final Moran Stats ####
        self.getMoranStats()

        #### Create Output Table ####
        if self.outputTable:
            self.createOutputTable()

        #### Ending Summary ####
        self.endSummary()
        if self.outputReportFile:
            fo.write(self.fullReport.encode('utf-8'))
            fo.close()

    def createOutputTable(self):
        """Create output table for a given set of results."""

        #### Message and Progressor ####
        msg = ARCPY.GetIDMessage(84008)
        ARCPY.AddMessage(msg)
        ARCPY.SetProgressor("default", msg)

        #### Create/Finalize Output Table Name ####
        UTILS.createOutputTable(self.outputTable, self.outFieldNames,
                                self.outFieldTypes, self.tableResults)

    def getMoranStats(self):
        self.sumMoranRuns = 0
        self.sumMoranPass = 0
        miValues = []
        miModels = []
        for resKey, resHandler in self.resultDict.iteritems():
            for olsKey, olsRes in resHandler.olsResults.iteritems():
                miValue = olsRes.miPVal
                if miValue != None:
                    if len(miValues) < 3:
                        miValues.append(miValue)
                        miModels.append(olsRes)
                    else:
                        minIndex = NUM.argsort(miValues)[0]
                        minValue = miValues[minIndex]
                        if minValue < miValue:
                            miValues[minIndex] = miValue
                            miModels[minIndex] = olsRes
                    self.sumMoranRuns += 1
                    if miValue > self.minMI:
                        self.sumMoranPass += 1

        miOrder = list(NUM.argsort(miValues))
        miOrder.reverse()
        self.miReportRows = []
        for miIndex in miOrder:
            miResult = miModels[miIndex]
            self.miReportRows.append(miResult.report(orderType = 2))

    def createJBReport(self):
        self.jbReportRows = []
        sortIndex = NUM.argsort(self.jbValues).tolist()
        sortIndex.reverse()
        for ind in sortIndex:
            olsRes = self.jbModels[ind]
            if olsRes.miPVal == None:
                if not self.allMIPass:
                    residuals = self.jbResiduals[:,ind].flatten()
                    mi = runMoransI(self.ssdo, residuals, self.weightsMatrix,
                                    weightsType = self.weightsType)
                    miPVal = mi.pVal
                else:
                    miPVal = 1.0
                olsRes.setMoransI(miPVal)

            olsOut = olsRes.report(orderType = 1)
            self.jbReportRows.append(olsOut)

            #### Update Output Table Moran Value ####
            if self.outputTable:
                try:
                    tableIndex = self.model2Table[olsRes.id]
                    self.tableResults[tableIndex][6] = olsRes.miPVal
                except:
                    pass


    def pushPopJB(self, olsRes, residuals):
        """Keeps track of the best (highest) Jarque-Bera p-values."""
        lenRes = len(self.jbValues)
        keep = False
        if lenRes < 3:
            self.jbValues.append(self.JBProb)
            self.jbModels.append(olsRes)
            self.jbResiduals[:,lenRes] = residuals
            keep = True
        else:
            minIndex = NUM.argsort(self.jbValues)[0]
            minValue = self.jbValues[minIndex]
            if minValue < self.JBProb:
                self.jbValues[minIndex] = self.JBProb
                self.jbModels[minIndex] = olsRes
                self.jbResiduals[:,minIndex] = residuals
                keep = True
        return keep

    def endSummary(self):
        """Creates End Summary for Report File."""

        #### Passing Model Global Summary ####
        passHeader = ARCPY.GetIDMessage(84294)
        emptyValue = ARCPY.GetIDMessage(84092)
        perfectMultiStr = ARCPY.GetIDMessage(84368)
        perfectInterStr = ARCPY.GetIDMessage(84369)
        perfectInterStr += " (%s)" % LOCALE.format("%0.2f", 100)

        passResults = [ [ARCPY.GetIDMessage(84295),
                         ARCPY.GetIDMessage(84296),
                         ARCPY.GetIDMessage(84297),
                         ARCPY.GetIDMessage(84298),
                         ARCPY.GetIDMessage(84299)] ]

        cutoffList = [ "> " + UTILS.formatValue(self.minR2, "%0.2f"),
                       "< " + UTILS.formatValue(self.maxCoef, "%0.2f"),
                       "< " + UTILS.formatValue(self.maxVIF, "%0.2f"),
                       "> " + UTILS.formatValue(self.minJB, "%0.2f"),
                       "> " + UTILS.formatValue(self.minMI, "%0.2f") ]

        categories = [ARCPY.GetIDMessage(84300), ARCPY.GetIDMessage(84301),
                      ARCPY.GetIDMessage(84302), ARCPY.GetIDMessage(84303),
                      ARCPY.GetIDMessage(84304)]

        boolPerc = [ returnPerc(i, self.sumRuns) for i in self.boolResults ]
        boolPerc.append( returnPerc(self.sumMoranPass, self.sumMoranRuns) )
        boolOut = list(self.boolResults) + [self.sumMoranPass]
        sumOut = [ self.sumRuns for i in self.boolResults ]
        sumOut += [self.sumMoranRuns]

        for ind, category in enumerate(categories):
            outValue = LOCALE.format("%0.2f", boolPerc[ind])
            outCutoff = cutoffList[ind]
            outTrial = sumOut[ind]
            outCount = boolOut[ind]
            passResults.append( [category, outCutoff, outTrial,
                                 outCount, outValue] )

        self.passReport = UTILS.outputTextTable(passResults,
                                        header = passHeader,
                                        pad = 1, justify = "right")

        ##### Variable Significance and VIF Reports ####
        ##### Create Table Headers ####
        signHeader = ARCPY.GetIDMessage(84305)
        vifHeader = ARCPY.GetIDMessage(84306)

        #### Create Column Labels and Result Lists ####
        signColInfo = [ [ARCPY.GetIDMessage(84068), ARCPY.GetIDMessage(84307),
                         ARCPY.GetIDMessage(84366), ARCPY.GetIDMessage(84367)] ]
        signResults = []
        vifResults = [ [ARCPY.GetIDMessage(84068), ARCPY.GetIDMessage(84284),
                        ARCPY.GetIDMessage(84308), ARCPY.GetIDMessage(84309)] ]

        ##### Get Covariate Total ####
        percVarRes = []
        totalTogether = 0
        for resultKey, result in self.resultDict.iteritems():
            totalTogether += result.eachAppears

        ##### Populate Result Lists ####
        for ind, varName in enumerate(self.independentVars):
            totalNeg = 0
            totalPos = 0
            totalSign = 0
            totalRan = 0
            totalViolations = 0
            totalCovariates = COLL.defaultdict(int)
            for resultKey, result in self.resultDict.iteritems():
                #### Significance Results ####
                numRan, numSign = result.signDict[varName]
                totalSign += numSign
                totalRan += numRan
                numNeg, numPos = result.varSignDict[varName]
                totalNeg += numNeg
                totalPos += numPos

                #### VIF Results ####
                numViolate, covariates = result.vifDict[varName]
                totalViolations += numViolate
                for covariate in covariates:
                    if covariate != varName:
                        totalCovariates[covariate] += 1

            #### Add Perfect Multicollinearity Results * ####
            successfulRun = totalRan > 0

            #### Complete Significance Row ####
            if successfulRun:
                percentSign = ((totalSign * 1.0) / totalRan) * 100.0
                percentNeg = ((totalNeg * 1.0) / totalRan) * 100.0
                percentPos = ((totalPos * 1.0) / totalRan) * 100.0
                rowRes = [varName, LOCALE.format("%0.2f", percentSign),
                          LOCALE.format("%0.2f", percentNeg),
                          LOCALE.format("%0.2f", percentPos)]
            else:
                percentSign = -1.0
                rowRes = [varName, emptyValue, emptyValue, emptyValue]

            ind2Insert = None
            if len(percVarRes):
                for ind, percVal in enumerate(percVarRes):
                    if percVal < percentSign:
                        ind2Insert = ind
                        break
            if ind2Insert == None:
                percVarRes.append(percentSign)
                signResults.append(rowRes)
            else:
                percVarRes.insert(ind2Insert, percentSign)
                signResults.insert(ind2Insert, rowRes)

            #### Complete VIF Row ####
            if successfulRun:
                if self.printVIF:
                    globalVIF = self.globalVifVals[varName]
                    if abs(globalVIF) >= 1000:
                        globalVIFOut = "> " + LOCALE.format("%0.2f", 1000.)
                    else:
                        globalVIFOut = LOCALE.format("%0.2f", globalVIF)
                else:
                    globalVIFOut = emptyValue

                coString = []
                sortedCovariates = sorted(totalCovariates.iteritems(),
                                          key=OP.itemgetter(1),
                                          reverse=True)
                for covariate, totalTimes in sortedCovariates:
                    tRatio = (totalTimes/totalTogether) * 100
                    tRatio = LOCALE.format("%0.2f", tRatio)
                    coString.append(covariate + " (" + str(tRatio) + ")")
                if len(coString):
                    coString = ", ".join(coString)
                else:
                    coString = emptyValue
                vifRes = [varName, globalVIFOut, "%i" % totalViolations, coString]
            else:
                vifRes = [varName, emptyValue, perfectMultiStr, perfectInterStr]
            vifResults.append(vifRes)

        #### Create Report Tables ####
        signResults = signColInfo + signResults
        self.signReport = UTILS.outputTextTable(signResults,
                                                header = signHeader,
                                                justify = ["left", "right",
                                                           "right", "right"],
                                                pad = 1)

        if self.perfectMultiWarnBool:
            vifHeader += ARCPY.GetIDMessage(84111)
        self.vifReport = UTILS.outputTextTable(vifResults, header = vifHeader,
                                               justify = ["left", "right",
                                                          "center", "left"],
                                               pad = 1)

        #### Add Perfect Multi Warning ####
        if self.perfectMultiWarnBool:
            msg = ARCPY.GetIDMessage(84409) + "\n" + ARCPY.GetIDMessage(84410)
            self.vifReport += msg


        ##### Residual Normality Summary ####
        jbHeader = ARCPY.GetIDMessage(84310)
        jbResults = [ [ARCPY.GetIDMessage(84042), ARCPY.GetIDMessage(84021),
                       ARCPY.GetIDMessage(84249), ARCPY.GetIDMessage(84036),
                       ARCPY.GetIDMessage(84284), ARCPY.GetIDMessage(84292),
                       ARCPY.GetIDMessage(84286)] ]
        jbResults += self.jbReportRows
        self.jbReport = UTILS.outputTextTable(jbResults, header = jbHeader,
                                          pad = 1, justify = masterJustify)

        ##### Residual Autocorrelation ####
        if not self.allMIPass:
            miHeader = ARCPY.GetIDMessage(84311)
            miResults = [ [ARCPY.GetIDMessage(84292), ARCPY.GetIDMessage(84021),
                           ARCPY.GetIDMessage(84249), ARCPY.GetIDMessage(84042),
                           ARCPY.GetIDMessage(84036), ARCPY.GetIDMessage(84284),
                           ARCPY.GetIDMessage(84286)] ]
            miResults += self.miReportRows
            justify = ["right"] * 6 + ["left"]
            self.miReport = UTILS.outputTextTable(miResults, header = miHeader,
                                              pad = 1, justify = masterJustify)
        else:
            self.miReport = "\n" + ARCPY.GetIDMessage(84311)
            self.miReport += " (" + ARCPY.GetIDMessage(84500) + ")\n"

        #### Significance Locale String ####
        decimalSep = UTILS.returnDecimalChar()
        modelString2 = ARCPY.GetIDMessage(84314)
        if decimalSep == ".":
            numSep = ","
        else:
            numSep = ";"
        modelString2 = modelString2.format(LOCALE.format("%0.2f", .1), numSep,
                                           LOCALE.format("%0.2f", .05),
                                           LOCALE.format("%0.2f", .01))

        ##### Abbreviation Table ####
        modelStrip = ARCPY.GetIDMessage(84286).strip()
        abbHeader = ARCPY.GetIDMessage(84312)
        modelString1 = ARCPY.GetIDMessage(84313)
        abbResults = [ [ARCPY.GetIDMessage(84021),ARCPY.GetIDMessage(84315)],
                       [ARCPY.GetIDMessage(84249),ARCPY.GetIDMessage(84316)],
                       [ARCPY.GetIDMessage(84042),ARCPY.GetIDMessage(84317)],
                       [ARCPY.GetIDMessage(84036),ARCPY.GetIDMessage(84318)],
                       [ARCPY.GetIDMessage(84284),ARCPY.GetIDMessage(84319)],
                       [ARCPY.GetIDMessage(84292),ARCPY.GetIDMessage(84320)],
                       [modelStrip, modelString1],
                       [modelStrip, modelString2]]

        self.abbReport = UTILS.outputTextTable(abbResults)
        self.abbReport = "\n" + abbHeader + "\n" + self.abbReport + "\n"

        ##### Display Tables ####
        starMess = "*" * 78
        dashMess = "-" * 78
        ARCPY.AddMessage(starMess)
        globalHeader = ARCPY.GetIDMessage(84321)
        globalHeader = globalHeader.format(self.dependentVar)
        globalHeader = globalHeader.center(78, "*")
        ARCPY.AddMessage(globalHeader)
        ARCPY.AddMessage(self.passReport)
        ARCPY.AddMessage(dashMess)
        ARCPY.AddMessage(self.signReport)
        ARCPY.AddMessage(dashMess)
        ARCPY.AddMessage(self.vifReport)
        ARCPY.AddMessage(dashMess)
        ARCPY.AddMessage(self.jbReport)
        ARCPY.AddMessage(dashMess)
        ARCPY.AddMessage(self.miReport)
        ARCPY.AddMessage(dashMess)
        ARCPY.AddMessage(self.abbReport)
        ARCPY.AddMessage(dashMess)
        self.fullReport = [starMess, globalHeader, self.passReport,
                           dashMess, self.signReport,
                           dashMess, self.vifReport,
                           dashMess, self.jbReport,
                           dashMess, self.miReport,
                           dashMess, self.abbReport,
                           dashMess]
        self.fullReport = "\n".join(self.fullReport)

    def calculate(self, comboX):
        """Performs OLS and related diagnostics."""

        #### Shorthand Attributes ####
        ssdo = self.ssdo
        x = comboX
        n, k = NUM.shape(comboX)
        y = self.y

        #### General Information ####
        fn = n * 1.0
        dof = n - k
        fdof = dof * 1.0
        xt = x.T
        yt = y.T
        xx = NUM.dot(xt, x)

        #### Check for Perfect Multicollinearity ####
        U, s, V = LA.svd(xx)
        if UTILS.compareFloat(0.0, s[-1]):
            return False

        #### Attempt to Invert Design Matrix ####
        try:
            xxi = LA.inv(xx)
        except:
            #### Perfect multicollinearity, cannot proceed ####
            return False

        #### Bad Probabilities - Near Multicollinearity ####
        badProbs = False

        #### Compute Coefficients ####
        xy = NUM.dot(xt, y)
        coef = NUM.dot(xxi, xy)

        #### Residuals, Sum Of Squares, R2, Etc. ####
        yHat = NUM.dot(x, coef)
        yBar = (y.sum())/fn
        e = y - yHat
        ess = ( NUM.dot(e.T, e) )[0][0]
        s2 = (ess / fdof)
        s2mle = (ess / fn)
        seResiduals = NUM.sqrt(s2)
        ss = y - yBar
        tss = ( NUM.dot(ss.T, ss) )[0][0]
        r2 = 1.0 - (ess/tss)
        r2Adj =  1.0 - ( (ess / (fdof)) / (tss / (fn-1)) )
        u2 = e * e

        #### Variance-Covariance for Coefficients ####
        varBeta = xxi * s2

        #### Standard Errors / t-Statistics ####
        seBeta = NUM.sqrt(varBeta.diagonal())
        tStat = (coef.T / seBeta).flatten()

        #### White's Robust Standard Errors ####
        dofScale =  ( n / (n - k) ) * 1.0
        sHat = NUM.dot((u2 * x).T, x) * dofScale
        varBetaRob = NUM.dot(NUM.dot(xxi, sHat), xxi)
        seBetaRob =  NUM.sqrt(varBetaRob.diagonal())
        tStatRob = (coef.T / seBetaRob).flatten()

        #### DOF Warning Once for t-Stats ####
        silentVector = [ True for i in range(k) ]
        if (2 <= dof <= 4) and not self.warnedTProb:
            silentVector[0] = False
            self.warnedTProb = True

        #### Coefficient t-Tests ####
        pVals = []
        pValsRob = []
        for varInd in xrange(k):
            #### General ####
            try:
                p = STATS.tProb(tStat[varInd], dof, type = 2,
                                silent = silentVector[varInd])
            except:
                p =  NUM.nan
                badProbs = True
            pVals.append(p)

            #### Robust ####
            try:
                p = STATS.tProb(tStatRob[varInd], dof, type = 2,
                                silent = True)
            except:
                p =  NUM.nan
                badProbs = True
            pValsRob.append(p)

        #### Jarque-Bera Test For Normality of the Residuals ####
        muE = (e.sum()) / fn
        devE = e - muE
        u3 = (devE**3.0).sum() / fn
        u4 = (devE**4.0).sum() / fn
        denomS = s2mle**1.5
        denomK = s2mle**2.0
        skew = u3 / denomS
        kurt = u4 / denomK
        self.JB = (n/6.) * ( skew**2. + ( (kurt - 3.)**2. / 4. ))
        if self.JB >= 0.0:
            self.JBProb = STATS.chiProb(self.JB, 2, type = 1)
        else:
            self.JBProb = NUM.nan
            badProbs = True

        #### Breusch-Pagan Test for Heteroskedasticity ####
        u2y = NUM.dot(xt, u2)
        bpCoef = NUM.dot(xxi, u2y)
        u2Hat = NUM.dot(x, bpCoef)
        eU = u2 - u2Hat
        essU = NUM.dot(eU.T, eU)
        u2Bar = (u2.sum()) / fn
        ssU = u2 - u2Bar
        tssU = NUM.dot(ssU.T, ssU)
        r2U = 1.0 - (essU/tssU)
        self.BP = (fn * r2U)[0][0]
        if self.BP >= 0.0:
            self.BPProb = STATS.chiProb(self.BP, (k-1), type = 1)
        else:
            self.BPProb = NUM.nan
            badProbs = True

        #### Classic Joint-Hypothesis F-Test ####
        q = k - 1
        fq = q * 1.0
        self.fStat = (r2/fq) / ((1 - r2) / (fn - k))
        try:
            self.fProb = abs(STATS.fProb(self.fStat, q,
                                      (n-k), type = 1))
        except:
            self.fProb = NUM.nan
            badProbs = True

        #### Wald Robust Joint Hypothesis Test ####
        R = NUM.zeros((q,k))
        R[0:,1:] = NUM.eye(q)
        Rb = NUM.dot(R, coef)

        try:
            invRbR = LA.inv( NUM.dot(NUM.dot(R, varBetaRob), R.T) )
        except:
            #### Perfect multicollinearity, cannot proceed ####
            return False

        self.waldStat = ( NUM.dot(NUM.dot(Rb.T, invRbR), Rb) )[0][0]
        if self.waldStat >= 0.0:
            self.waldProb = STATS.chiProb(self.waldStat, q, type = 1)
        else:
            self.waldProb = NUM.nan
            badProbs = True

        #### Log-Likelihood ####
        self.logLik = -(n / 2.) * (1. + NUM.log(2. * NUM.pi)) - \
                       (n / 2.) * NUM.log(s2mle)

        #### AIC/AICc ####
        k1 = k + 1
        self.aic = -2. * self.logLik + 2. * k1
        self.aicc = -2. * self.logLik + 2. * k1 * (fn / (fn - k1 - 1))

        #### Calculate the Variance Inflation Factor ####
        if k <= 2:
            self.vifVal = ARCPY.GetIDMessage(84090)
            self.vif = False
        else:
            xTemp = xt[1:]
            corX = NUM.corrcoef(xTemp)
            try:
                ic = LA.inv(corX)
                self.vifVal = abs(ic.diagonal())
                self.vifVal[self.vifVal >= 1000] = 1000
                self.vif = True
            except:
                #### Perfect multicollinearity, cannot proceed ####
                return False

        #### Set Attributes ####
        self.dof = dof
        self.coef = coef
        self.yHat = yHat
        self.yBar = yBar
        self.residuals = e
        self.seResiduals = seResiduals
        self.stdRedisuals = e / self.seResiduals
        self.ess = ess
        self.tss = tss
        self.varCoef = varBeta
        self.seCoef = seBeta
        self.tStats = tStat
        self.pVals = pVals
        self.varCoefRob = varBetaRob
        self.seCoefRob = seBetaRob
        self.tStatsRob = tStatRob
        self.pValsRob = pValsRob
        self.r2 = r2
        self.r2Adj = r2Adj
        self.s2 = s2
        self.s2mle = s2mle
        self.q = q
        self.badProbs = badProbs
        self.varLabels = [ARCPY.GetIDMessage(84064)] + self.independentVars

        return True

if __name__ == '__main__':
    er = runExploratoryRegression()



