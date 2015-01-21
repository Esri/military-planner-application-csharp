'''
Tool Name:  Generate Service Areas
Source Name: GenerateServiceAreas.py
Version: ArcGIS 10.1
Author: ESRI
This script generates service area polygons based on specified break values. It is intended to be used
in a geoprocessing service.
'''

#Import the modules
import os
import sys
import traceback
import time
import arcpy
import uuid
import locale
import NAUtils as nau

#set some constants
DEBUG = False
NA_LAYER = "GenerateServiceAreas_ServiceArea"
POLYGONS_SUBLAYER = NA_LAYER + os.sep + "Polygons"
EXTRA_BREAK_VALUE_FACTOR = 1.1
ROUND_PRECISION = 5
TIME_UNITS = ('minutes','hours','days', 'seconds')
INFINITY = sys.maxint
TOOL_NAME = "GenerateServiceAreas_na"

#Field names from input features sets. These need to be updated if we change schema for inputs
FACILITIES_FIELDS = (u'Name', )
POINT_BARRIER_FIELDS = (u'Name', u'BarrierType', u'AdditionalCost')
LINE_BARRIER_FIELDS = (u'Name',)
POLYGON_BARRIER_FIELDS = (u'Name', u'BarrierType', u'ScaledCostFactor')
ATTRIBUTE_PARAMETER_FIELDS = (u'AttributeName', u'ParameterName', u'ParameterValue')

#ParameterName to Parameter Index mapping. If the parameter index changes, make sure that this mapping
#is upto date.
parameterIndex = {'facilities': 0,
                  'breakValues':1,
                  'breakUnits':2,
                  'networkDataset':3,
                  'outputPolygons':4,
                  'travelDirection':5,
                  'arriveDepartTime':6,
                  'uturnPolicy':7,
                  'pointBarriers':8,
                  'lineBarriers':9,
                  'polygonBarriers':10,
                  'timeImpedance': 11,
                  'timeImpedanceUnits':12,
                  'distanceImpedance':13,
                  'distanceImpedanceUnits':14,                  
                  'useHierarchy': 15,                  
                  'restrictions':16,
                  'attributeParameters':17,
                  'searchTolerance': 18,
                  'excludeRestricted': 19,
                  'locatorWhereClause': 20,
                  'polygonMerge':21,
                  'polygonNestingType':22,
                  'detailedPolygons': 23,
                  'trimDistance' : 24,
                  'geometryPrecision':25,
                  'maxFacilities' : 26,
                  'maxBreaks': 27,
                  'maxPointBarrierCount':28,
                  'maxLineBarriers': 29,
                  'maxPolygonBarriers': 30,
                  'maxBreakTime': 31,
                  'maxBreakDistance': 32,
                  'forceHierarchyTime' : 33,
                  'forceHierarchyDistance' : 34,
                  'saveOutputLayer':35,
                  'timeZoneUsage' : 36,
                  'solveSucceeded':37
                  }

parameterInfo = arcpy.GetParameterInfo(TOOL_NAME)

