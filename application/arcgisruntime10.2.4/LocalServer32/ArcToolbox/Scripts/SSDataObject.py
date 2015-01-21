"""
Source Name:   SSDataObject.py
Version:       ArcGIS 10.1
Author:        Environmental Systems Research Institute Inc.
Description:   Python virtual wrapper for feature classes in the context
               of spatial statistics script tools.  Incorporates Utility
               Functions from SSUtilities.py while maintaining
               characteristics of the input feature class.
               The geoprocessor is also included via composition.
"""

################### Imports ########################

import os as OS
import numpy as NUM
import arcgisscripting as ARC
import arcpy as ARCPY
import arcpy.management as DM
import arcpy.conversion as CONV
import arcpy.da as DA
import ErrorUtils as ERROR
import SSUtilities as UTILS
import locale as LOCALE
import gapy as GAPY
import WeightsUtilities as WU
import datetime as DT

################## Classes #########################

class CandidateField(object):
    """Contains information for a field that is a candidate to be added to an
    output feature class

    INPUTS:
    name (str): name of the field
    type (str): type of data {'Single', 'Double', 'Integer', etc...}
    data (array): 1-d array of values
    alias {str, None}: field alias
    length {int, None}: length of the field

    METHODS:
    report
    """

    def __init__(self, name, type, data = None, alias = None,
                 nullable = True, precision = None, scale = None,
                 length = None, required = False, domain = None):

        #### Set Initial Attributes ####
        UTILS.assignClassAttr(self, locals())

    def report(self, fileName = None):
        """Reports Field Information.

        INPUTS:
        fileName {str, None}: path to report text file
        """

        header = "Candidate Field Description"
        row1 = ["Field Name: ", self.name]
        row2 = ["Field Type: ", self.type]
        row3 = ["Field Alias: ", str(self.alias)]
        row4 = ["Field Length: ", str(self.length)]
        results =  [row1, row2, row3, row4]
        outputTable = UTILS.outputTextTable(results, header = header)
        if fileName:
            f = UTILS.openFile(fileName, "w")
            f.write(outputTable)
            f.close()
        else:
            ARCPY.AddMessage(outputTable)

    def copy2FC(self, outputFC):
        """Copies self to an output feature class.

        INPUTS:
        outputFC (str): path to output feature class
        """

        UTILS.addEmptyField(outputFC, self.name, self.type,
                            alias = self.alias,
                            nullable = self.nullable,
                            precision = self.precision,
                            scale = self.scale,
                            length = self.length,
                            required = self.required,
                            domain = self.domain)

class FCField(object):
    """Python representation of a database field to be organized and
    dispatched by SSDataObject.

    INPUTS: CandidateField
    fieldObject (obj): instance of a field object from ARCPY.ListFields(*)

    ATTRIBUTES:
    name (str): name of the field
    baseName (str): name of th field on disk, I.e. without table joins
    type (str): type of data {'Single', 'Double', 'Integer', etc...}
    length (int): length of the field

    METHODS:
    createDataArray: creates empty numpy arrays for field values.
    resizeDataArrays: resizes arrays to accounnt for bad records.
    """

    def __init__(self, fieldObject):
        self.name = fieldObject.name
        self.baseName = fieldObject.baseName
        self.type = fieldObject.type
        self.length = fieldObject.length
        self.fieldObject = fieldObject
        self.alias = fieldObject.aliasName
        self.nullable = fieldObject.isNullable
        self.precision = fieldObject.precision

    def createDataArray(self, numObs, dateStr = False):
        """Creates empty numpy arrays for field values.

        INPUTS:
        numObs (int): number of features
        """

        if UTILS.numpyConvert.has_key(self.type):
            myType = UTILS.numpyConvert[self.type]
            if self.type == "String":
                myType = myType % self.length
            if self.type == "Date":
                if dateStr:
                    myType = 'a64'
        else:
            myType = 'a64'

        self.data = NUM.empty((numObs,), dtype = myType)

    def copy2FC(self, outputFC, outName = None, setNullable = False):
        """Copies self to an output feature class.

        INPUTS:
        outputFC (str): path to output feature class
        outName (str): optional output field name (for joins and such.)
        setNullable (bool): if set to true, overwrite self to nullable
        """

        if outName == None:
            outName = self.name

        if setNullable:
            nullable = True
        else:
            nullable = self.nullable

        UTILS.addEmptyField(outputFC, outName, self.type,
                            alias = self.alias,
                            nullable = nullable,
                            precision = self.fieldObject.precision,
                            scale = self.fieldObject.scale,
                            length = self.fieldObject.length,
                            required = self.fieldObject.required,
                            domain = self.fieldObject.domain)

    def returnDouble(self):
        """Converts integers to doubles (NUM.float64) for analysis."""
        if self.type in ['SmallInteger', 'Integer']:
            return NUM.array(self.data, dtype = float)
        else:
            return self.data

