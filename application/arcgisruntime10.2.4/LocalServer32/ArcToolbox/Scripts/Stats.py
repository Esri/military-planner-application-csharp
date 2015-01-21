"""
 Source Name:   Stats.py
 Version:       ArcGIS 10.1
 Author:        Environmental Systems Research Institute Inc.
 Description:   Probability Helper Functions
"""

################### Imports ########################
import arcgisscripting as ARC
import arcpy as ARCPY
import numpy as NUM

################### Methods ########################

def tProb(t, dof, type = 0, silent = False):
    """Calculates the area under the curve of the studentized-t
    distribution. (A)
    
    INPUTS:
    t (float): t-statistic
    dof (int): degrees of freedom
    type {int, 0}: {0,1,2} (See (1))

    NOTES: 
    (1) 0 = area under the curve to the left
        1 = area under the curve to the right
        2 = two-tailed test

    REFERENCES:
    (A) Source - Algorithm AS 27: Applied Statistics, Vol. 19(1), 1970
    """

    if dof <= 1:
        #### Must Have More Than One Degree of Freedom ####
        ARCPY.AddIDMessage("ERROR", 1128, 1)
        raise SystemExit()
    else:
        if (2 <= dof <= 4) and not silent:
            #### Warn if Less Than Five Degrees of Freedom ####
            ARCPY.AddIDMessage("WARNING", 1130)
    
    return ARC._ss.t_prob(t, dof, type)

def zProb(x, type = 0):
    """Calculates the area under the curve of the standard normal
    distribution. (A)

    INPUTS:
    z (float): z-statistic
    type {int, 0}: {0,1,2} (See (1))

    NOTES: 
    (1) 0 = area under the curve to the left
        1 = area under the curve to the right
        2 = two-tailed test

    REFERENCES:
    (A) Algorithm AS 66: Applied Statistics, Vol. 22(3), 1973
    """

    return ARC._ss.z_prob(x, type)

def chiProb(x, dof, type = 0):
    """Calculates the area under the curve for the chi-squared 
    distribution. (A)

    INPUTS:
    x (float): t-statistic
    dof (int): degrees of freedom
    type {int, 0}: {0,1} (See (1))

    NOTES: 
    (1) 0 = area under the curve to the left
        1 = area under the curve to the right
    
    REFERENCES:
    (A) Algorithm 299: Communications of the ACM, Vol. 10(4), 1967
    """

    bigX = 18. # based on simulations
    if x < 0:
        #### No Negative Values ####
        ARCPY.AddIDMessage("ERROR", 1131)
        raise SystemExit()
    if dof < 1: 
        #### Must Have More Than One Degree of Freedom ####
        ARCPY.AddIDMessage("ERROR", 1128, 1)
        raise SystemExit()
    a = 0.5 * x
    if a > bigX:
        y = 0.0
    else:
        y = NUM.exp(-a)
    if dof%2 == 0: 
        even = 1
    else:
        even = 0
    if even:
        s = y
    else:
        s = 2.0 * zProb( -NUM.sqrt(x))
    if dof == 1:
        pvalue = s
    else:
        x = .5 * (dof - 1.0)
        if even:
            z = 1.0
        else:
            z = 0.5
        if a > bigX:
            if even:
                e = 0.0
            else:
                e = 0.572364942925
            c = NUM.log(a)
            while z <= x:
                e = NUM.log(z) + e
                s = NUM.exp( (c*z) - a - e ) + s
                z += 1.0
            pvalue = s
        else:
            if even:
                e = 1.0
            else:
                e = 0.564189583548 / NUM.sqrt(a)
            c = 0
            while z <= x:
                e = e * (a/z)
                c = c + e
                z += 1.0
            pvalue = (c * y) + s
    
    if not type:
        pvalue = 1 - pvalue
        
    return pvalue