#Get all the input and output parameter values
facilities = arcpy.GetParameter(parameterIndex['facilities'])
breakValues = arcpy.GetParameterAsText(parameterIndex['breakValues'])
breakUnits = arcpy.GetParameterAsText(parameterIndex['breakUnits'])
networkDataset = arcpy.GetParameterAsText(parameterIndex['networkDataset'])
outputPolygons = arcpy.GetParameterAsText(parameterIndex['outputPolygons'])
travelDirection = arcpy.GetParameterAsText(parameterIndex['travelDirection'])
polygonMerge = arcpy.GetParameterAsText(parameterIndex['polygonMerge'])
polygonNestingType = arcpy.GetParameterAsText(parameterIndex['polygonNestingType'])
detailedPolygons = arcpy.GetParameter(parameterIndex['detailedPolygons'])
polygonTrimDistance = arcpy.GetParameterAsText(parameterIndex['trimDistance'])
geometryPrecision = arcpy.GetParameterAsText(parameterIndex['geometryPrecision'])
uturnPolicy = arcpy.GetParameterAsText(parameterIndex['uturnPolicy'])
restrictions = arcpy.GetParameterAsText(parameterIndex['restrictions'])
useHierarchy = arcpy.GetParameter(parameterIndex['useHierarchy'])
attributeParameters = arcpy.GetParameter(parameterIndex['attributeParameters'])
pointBarriers = arcpy.GetParameter(parameterIndex['pointBarriers'])
lineBarriers = arcpy.GetParameter(parameterIndex['lineBarriers'])
polygonBarriers = arcpy.GetParameter(parameterIndex['polygonBarriers'])
arriveDepartTime = arcpy.GetParameterAsText(parameterIndex['arriveDepartTime'])
timeZoneUsage = arcpy.GetParameterAsText(parameterIndex['timeZoneUsage'])
timeImpedance = arcpy.GetParameterAsText(parameterIndex['timeImpedance'])
timeImpedanceUnits = arcpy.GetParameterAsText(parameterIndex['timeImpedanceUnits'])
distanceImpedance = arcpy.GetParameterAsText(parameterIndex['distanceImpedance'])
distanceImpedanceUnits = arcpy.GetParameterAsText(parameterIndex['distanceImpedanceUnits'])
searchTolerance = arcpy.GetParameterAsText(parameterIndex['searchTolerance'])
excludeRestricted = arcpy.GetParameterAsText(parameterIndex['excludeRestricted'])
locatorWhereClause = arcpy.GetParameterAsText(parameterIndex['locatorWhereClause'])
strMaxFacilities = arcpy.GetParameterAsText(parameterIndex['maxFacilities'])
strMaxBreaks = arcpy.GetParameterAsText(parameterIndex['maxBreaks'])
strMaxPointBarrierCount = arcpy.GetParameterAsText(parameterIndex['maxPointBarrierCount'])
strMaxEdgeCountLineBarriers = arcpy.GetParameterAsText(parameterIndex['maxLineBarriers'])
strMaxEdgeCountPolygonBarriers = arcpy.GetParameterAsText(parameterIndex['maxPolygonBarriers'])
strMaxBreakTime = arcpy.GetParameterAsText(parameterIndex['maxBreakTime'])
strMaxBreakDistance = arcpy.GetParameterAsText(parameterIndex['maxBreakDistance'])
strForceHierarchyTime = arcpy.GetParameterAsText(parameterIndex['forceHierarchyTime'])
strForceHierarchyDistance = arcpy.GetParameterAsText(parameterIndex['forceHierarchyDistance'])
saveOutputLayer = arcpy.GetParameter(parameterIndex['saveOutputLayer'])