class SSDataObject(object):
    """Spatial Statistics Data Object: Creates and keeps track of
    Feature Class information for scripts in the Spatial Statistics
    Toolbox.

    INPUTS:
    inputFC (str): catalogue path to the input feature class
    templateFC {str, None}: catalogue path to a template feature class (1)

    ATTRIBUTES:
    inPath (str): workspace
    inName (str): fileName
    info (object): result of GeoProcessor method
    catPath (str): catalogue path to the input feature class
    shapeType (str): type of feature class; I.e. Polygon, Point
    shapeField (str): name of the shapeField
    spatialRef (str): spatial reference
    oidName (str): name of the object ID field
    shapeFileBool (bool): is the input FC a shapefile?

    METHODS:
    setHiddenFields
    createOutputFieldMappings
    obtainData
    obtainDataGA
    output2NewFC

    NOTES:
    (1) the template feature class defines environment variables that affect
        reading/writing/calculating
    """

    def __init__(self, inputFC, templateFC = None, explicitSpatialRef = None,
                 silentWarnings = False, useChordal = True):
        #### Validate Input Feature Class ####
        ERROR.checkFC(inputFC)
        try:
            self.inPath, self.inName = OS.path.split(inputFC)
        except:
            self.inPath = None
            self.inName = inputFC

        #### Validate Template FC ####
        if templateFC != None:
            if ARCPY.Exists(templateFC) == False:
                templateFC = None

        #### ShapeFile Boolean ####
        self.shapeFileBool = False
        if self.inPath:
            self.shapeFileBool = UTILS.isShapeFile(inputFC)

            #### Create Feature Layer if LYR File ####
            path, ext = OS.path.splitext(inputFC)
            if ext.upper() == ".LYR":
                tempFC = "SSDO_FeatureLayer"
                DM.MakeFeatureLayer(inputFC, tempFC)
                inputFC = tempFC

        #### Describe Input ####
        self.info = ARCPY.Describe(inputFC)

        #### Assure Input are Features with OIDs ####
        if not self.info.hasOID:
            ARCPY.AddIDMessage("ERROR", 339, self.inName)
            raise SystemExit()

        #### Assign Describe Objects to Class Attributes ####
        self.inputFC = inputFC
        self.catPath = self.info.CatalogPath
        self.shapeType = self.info.ShapeType
        self.oidName = self.info.oidFieldName
        self.dataType = self.info.DataType
        self.shapeField = self.info.ShapeFieldName
        self.templateFC = templateFC
        self.hasM = self.info.HasM
        self.hasZ = self.info.HasZ
        self.silentWarnings = silentWarnings

        #### Set Initial Extent Depending on DataType ####
        if self.dataType in ["FeatureLayer", "Layer"]:
            try:
                tempInfo = ARCPY.Describe(self.catPath)
                extent = tempInfo.extent
            except:
                #### in_memory, SDE, NetCDF etc... ####
                extent = self.info.extent
            self.fidSet = self.info.FIDSet
            if self.fidSet == "":
                self.selectionSet = False
            else:
                self.selectionSet = True
        else:
            extent = self.info.extent
            self.fidSet = ""
            self.selectionSet = False
        self.extent = extent

        #### Set Spatial Reference ####
        inputSpatRef = self.info.SpatialReference
        inputSpatRefName = inputSpatRef.name
        if explicitSpatialRef:
            #### Explicitely Override Spatial Reference ####
            self.templateFC = None
            self.spatialRef = explicitSpatialRef
        else:
            #### 1. Feature Dataset, 2. Env Setting, 3. Input Hierarchy ####
            self.spatialRef = UTILS.returnOutputSpatialRef(inputSpatRef,
                                                  outputFC = templateFC)
        self.spatialRefString = UTILS.returnOutputSpatialString(self.spatialRef)
        self.spatialRefName = self.spatialRef.name
        self.spatialRefType = self.spatialRef.type

        #### Warn if Spatial Reference Changed ####
        if not silentWarnings:
            UTILS.compareSpatialRefNames(inputSpatRefName, self.spatialRefName)

        #### Check for Projection ####
        if self.spatialRefType.upper() != "PROJECTED":
            if self.spatialRefType.upper() == "GEOGRAPHIC":
                self.useChordal = useChordal
                if not explicitSpatialRef:
                    if self.useChordal:
                        ARCPY.AddIDMessage("WARNING", 1605)
                    else:
                        ARCPY.AddIDMessage("WARNING", 916)
            else:
                self.useChordal = False
                if not explicitSpatialRef:
                    ARCPY.AddIDMessage("WARNING", 916)
        else:
            self.useChordal = False

        #### Angular/Linear Unit Info ####
        self.distanceInfo = UTILS.DistanceInfo(self.spatialRef, 
                                         useChordalDistances = self.useChordal)

        #### Create Composition and Accounting Structure ####
        self.fields = {}
        self.master2Order = {}
        self.order2Master = {}

        #### Obtain a Full List of Field Names/Type ####
        self.allFields = {}
        listFields = self.info.fields
        for field in listFields:
            name = field.name.upper()
            self.allFields[name] = FCField(field)

        #### Set Z and M Flags and Defaults ####
        zmInfo = UTILS.setZMFlagInfo(self.hasM, self.hasZ, self.spatialRef)
        self.zFlag, self.mFlag, self.defaultZ = zmInfo
        self.zBool = self.zFlag == "ENABLED"

        #### Render Type ####
        self.renderType = UTILS.renderType[self.shapeType.upper()]

    def setHiddenFields(self):
        """Keeps track of all the fields in the input feature class that
        are not being used in analysis to prevent unnecessary copying to
        output feature class.

        ATTRIBUTES SET:
        hidden (list): list of field names disabled for output copy.
        """

        self.hidden = []
        for field in self.allFields:
            if not self.fields.has_key(field):
                self.hidden.append(field)

        self.hidden.remove(self.shapeField.upper())
        self.hidden.remove(self.oidName.upper())

    def createOutputFieldMappings(self, appendFields = None):
        """Creates field mapping for resulting output feature class.

        INPUTS:
        appendFields {list, None}: additional field names not used in analysis.

        OUTPUT:
        fieldMappings (obj): instance of FieldMappings()
        """

        #### Initialize Field Mapping ####
        fieldMappings = ARCPY.FieldMappings()

        #### Create Master Field Mapping ####
        if self.masterIsOID:
            masterFieldOutName = "Source_ID"
            masterFieldOutAlias = self.inName + "_" + masterFieldOutName
        else:
            masterFieldOutName = self.masterField
            masterFieldOutAlias = self.masterField
        masterMap = UTILS.createFieldMap

    def resizeDataArrays(self, goodRecs):
        """For the obtainData option only, removes bad records from arrays.

        INPUTS:
        goodRecs (int): number of good records (valid shape and data values)
        """

        for fieldName, fieldObj in self.fields.iteritems():
            self.fields[fieldName].data = fieldObj.data[0:goodRecs]

    def obtainDataGA(self, masterField, fields = [], types = [0,1,2,3,5,6],
                     minNumObs = 0, warnNumObs = 0):
        """Takes a list of field names and returns it in a dictionary
        structure.

        INPUTS:
        masterField (str): name of field being used as the master
        fields {list, []}: name(s) of the field to be returned
        types (list): types of data allowed to be returned (1)
        minNumObs {int, 0}: minimum number of observations for error
        warnNumObs {int, 0}: minimum number of observations for warning

        ATTRIBUTES:
        gaTable (structure): instance of the GA Table
        fields (dict): fieldName = instance of FCField
        master2Order (dict): masterID = order in lists
        order2Master (dict): order in lists = masterID
        masterField (str): field that serves as the master
        badRecords (list): master IDs that could not be read
        xyCoords (array, nunObs x 2): xy-coordinates for feature centroids

        NOTES:
        (1) No Text Fields; short [0], long [1], float [2], double[3]
        """

        #### Validation of Master Field ####
        verifyMaster = ERROR.checkField(self.allFields, masterField,
                                        types = [0,1,5])

        #### Set MasterIsOID Boolean ####
        self.masterIsOID = masterField == self.oidName

        #### Set Master and Data Indices ####
        if self.masterIsOID:
            self.masterColumnIndex = 0
            self.dataColumnIndex = 2
            fieldList = []
        else:
            self.masterColumnIndex = 2
            self.dataColumnIndex = 3
            fieldList = [masterField]

        #### Validation and Initialization of Data Fields ####
        numFields = len(fields)
        for field in fields:
            fType = ERROR.checkField(self.allFields, field, types = types)
            fieldList.append(field)
            self.fields[field] = self.allFields[field]

        #### ZCoords Are Last ####
        getZBool = self.hasZ and (not self.renderType)
        if getZBool:
            fieldList.append("SHAPE&Z")

        #### Create GA Data Structure ####
        cnt = UTILS.getCount(self.inputFC)
        fieldList = tuple(fieldList)
        gaTable, gaInfo = WU.gaTable(self.inputFC, fieldNames = fieldList,
                                     spatRef = self.spatialRefString)

        #### Check Whether the Number of Features is Appropriate ####
        numObs = gaInfo[0]
        ERROR.checkNumberOfObs(numObs, minNumObs = minNumObs,
                               warnNumObs = warnNumObs,
                               silentWarnings = self.silentWarnings)

        #### Process any bad records encountered ####
        numBadIDs = cnt - numObs
        if numBadIDs:
            badIDs = WU.parseGAWarnings(gaTable.warnings)
            if not self.silentWarnings:
                ERROR.reportBadRecords(cnt, numBadIDs, badIDs,
                                       label = self.oidName)
        else:
            badIDs = []

        #### Initialization of Centroids  ####
        xyCoords = NUM.empty((numObs, 2), float)

        #### Z Coords ####
        if self.hasZ:
            zCoords = NUM.empty((numObs, ), float)

        #### Create Empty Data Arrays ####
        for fieldName, fieldObj in self.fields.iteritems():
            fieldObj.createDataArray(numObs)

        #### Populate SSDataObject ####
        ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84001), 0, numObs, 1)
        for row in xrange(numObs):
            rowInfo = gaTable[row]
            x,y = rowInfo[1]
            masterID = int(rowInfo[self.masterColumnIndex])
            if self.master2Order.has_key(masterID):
                ARCPY.AddIDMessage("ERROR", 644, masterField)
                ARCPY.AddIDMessage("ERROR", 643)
                raise SystemExit()
            else:
                self.master2Order[masterID] = row
                self.order2Master[row] = masterID
                xyCoords[row] = (x, y)
            if numFields:
                restFields = rowInfo[self.dataColumnIndex:]
                for fieldInd, fieldName in enumerate(fields):
                    self.fields[fieldName].data[row] = restFields[fieldInd]
            if self.hasZ:
                if getZBool:
                    zCoords[row] = rowInfo[-1]
                else:
                    zCoords[row] = NUM.nan

            ARCPY.SetProgressorPosition()

        #### Set the Hidden Fields (E.g. Not in Use) ####
        self.setHiddenFields()

        #### Reset Extent to Honor Env and Subsets ####
        try:
            self.extent = UTILS.resetExtent(xyCoords)
        except:
            pass

        #### Reset Coordinates for Chordal ####
        if self.useChordal:
            #### Project to XY on Spheroid ####
            self.spheroidCoords = ARC._ss.lonlat_to_xy(xyCoords,
                                                self.spatialRef) 
            self.sliceInfo = UTILS.SpheroidSlice(self.extent,
                                                self.spatialRef)
        else:
            self.spheroidCoords = None
            self.sliceInfo = None

        #### Set Further Attributes ####
        self.badRecords = badIDs
        self.xyCoords = xyCoords
        self.masterField = masterField
        self.gaTable = gaTable
        self.numObs = numObs
        if self.hasZ:
            self.zCoords = zCoords
        else:
            self.zCoords = None

    def obtainData(self, masterField, fields = [], types = [0,1,2,3,4,5,6],
                   minNumObs = 0, warnNumObs = 0, dateStr = False,
                   explicitBadRecordID = None):
        """Takes a list of field names and returns it in a dictionary
        structure.

        INPUTS:
        masterField (str): name of field being used as the master
        fields {list, []}: name(s) of the field to be returned
        types (list): types of data allowed to be returned (1)
        minNumObs {int, 0}: minimum number of observations for error
        warnNumObs {int, 0}: minimum number of observations for warning
        OID {bool, False}: OID field allowed to be master field?

        ATTRIBUTES:
        gaTable (structure): instance of the GA Table
        fields (dict): fieldName = instance of FCField
        master2Order (dict): masterID = order in lists
        order2Master (dict): order in lists = masterID
        masterField (str): field that serves as the master
        badRecords (list): master IDs that could not be read
        xyCoords (array, nunObs x 2): xy-coordinates for feature centroids
        """

        #### Get Base Count, May Include Bad Records ####
        cnt = UTILS.getCount(self.inputFC)

        #### Validation of Master Field ####
        verifyMaster = ERROR.checkField(self.allFields, masterField,
                                        types = [0,1,5])

        #### Set MasterIsOID Boolean ####
        self.masterIsOID = masterField == self.oidName

        #### Set Master and Data Indices ####
        if self.masterIsOID:
            self.masterColumnIndex = 0
            self.dataColumnIndex = 2
            fieldList = [self.oidName, "shape@XY"]
        else:
            self.masterColumnIndex = 2
            self.dataColumnIndex = 3
            fieldList = [self.oidName, "shape@XY", masterField]

        #### Initialization of Centroids  ####
        xyCoords = NUM.empty((cnt, 2), float)

        #### Validation and Initialization of Data Fields ####
        numFields = len(fields)
        fieldTypes = {}
        hasDate = False
        for field in fields:
            fieldType = ERROR.checkField(self.allFields, field, types = types)
            fieldTypes[field] = fieldType
            fieldList.append(field)
            self.fields[field] = self.allFields[field]
            if fieldType.upper() == "DATE":
                hasDate = True
                nowTime = DT.datetime.now()

        #### Create Empty Data Arrays ####
        for fieldName, fieldObj in self.fields.iteritems():
            fieldObj.createDataArray(cnt, dateStr = dateStr)

        #### Z Coords ####
        if self.hasZ:
            zCoords = NUM.empty((cnt, ), float)
            fieldList.append("shape@Z")

        #### Keep track of Invalid Fields ####
        badIDs = []
        badRecord = 0

        #### Create Progressor Bar ####
        ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84001), 0, cnt, 1)

        #### Process Field Values ####
        try:
            rows = DA.SearchCursor(self.inputFC, fieldList, "",
                                   self.spatialRefString)
        except:
            ARCPY.AddIDMessage("ERROR", 204)
            raise SystemExit()

        c = 0
        for row in rows:
            oid = row[0]
            badXY = row[1].count(None)
            if self.hasZ:
                badValues = row[0:-1].count(None)
            else:
                badValues = row.count(None)

            #### Check Bad Record ####
            if badXY or badValues:
                badRow = 1
                badRecord = 1
                badIDs.append(oid)
            else:
                #### Get Centroid and Master ID ####
                xyCoords[c] = row[1]
                masterID = row[self.masterColumnIndex]

                #### Add Field Values ####
                if numFields:
                    restFields = row[self.dataColumnIndex:]
                    for fieldInd, fieldName in enumerate(fields):
                        fieldValue = restFields[fieldInd]
                        fieldType = fieldTypes[fieldName]
                        if fieldType.upper() == "DATE":
                            if dateStr:
                                fieldValue = str(fieldValue)
                            else:
                                fieldValue = (nowTime - fieldValue).total_seconds()
                        self.fields[fieldName].data[c] = fieldValue
                if self.hasZ:
                    zCoords[c] = row[-1]

                #### Check uniqueness of masterID field ####
                if self.master2Order.has_key(masterID):
                    del rows
                    ARCPY.AddIDMessage("ERROR", 644, masterField)
                    ARCPY.AddIDMessage("ERROR", 643)
                    raise SystemExit()
                else:
                    self.master2Order[masterID] = c
                    self.order2Master[c] = masterID
                    c += 1

            ARCPY.SetProgressorPosition()

        del rows

        #### Check Whether the Number of Features is Appropriate ####
        numObs = len(self.master2Order)
        ERROR.checkNumberOfObs(numObs, minNumObs = minNumObs,
                               warnNumObs = warnNumObs,
                               silentWarnings = self.silentWarnings)

        #### Get Set of Bad IDs ####
        badIDs = list(set(badIDs))
        badIDs.sort()
        badIDs = [ str(i) for i in badIDs ]

        #### Process any bad records encountered ####
        if badRecord != 0:
            bn = len(badIDs)
            if not self.silentWarnings:
                ERROR.reportBadRecords(cnt, bn, badIDs, label = self.oidName,
                                       explicitBadRecordID = explicitBadRecordID)

            #### Prune Data Arrays ####
            xyCoords = xyCoords[0:numObs]
            self.resizeDataArrays(numObs)
            if self.hasZ:
                zCoords = zCoords[0:numObs]

        #### Set the Hidden Fields (E.g. Not in Use) ####
        self.setHiddenFields()

        #### Reset Extent to Honor Env and Subsets ####
        try:
            self.extent = UTILS.resetExtent(xyCoords)
        except:
            pass

        #### Reset Coordinates for Chordal ####
        if self.useChordal:
            #### Project to XY on Spheroid ####
            self.spheroidCoords = ARC._ss.lonlat_to_xy(xyCoords, 
                                                self.spatialRef) 
            self.sliceInfo = UTILS.SpheroidSlice(self.extent,
                                                self.spatialRef)
        else:
            self.spheroidCoords = None
            self.sliceInfo = None

        #### Set Further Attributes ####
        self.badRecords = badIDs
        self.xyCoords = xyCoords
        self.masterField = masterField
        self.gaTable = None
        self.numObs = numObs
        if self.hasZ:
            self.zCoords = zCoords
        else:
            self.zCoords = None

    def addFields2FC(self, candidateFields, fieldOrder = []):

        #### Create/Verify Result Field Order ####
        fieldKeys = candidateFields.keys()
        fieldKeys.sort()
        if len(fieldOrder) == len(fieldKeys):
            fKeySet = set(fieldKeys)
            fieldOrderSet = set(fieldOrder)
            if fieldOrderSet == fKeySet:
                fieldKeys = fieldOrder

            del fKeySet, fieldOrderSet

        #### Add Empty Output Analysis Fields ####
        outputFieldNames = [self.masterField]
        for fieldInd, fieldName in enumerate(fieldKeys):
            field = candidateFields[fieldName]
            field.copy2FC(self.inputFC)
            outputFieldNames.append(fieldName)

            #### Replace NaNs for Shapefiles ####
            if self.shapeFileBool:
                if field.type != "TEXT":
                    isNaN = NUM.isnan(field.data)
                    if NUM.any(isNaN):
                        field.data[isNaN] = UTILS.shpFileNull[field.type]

        #### Populate Output Feature Class with Values ####
        ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84003),
                            0, self.numObs, 1)
        outRows = DA.UpdateCursor(self.inputFC, outputFieldNames)

        for row in outRows:
            masterID = row[0]
            if self.master2Order.has_key(masterID):
                order = self.master2Order[masterID]

                #### Create Output Row from Input ####
                resultValues = [masterID]

                #### Add Result Values ####
                for fieldName in fieldKeys:
                    field = candidateFields[fieldName]
                    fieldValue = field.data.item(order)
                    resultValues.append(fieldValue)

                #### Insert Values into Output ####
                outRows.updateRow(resultValues)

            else:
                #### Bad Record, Input: Do Not Delete Record ####
                pass

            ARCPY.SetProgressorPosition()

        #### Clean Up ####
        del outRows

    def output2NewFC(self, outputFC, candidateFields, appendFields = [],
                     fieldOrder = []):
        """Creates a new feature class with the same shape charcteristics as
        the source input feature class and appends data to it.

        INPUTS:
        outputFC (str): catalogue path to output feature class
        candidateFields (dict): fieldName = instance of CandidateField
        appendFields {list, []}: field names in the order you want appended
        fieldOrder {list, []}: the order with which to write fields
        """

        #### Initial Progressor Bar ####
        ARCPY.overwriteOutput = True
        ARCPY.SetProgressor("default", ARCPY.GetIDMessage(84006))

        #### Validate Output Workspace ####
        ERROR.checkOutputPath(outputFC)

        #### Create Path for Output FC ####
        outPath, outName = OS.path.split(outputFC)

        #### Get Output Name for SDE if Necessary ####
        baseType = UTILS.getBaseWorkspaceType(outPath)
        if baseType.upper() == 'REMOTEDATABASE':
            outName = outName.split(".")[-1]
        self.outputFC = OS.path.join(outPath, outName)

        #### Assess Whether to Honor Original Field Nullable Flag ####
        setNullable = UTILS.setToNullable(self.catPath, self.outputFC)

        #### Add Null Value Flag ####
        outIsShapeFile = UTILS.isShapeFile(self.outputFC)

        #### Create Output Field Names to be Appended From Input ####
        inputFieldNames = ["SHAPE@", self.masterField]
        appendFieldNames = []
        masterIsOID = self.masterField == self.oidName
        if masterIsOID:
            appendFieldNames.append("SOURCE_ID")
        else:
            master = self.allFields[self.masterField.upper()]
            returnName = UTILS.returnOutputFieldName(master)
            appendFieldNames.append(returnName)

        for fieldName in appendFields:
            field = self.allFields[fieldName.upper()]
            returnName = UTILS.returnOutputFieldName(field)
            inputFieldNames.append(fieldName)
            appendFieldNames.append(returnName)
        appendFieldNames = UTILS.createAppendFieldNames(appendFieldNames,
                                                        outPath)
        masterOutName = appendFieldNames[0]

        #### Create Field Mappings for Visible Fields ####
        outputFieldMaps = ARCPY.FieldMappings()

        #### Add Input Fields to Output ####
        for ind, fieldName in enumerate(appendFieldNames):
            if ind == 0:
                #### Master Field ####
                sourceFieldName = self.masterField
                if masterIsOID:
                    fieldType = "LONG"
                    alias = fieldName
                    setOutNullable = False
                    fieldLength = None
                    fieldPrecision = None
                else:
                    masterOutField = self.allFields[self.masterField.upper()]
                    fieldType = masterOutField.type
                    alias = masterOutField.baseName
                    setOutNullable = setNullable
                    fieldLength = masterOutField.length
                    fieldPrecision = masterOutField.precision
            else:
                #### Append Fields ####
                sourceFieldName = appendFields[ind-1]
                outField = self.allFields[sourceFieldName]
                fieldType = outField.type
                alias = outField.baseName
                setOutNullable = setNullable
                fieldLength = outField.length
                fieldPrecision = outField.precision

            #### Create Candidate Field ####
            outCandidate = CandidateField(fieldName, fieldType, None,
                                          alias = alias,
                                          precision = fieldPrecision,
                                          length = fieldLength)

            #### Create Output Field Map ####
            outFieldMap = UTILS.createOutputFieldMap(self.inputFC,
                                                  sourceFieldName,
                                 outFieldCandidate = outCandidate,
                                     setNullable = setOutNullable)

            #### Add Output Field Map to New Field Mapping ####
            outputFieldMaps.addFieldMap(outFieldMap)

        #### Do FC2FC Without Extent Env Var ####
        FC2FC = UTILS.clearExtent(CONV.FeatureClassToFeatureClass)
        try:
            FC2FC(self.inputFC, outPath, outName, "", outputFieldMaps)
        except:
            ARCPY.AddIDMessage("ERROR", 210, self.outputFC)
            raise SystemExit()

        #### Create/Verify Result Field Order ####
        fieldKeys = candidateFields.keys()
        fieldKeys.sort()
        if len(fieldOrder) == len(fieldKeys):
            fKeySet = set(fieldKeys)
            fieldOrderSet = set(fieldOrder)
            if fieldOrderSet == fKeySet:
                fieldKeys = fieldOrder

            del fKeySet, fieldOrderSet

        #### Add Empty Output Analysis Fields ####
        outputFieldNames = [masterOutName]
        for fieldInd, fieldName in enumerate(fieldKeys):
            field = candidateFields[fieldName]
            field.copy2FC(outputFC)
            outputFieldNames.append(fieldName)

            #### Replace NaNs for Shapefiles ####
            if outIsShapeFile:
                if field.type != "TEXT":
                    isNaN = NUM.isnan(field.data)
                    if NUM.any(isNaN):
                        field.data[isNaN] = UTILS.shpFileNull[field.type]

        #### Populate Output Feature Class with Values ####
        ARCPY.SetProgressor("step", ARCPY.GetIDMessage(84003),
                            0, self.numObs, 1)
        outRows = DA.UpdateCursor(self.outputFC, outputFieldNames)

        for row in outRows:
            masterID = row[0]
            if self.master2Order.has_key(masterID):
                order = self.master2Order[masterID]

                #### Create Output Row from Input ####
                resultValues = [masterID]

                #### Add Result Values ####
                for fieldName in fieldKeys:
                    field = candidateFields[fieldName]
                    fieldValue = field.data.item(order)
                    resultValues.append(fieldValue)

                #### Insert Values into Output ####
                outRows.updateRow(resultValues)

            else:
                #### Bad Record ####
                outRows.deleteRow()

            ARCPY.SetProgressorPosition()

        #### Clean Up ####
        del outRows