def fProb(x, m, n, type = 0):
    """Calculates the area under the curve for the F-distribution. (A)
    
    INPUTS:
    m (int): degrees of freedom
    n (int): degrees of freedom
    type {int, 0}: {0,1} (See (1))

    OUTPUT:
    x (float): F-test statistic

    NOTES: 
    (1) 0 = area under the curve to the left
        1 = area under the curve to the right

    REFERENCES: 
    (A) Algorithm 322: Communications of the ACM, Vol. 11(2), 1968
    """

    mf = 1.0 * m
    nf = 1.0 * n
    a = 2 * (m / 2) - m + 2
    b = 2 * (n / 2) - n + 2
    w = x * (mf/nf)
    z = 1.0 / (1.0+w)
    if a == 1:
        if b == 1:
            p = NUM.sqrt(w)
            y = 0.3183098862
            d = y * z / p
            p = 2 * y * NUM.arctan(p)
        else:
            p = NUM.sqrt(w*z)
            d = 0.5 * p * z / w
    else:
        if b == 1:
            p = NUM.sqrt(z)
            d = 0.5 * z * p
            p = 1 - p
        else:
            d = z * z
            p = w * z
    y = 2.0 * w / z
    j = b + 2
    while j <= n:
        d = (1 + (1.*a) / (j - 2)) * d * z
        if a == 1:
            p = p + d * y / (j - 1)
        else:
            p = (p + w) * z 
        j += 2
    y = w * z
    z = 2.0 / z
    b = n - 2
    i = a + 2
    while i <= m:
        j = i + b
        d = y * d * j / (i - 2)
        p = p - z * d / j
        i += 2
    if type == 1:
        p = 1.0 - p
    return p

def qNorm(p):
    """
    Lower tail quantile for standard normal distribution function. (A)

    INPUTS:
    p (float): probability value

    OUTPUT:
    q (float): quantile value

    REFERENCES: 
    (A) Dan Field's python adaption of Peter Acklam's code:
           
        http://home.online.no/~pjacklam/notes/invnorm/#Other_algorithms

    ORIGINAL NOTES:    

        Modified from the author's original perl code (original comments
        follow below) by dfield@yahoo-inc.com.  May 3, 2004.

        This function returns an approximation of the inverse cumulative
        standard normal distribution function.  I.e., given P, it returns
        an approximation to the X satisfying P = Pr{Z <= X} where Z is a
        random variable from the standard normal distribution.

        The algorithm uses a minimax approximation by rational functions
        and the result has a relative error whose absolute value is less
        than 1.15e-9.

        Author:      Peter J. Acklam
        Time-stamp:  2000-07-19 18:26:14
        E-mail:      pjacklam@online.no
        WWW URL:     http://home.online.no/~pjacklam
    """

    if p <= 0 or p >= 1:
        #### No Negative Values ####
        ARCPY.AddIDMessage("ERROR", 1129)
        raise SystemExit()

    #### Coefficients in rational approximations ####
    a = (-3.969683028665376e+01,  2.209460984245205e+02, \
         -2.759285104469687e+02,  1.383577518672690e+02, \
         -3.066479806614716e+01,  2.506628277459239e+00)
    b = (-5.447609879822406e+01,  1.615858368580409e+02, \
         -1.556989798598866e+02,  6.680131188771972e+01, \
         -1.328068155288572e+01 )
    c = (-7.784894002430293e-03, -3.223964580411365e-01, \
         -2.400758277161838e+00, -2.549732539343734e+00, \
          4.374664141464968e+00,  2.938163982698783e+00)
    d = ( 7.784695709041462e-03,  3.224671290700398e-01, \
          2.445134137142996e+00,  3.754408661907416e+00)

    #### Define break-points ####
    plow  = 0.02425
    phigh = 1 - plow

    #### Rational approximation for lower region ####
    if p < plow:
       q  = NUM.sqrt(-2*NUM.log(p))
       return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)

    #### Rational approximation for upper region ####
    if phigh < p:
       q  = NUM.sqrt(-2*NUM.log(1-p))
       return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)

    #### Rational approximation for central region ####
    q = p - 0.5
    r = q*q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)

def pseudoPValue(testStat, permValues):
    numPerms = len(permValues)
    numLarger = (permValues >= testStat).sum()
    if (numPerms - numLarger) < numLarger:
        numSmaller = (permValues <= testStat).sum()
        pValue = ((numSmaller + 1.0) * 2.0) / (numPerms + 1.0)
    else:
        pValue = ((numLarger + 1.0) * 2.0) / (numPerms + 1.0)

    return pValue

######################## Inequality Measures ##########################

class TheilsT(object):
    """Calculates the Classic Theil's T Index of Inequality.

    INPUTS:
    values (array): nxk variable(s) to calculate the index on.

    ATTRIBUTES:
    T (float): Theil's T Index for given variables
    n (int): number of observations
    k {int, None}: number of fields/variables
    sumVals (float): sum of all the values in each column
    meanVals (float): mean of all values in each column
    """

    def __init__(self, values):
        shapeVals = values.shape
        if len(shapeVals) > 1:
            n,k = shapeVals
        else:
            n = shapeVals[0]
            k = 1

        sumVals = values.sum(0) * 1.0
        propSum = values / sumVals
        meanVals = values.mean(0)
        logNMean = NUM.log(n*propSum)
        meanLogMean = propSum*logNMean
        self.T = meanLogMean.sum(0)
        self.values = values
        self.sumVals = sumVals
        self.meanVals = meanVals
        self.n = n
        self.k = k

    def decompose(self, partition):
        uniqueParts = NUM.unique(partition)
        nParts = len(uniqueParts)
        between = NUM.zeros((nParts, self.k))
        c = 0
        for part in uniqueParts:
            partVals = self.values[NUM.where(partition == part)]
            nPart = len(partVals)
            nRatio = nPart / (self.n * 1.0)
            valRatio = partVals.sum(0) / self.sumVals
            between[c] = nRatio * NUM.log( nRatio / valRatio )
            c += 1
        between = between.sum(0)
        self.within = self.T - between
        self.between = between