try:
    #Check out network analyst extension license
    arcpy.CheckOutExtension("network")
    #Set GP environment settings
    #arcpy.env.overwriteOutput = True
    
    ##set module level variables
    solveSucceeded = False    
    useExtraBreak = False
    saLayerExists = False
    polygonType = "SIMPLE_POLYS"
    input_copies = []
    
    #Convert constraint values from strings to number. If empty string use max Int
    maxPointBarrierCount = locale.atoi(strMaxPointBarrierCount) if strMaxPointBarrierCount else INFINITY
    maxEdgeCountLineBarriers = locale.atoi(strMaxEdgeCountLineBarriers) if strMaxEdgeCountLineBarriers else INFINITY
    maxEdgeCountPolygonBarriers = locale.atoi(strMaxEdgeCountPolygonBarriers) if strMaxEdgeCountPolygonBarriers else INFINITY
    maxFacilities = locale.atoi(strMaxFacilities) if strMaxFacilities else INFINITY
    maxBreaks = locale.atoi(strMaxBreaks) if strMaxBreaks else INFINITY
    maxBreakTime = locale.atof(strMaxBreakTime) if strMaxBreakTime else INFINITY
    maxBreakDistance = locale.atof(strMaxBreakDistance) if strMaxBreakDistance else INFINITY
    forceHierarchyTime = locale.atof(strForceHierarchyTime) if strForceHierarchyTime else INFINITY
    forceHierarchyDistance = locale.atof(strForceHierarchyDistance) if strForceHierarchyDistance else INFINITY
    
    descNDS = arcpy.Describe(networkDataset)
    descNDSAttributes = descNDS.attributes
    
    #Convert all input features to feature sets or recordsets if they are not
    #This is required as if input is passed a feature layer or feature class
    #We will end up directly modifying the inputs
    
    facilities_obj = nau.InputFeatureClass(facilities)
    #Store the OBJECTID field for facilities as it will used later when exporting output facilities
    orig_input_facilities_oid_fld_name = facilities_obj.origOIDFieldName    
    #Store the describe object and all the fields names from input facilities to be used later when exporting output facilities
    orig_input_facilities_desc = facilities_obj.describeObject
    #orig_input_facilities_fld_aliases = {f.name:f.aliasName for f in orig_input_facilities_desc.fields}
    point_barriers_obj = nau.InputFeatureClass(pointBarriers)
    line_barriers_obj = nau.InputFeatureClass(lineBarriers)
    polygon_barriers_obj = nau.InputFeatureClass(polygonBarriers)
    attribute_parameters_obj = nau.InputTable(attributeParameters)
    #Keep a list of input copies so we can delete them just before exit
    input_copies = (facilities_obj, point_barriers_obj, line_barriers_obj,
                    polygon_barriers_obj, attribute_parameters_obj)
    
    #Get counts for facilities, incidents, barrier features and attribute parameters
    facility_count = facilities_obj.count
    
    #Convert inputs from record sets to feature classes if they are not empty.
    out_workspace = os.path.dirname(outputPolygons)
    desc_out_workspace = arcpy.Describe(out_workspace)
    #If the workspace is a folder, set scratchGDB as workspace
    if desc_out_workspace.dataType.lower() == "folder" and desc_out_workspace.workspaceType.lower() == "filesystem":
        out_workspace = arcpy.env.scratchGDB    
    if facility_count:
        facilities_obj.copyFeatures(out_workspace, FACILITIES_FIELDS)
        facilities = facilities_obj.catalogPath
    
    if point_barriers_obj.count:
        point_barriers_obj.copyFeatures(out_workspace, POINT_BARRIER_FIELDS)
        pointBarriers = point_barriers_obj.catalogPath
    
    if line_barriers_obj.count:
        line_barriers_obj.copyFeatures(out_workspace, LINE_BARRIER_FIELDS)
        lineBarriers = line_barriers_obj.catalogPath
    
    if polygon_barriers_obj.count:
        polygon_barriers_obj.copyFeatures(out_workspace, POLYGON_BARRIER_FIELDS)
        polygonBarriers = polygon_barriers_obj.catalogPath
    
    if attribute_parameters_obj.count:
        attribute_parameters_obj.copyFeatures(out_workspace, ATTRIBUTE_PARAMETER_FIELDS)
        attributeParameters = attribute_parameters_obj.catalogPath    
    
    #If the network dataset does not support hierarchy, set the useHierarchy parameter to false.
    ndsSupportsHierarchy = nau.nds_supports_hierarchy(descNDSAttributes)
    if not ndsSupportsHierarchy:
        useHierarchy = False
    isTrimDistanceZero = False
    if not polygonTrimDistance or polygonTrimDistance.split(" ")[0] == '0':
        isTrimDistanceZero = True
    #determine whether we should use time based or distance based impedance attribute based on break units
    #using python ternary operator here.
    impedanceAttribute = timeImpedance if breakUnits.lower() in TIME_UNITS else distanceImpedance 
    #get the user supplied break values as list for easy processing    
    breakValueList = [val.encode("utf-8") for val in breakValues.strip().split()]
    breakValueCount = len(breakValueList)
    if breakValueCount == 0:
        arcpy.AddIDMessage("ERROR",30117)
        raise nau.InputError()
    #Find the largest break value.
    try:
        endBreakValue = max([locale.atof(val) for val in breakValueList])
    except ValueError:
        arcpy.AddIDMessage("ERROR",30118)
        raise nau.InputError()
    impedanceUnit = nau.verify_impedance_units(timeImpedance,timeImpedanceUnits,distanceImpedance,
                                               distanceImpedanceUnits,descNDSAttributes,False)[impedanceAttribute]
    #Convert break values from user specified units to impedance units.
    convertedBreakValueList = nau.convert_units(breakValueList,breakUnits,impedanceUnit)
    converetedEndBreakValue = max([locale.atof(val) for val in convertedBreakValueList])   

    zeroString = nau.float_to_string(0,ROUND_PRECISION)
    
    ##Determine if the throtling conditions are met. If not raise an exception and quit
    ##If throtling parameters have zero value, then do not perform throtlling checks.
    # Thortling Check 1: Check for number of facilities
    if facilities_obj.count == 0:
        arcpy.AddIDMessage("ERROR",30117)
        raise nau.InputError()
    if strMaxFacilities and facilities_obj.count > maxFacilities:
        arcpy.AddIDMessage("ERROR", 30096,"Facilities", maxFacilities)
        raise nau.InputError()
    
    #Thortling Check 2: Check for number of breaks
    if breakValueCount == 0:
        arcpy.AddIDMessage("ERROR",30117)
        raise nau.InputError()
    if strMaxBreaks and breakValueCount > maxBreaks:
        arcpy.AddIDMessage("ERROR",30121, breakValueCount,maxBreaks)
        raise nau.InputError()
    
    #Thortling Check 3: Check if the end break value is within maximum allowed and if hierarchy needs to be forced
    if impedanceAttribute == timeImpedance:
        if strMaxBreakTime and converetedEndBreakValue > maxBreakTime:
            convertedMaxBreakTime = nau.convert_units(maxBreakTime,impedanceUnit,breakUnits)
            convertedMaxBreakTimeWithUnits = "%s %s" % (convertedMaxBreakTime, breakUnits)
            arcpy.AddIDMessage("ERROR",30122, endBreakValue, convertedMaxBreakTimeWithUnits)
            raise nau.InputError()
            
        if strForceHierarchyTime and useHierarchy == False and converetedEndBreakValue > forceHierarchyTime:
            convertedForceHierarchyTime = nau.convert_units(forceHierarchyTime, impedanceUnit, breakUnits)            
            #force to use hierarchy. If the NDS does not support hierarchy raise and error and quit.
            if ndsSupportsHierarchy:
                useHierarchy = True
                arcpy.AddIDMessage("WARNING", 30109)
                convertedForceHierarchyTimeWithUnits = "%s %s" % (convertedForceHierarchyTime, breakUnits)
                arcpy.AddIDMessage("WARNING", 30120,endBreakValue, convertedForceHierarchyTimeWithUnits)
                
            else:
                arcpy.AddIDMessage("ERROR", 30119, parameterInfo[parameterIndex['forceHierarchyTime']].displayName)
                raise nau.InputError()
            
    else:
        if strMaxBreakDistance and converetedEndBreakValue > maxBreakDistance:
            convertedMaxBreakDistance = nau.convert_units(maxBreakDistance,impedanceUnit,
                                                      breakUnits)
            convertedMaxBreakDistanceWithUnits = "%s %s" % (convertedMaxBreakDistance, breakUnits)
            arcpy.AddIDMessage("ERROR",30123, endBreakValue, convertedMaxBreakDistanceWithUnits)
            raise nau.InputError()
        if strForceHierarchyDistance and useHierarchy == False and converetedEndBreakValue > forceHierarchyDistance:
            convertedForceHierarchyDistance = nau.convert_units(forceHierarchyDistance, impedanceUnit, breakUnits)            
            #force to use hierarchy. If the NDS does not support hierarchy raise and error and quit.
            if ndsSupportsHierarchy:
                useHierarchy = True
                arcpy.AddIDMessage("WARNING", 30109)
                convertedForceHierarchyDistanceWithUnits = "%s %s" % (convertedForceHierarchyDistance, breakUnits)
                arcpy.AddIDMessage("WARNING", 30120,endBreakValue, convertedForceHierarchyDistanceWithUnits)
        
            else:
                arcpy.AddIDMessage("ERROR", 30119, parameterInfo[parameterIndex['forceHierarchyDistance']].displayName)
                raise nau.InputError()

    #Check if generating detailed polygons when using hierarchy
    if useHierarchy and detailedPolygons:
        arcpy.AddIDMessage("ERROR", 30097, parameterInfo[parameterIndex['detailedPolygons']].displayName)
        raise nau.InputError()
    
    #Thortling Check 4: Check if the number of barrier features (point, line and polygon)
    #are within maximum allowed
    loadPointBarriers, loadLineBarriers, loadPolygonBarriers = nau.check_barriers(point_barriers_obj, line_barriers_obj, polygon_barriers_obj,
                                                                                  maxPointBarrierCount, maxEdgeCountLineBarriers, maxEdgeCountPolygonBarriers, 
                                                                                  descNDS)    
    
    ##Perform the Service Area analysis as all throtlling conditions are met.
    #We don't want to use extra break when using hierarchy as the solver does this for us.
    #trimming is not supported when using hierarchy
    #detailed Polygons are not supported when using hierarchy
    if useHierarchy:
        useExtraBreak = False
        trimPolygons = "NO_TRIM_POLYS"
        polygonType = "SIMPLE_POLYS"
        #Add warning messages that trim distance and detailed polygons will not be generated
        if isTrimDistanceZero == False:
            arcpy.AddIDMessage("WARNING", 30097, parameterInfo[parameterIndex['trimDistance']].displayName)
    else:    
        #If a trim distance is specified, we use trimming instead of extra break
        if isTrimDistanceZero == False:
            useExtraBreak = False
            trimPolygons = "TRIM_POLYS"
        else:
            useExtraBreak = True
            trimPolygons = "NO_TRIM_POLYS"
        #generate detailed polygons when requested for non-hierarchical case.
        if detailedPolygons:
            polygonType = "DETAILED_POLYS"
        else:
            polygonType = "SIMPLE_POLYS"
        
    #Add an extra break so that we get better polygons without trimming
    if useExtraBreak:
        extraBreakValue = locale.str(round(converetedEndBreakValue * EXTRA_BREAK_VALUE_FACTOR,
                                           ROUND_PRECISION))
        convertedBreakValueList.append(extraBreakValue)

    #Use only those restrictions that are supported by the network dataset. If the user supplied
    #restriction list contain un-supported restrictions, add a warning message.

    #Get the restrictions and accumulate attributes that are valid for the network dataset
    if restrictions:
        restrictions_to_use = nau.get_valid_attributes(descNDSAttributes, restrictions)
    else:
        restrictions_to_use = []
    
    #Make a new service area layer
    saLayer = arcpy.na.MakeServiceAreaLayer(networkDataset, NA_LAYER, impedanceAttribute, travelDirection,
                                  " ".join(convertedBreakValueList),polygonType, polygonMerge,
                                  polygonNestingType,"NO_LINES","OVERLAP","NO_SPLIT", "", "", uturnPolicy,
                                  restrictions_to_use, trimPolygons, polygonTrimDistance,
                                  "NO_LINES_SOURCE_FIELDS", useHierarchy, arriveDepartTime).getOutput(0)
    
    saLayerExists = True
    saLayerSolverProps = arcpy.na.GetSolverProperties(saLayer)
    #Set the timeZoneUsage if timeOfDay is specified
    if arriveDepartTime:
        saLayerSolverProps.timeZoneUsage = timeZoneUsage
    
    #Add FacilityOID field that will contain the ObjectdID from input points
    #arcpy.na.AddFieldToAnalysisLayer(saLayer, naClassNames["Facilities"], saFacilitiesOIDFieldName, "LONG",
                                     #field_alias=saFacilitiesOIDFieldName)
    
    
    #Add attribute parameters if specified
    nau.update_attribute_parameters(saLayer, attributeParameters, restrictions_to_use + [impedanceAttribute], descNDSAttributes)    

    #Add Barriers before loading facilities as we want to exclude restricted portions
    if loadPointBarriers:
        nau.add_locations(saLayer, "Barriers", point_barriers_obj, impedanceAttribute, impedanceUnit,
                          breakUnits, searchTolerance, locatorWhereClause)        
    if loadLineBarriers:
        nau.add_locations(saLayer, "PolylineBarriers", line_barriers_obj, impedanceAttribute, impedanceUnit,
                          breakUnits, searchTolerance, locatorWhereClause)        
    
    if loadPolygonBarriers:
        nau.add_locations(saLayer, "PolygonBarriers", polygon_barriers_obj, impedanceAttribute, impedanceUnit,
                          breakUnits, searchTolerance, locatorWhereClause)        
    
    #Add facilities
    nau.add_locations(saLayer, "Facilities", facilities_obj, impedanceAttribute, impedanceUnit,
                      breakUnits, searchTolerance, locatorWhereClause, None,
                      exclude_restricted_elements=excludeRestricted)    
    #Solve
    solveResult = arcpy.na.Solve(saLayer,"SKIP","TERMINATE", geometryPrecision)
    
    #Get all the layer objects corresponding to the sa layer
    allLayers  = {layer.datasetName: layer for layer in arcpy.mapping.ListLayers(saLayer)[1:]}
    #polygonsSublayer = arcpy.mapping.ListLayers(saLayer,naClassNames["SAPolygons"])[0]
    polygonsSublayer = allLayers["SAPolygons"]
    facilitiesSublayer = allLayers["Facilities"]
    
    if solveResult.getOutput(1).lower() == 'true':
        solveSucceeded = True
    else:
        solveSucceeded = False
    if solveResult.maxSeverity == 1:
        nau.print_message(solveResult.getMessages(1), 1)
    
    #Transfer the FacilityOID field from facilities to polygons if we are not merging polygons
    #otherwise calculate the field as <Null>
    saFacilitiesOIDFieldName = "FacilityOID"
    naClassNames = arcpy.na.GetNAClassNames(saLayer)
    arcpy.na.AddFieldToAnalysisLayer(saLayer, naClassNames["SAPolygons"], saFacilitiesOIDFieldName, "LONG",
                                         field_alias=saFacilitiesOIDFieldName)    
    if polygonMerge != "MERGE":
        #Use Add Join instead of JoinField as AddJoin has better performance.
        arcpy.management.AddJoin(polygonsSublayer, "FacilityID", facilitiesSublayer, "ObjectID")
        arcpy.management.CalculateField(polygonsSublayer, "SAPolygons.{0}".format(saFacilitiesOIDFieldName),
                                        "!Facilities.{0}!".format(saFacilitiesOIDFieldName), "PYTHON_9.3")
        arcpy.management.RemoveJoin(polygonsSublayer, "Facilities")        
                
    #Save the output layer. The layer name is based on random guid    
    if saveOutputLayer:
        scratchFolder = arcpy.env.scratchFolder
        uid = str(uuid.uuid4()).replace("-","")
        naLayerFileName = "_ags_gpna{0}.lyr".format(uid)
        outputLayerFile = os.path.join(scratchFolder, naLayerFileName)
        arcpy.management.SaveToLayerFile(saLayer,outputLayerFile)
        arcpy.AddIDMessage("INFORMATIVE", 30124, naLayerFileName) 
    #If we are using an extra break exclude the polygons corresponding to that break before copying them
    if useExtraBreak:
        #We are not converting the float to str using locale specific locale.str as
        #SQL statements need number with period as decimal points irrespective of locales.
        whereClause = '"ToBreak" <= ' + str(converetedEndBreakValue)
        arcpy.management.SelectLayerByAttribute(polygonsSublayer, "NEW_SELECTION", whereClause)
    #Convert break values from impedance units to break units in the polygons sublayer.
    #We need to update the Name, FromBreak and ToBreak Fields
    if breakUnits.lower() != impedanceUnit.lower():
        nameField = "Name"        
        fromBreakField = "FromBreak"
        toBreakField = "ToBreak"
        with arcpy.da.UpdateCursor(polygonsSublayer, (nameField, fromBreakField, toBreakField)) as cursor:
            for row in cursor:
                nameFirstPart = row[0].split(":")[0].strip()
                fromBreak = nau.float_to_string(row[1], ROUND_PRECISION)
                newFromBreak = "0"
                toBreak = nau.float_to_string(row[2], ROUND_PRECISION)
                newToBreak = ""
                #update FromBreak value if it not zero.
                if fromBreak != zeroString:        
                    if fromBreak in convertedBreakValueList:
                        #Get the user break value which must be at the same index as the impedance break value. 
                        newFromBreak = breakValueList[convertedBreakValueList.index(fromBreak)]
                    else:
                        #This might happen if the solver could not reach the break value and the output polygons
                        #are different than the input break values. So just do a conversion
                        newFromBreak = nau.convert_units(fromBreak, impedanceUnit, breakUnits) 
                    row[1] = newFromBreak
                #Update ToBreak value
                if toBreak in convertedBreakValueList:
                    newToBreak = breakValueList[convertedBreakValueList.index(toBreak)]
                else:
                    newToBreak = nau.convert_units(toBreak, impedanceUnit, breakUnits)
                row[2] = newToBreak
                #update Name value
                if polygonMerge == "MERGE":
                    newName = "%s - %s" % (newFromBreak, newToBreak)
                else:
                    newName = "%s : %s - %s" % (nameFirstPart, newFromBreak, newToBreak)
                row[0] = newName
                cursor.updateRow(row)
                
    #Copy the polygons to the output feature class. Transfer all the attributes from input facilities to polygons if
    #not creating merge polygons.
    
    if polygonMerge != "MERGE":
        
        #We need to transfer all fields from input facilities. So do not specify fields parameter when calling JoinField tool
        arcpy.management.JoinField(polygonsSublayer, saFacilitiesOIDFieldName, facilities_obj.inputFeatures, 
                                   orig_input_facilities_oid_fld_name)        
        ##Use this portion if we really need control over the field names from input facilities in case of name collisions. 
        #Get the field names on SAPolygons before making the next join
        #polygonsSublayerFieldNames = [f.name for f in arcpy.Describe(polygonsSublayer).fields]        
        ##Make a join based on FacilityOID from polygons and OID from orig_input_facilities
        #arcpy.management.AddJoin(polygonsSublayer, saFacilitiesOIDFieldName, facilities_obj.inputFeatures, orig_input_facilities_oid_fld_name)
        ##
        ##Get a list of all field names after the join
        #polygonsSublayer_join_desc = arcpy.Describe(polygonsSublayer)
        ##Do not transfer OID fields from both tables as well as shape field from SAPolygons
        #ignore_field_names = (polygonsSublayer_join_desc.oidFieldName,
                              #polygonsSublayer_join_desc.shapeFieldName,
                              #"{0}.{1}".format(orig_input_facilities_desc.name,orig_input_facilities_oid_fld_name))
        #polygonsSublayerJoinFieldNames = [f.name for f in polygonsSublayer_join_desc.fields if not f.name in ignore_field_names]
        #field_mappings = arcpy.FieldMappings()
        #for join_fld_name in polygonsSublayerJoinFieldNames:
            #field_map = arcpy.FieldMap()
            #tbl_name, fld_name = join_fld_name.split(".")
            #nau.print_message("Adding {0} field to output".format(fld_name),0)
            #field_map.addInputField(polygonsSublayer,join_fld_name)
            #out_fld = field_map.outputField
            #if tbl_name == "SAPolygons":
                #out_fld.name = fld_name
                #out_fld.aliasName = fld_name
            #else:
                ##Check if the field name is same as one of SAPolygons fields. if Yes add _ORIG to the end
                #if fld_name in polygonsSublayerFieldNames:
                    #fld_name = fld_name + "_ORIG"
                #out_fld.name = fld_name
                ##Get the alias name from original input facilities
                #out_fld.aliasName = orig_input_facilities_fld_aliases.get(fld_name, fld_name)
            #field_map.outputField = out_fld
            #field_mappings.addFieldMap(field_map)
        #arcpy.conversion.FeatureClassToFeatureClass(polygonsSublayer, os.path.dirname(outputPolygons),
                                                    #os.path.basename(outputPolygons),"",field_mappings)
        #arcpy.management.RemoveJoin(polygonsSublayer)
    #else:
        #arcpy.management.CopyFeatures(polygonsSublayer, outputPolygons)  
    arcpy.management.CopyFeatures(polygonsSublayer, outputPolygons)
    
except nau.InputError as ex:
    #Handle errors due to throtling conditions
    solveSucceeded = False
    if ex.message:
        nau.print_message(ex.message)
except arcpy.ExecuteError:
    #Handle GP exceptions
    solveSucceeded = False    
    if DEBUG:
        #Get the line number at which the GP error occured
        tb = sys.exc_info()[2]
        nau.print_message("A geoprocessing error occurred in File %s, line %s" % (__file__, tb.tb_lineno))
    else:
        nau.print_message("A geoprocessing error occurred.")
    warningMessages = arcpy.GetMessages(1) 
    if warningMessages:    
        nau.print_message(warningMessages, 1)
    nau.print_message(arcpy.GetMessages(2))
except:
    #Handle python errors
    solveSucceeded = False
    if DEBUG:
        #Get a nicely formatted traceback object except the first line.
        msgs = traceback.format_exception(*sys.exc_info())[1:]
        msgs[0] = "A python error occurred in " + msgs[0].lstrip()
        for msg in msgs:
            nau.print_message(msg.strip())
    else:
        nau.print_message("A python error occurred.")
finally:
    #Delete the in-memory na layer
    if saLayerExists:
        try:
            arcpy.management.Delete(saLayer)
        except:
            pass
    #Delete copies of inputs
    for obj in input_copies:
        if obj:
            obj.deleteCopy()    
    arcpy.SetParameter(parameterIndex['solveSucceeded'], solveSucceeded)



                  
                  