################## Transformations ######################

def zTransform(x):
    return (x - x.mean(0)) / x.std(0)

def fdrTransform(pVals, rawVals):
    n = len(pVals)
    order = pVals.argsort()
    reverseOrder = NUM.empty((n,), int)
    reverseOrder[:] = order[::-1]
    adjustedCutoffs = NUM.arange(1, (n+1)) / (n * 1.0)
    adjustedCutoffs.shape = n,1
    cutoffs = NUM.array([.1, .05, .01])
    adjustedCutoffs = NUM.multiply(adjustedCutoffs, cutoffs)
    finalCutoffs = NUM.empty((n,3), float)
    finalCutoffs[:] = adjustedCutoffs[::-1]
    
    #### Internal Method Expects "Well-Behaved" Arrays ####
    return ARC._ss.fdr_adjusted_bins(rawVals, pVals, reverseOrder, finalCutoffs)

def pValueBins(pVals, rawVals):
    return ARC._ss.pvalue_bins(rawVals, pVals)

def moranBinFromPVals(pVals, moranInfo, fdrBins = None):
    """Returns a string representation of Local Moran's I 
    Cluster-Outlier classification bins.

    INPUTS:
    pVals (array, n): pvalues from local moran (or pseudo p-values)
    moranInfo (dict): orderID = (clustered?, 
                                 local greater than global mean?,
                                 feature greater than global mean?)
    fdrBins (array, n): fdr adjusted bins for significance

    OUTPUT:
    moranBin (str): HH = Cluster of Highs, L = Cluster of Lows,
                    HL = High Outlier, LH = Low Outlier.
    """
    n = len(pVals)
    bins = NUM.empty((n,), dtype = 'a2')
    bins[:] = ""
    if fdrBins != None:
        significant = NUM.where(abs(fdrBins) >= 2)
    else:
        significant = NUM.where(pVals <= .05)

    for orderID in significant[0]:
        clusterBool, localGlobalBool, featureGlobalBool = moranInfo[orderID]
        if clusterBool:
            if localGlobalBool:
                moranBin = "HH"
            else:
                moranBin = "LL"
        else:
            if featureGlobalBool and not localGlobalBool:
                moranBin = "HL"
            else:
                moranBin = "LH"
        bins[orderID] = moranBin

    return bins

################ Summary Statistics #####################

def median(values, weights = None):
    """Returns the weigthed median for univariate data.

    INPUTS:
    values (list): list of data values
    weights {list, None}: list of weights associated with values

    OUTPUT
    wMed (float): weighted median center
    """

    #### Assess Shape and Return if Single Feature ####
    n = len(values)
    if n == 1:
        return values[0]

    #### Assure Appropriate Weights ####
    try:
        wn = len(weights)
        if wn != n:
            weights = NUM.ones(n) 
    except:
        weights = NUM.ones(n)
    values = NUM.asarray(values)
    weights = NUM.asarray(weights)

    #### Remove Values with Zero Weights ####
    nonZeroW = NUM.flatnonzero(weights)
    weights = weights[nonZeroW]
    values = values[nonZeroW]
    numTotal = len(values)

    #### Sorting Values/Weights ####
    indSort = NUM.argsort(values)
    values = values[indSort]
    weights = weights[indSort]

    #### Create Weight Sums and Divide Sample ####
    cumulativeSumW = weights.cumsum()
    sumW = cumulativeSumW[-1]
    midW = sumW / 2.
    lowerHalf = (cumulativeSumW <= midW)
    numLower = lowerHalf.sum()

    #### Calculate Median ####
    if numLower == 0:
        wMed = values[0]
    elif numLower == numTotal:
        wMed = values[-1]
    else:
        lowerSumW = cumulativeSumW[numLower - 1]
        higherSumW = sumW - lowerSumW
        if higherSumW > midW:
            wMed = values[numLower]
        else:
            lowVal = lowerSumW * values[numLower - 1]
            highVal = higherSumW * values[numLower]
            wMed = (lowVal + highVal) / sumW

    return wMed
