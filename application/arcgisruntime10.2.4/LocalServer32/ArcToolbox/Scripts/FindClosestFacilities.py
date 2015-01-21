'''
Tool Name: Find Closest Facilities
Source Name: FindClosestFacilities.py
Version: ArcGIS 10.2.1
Author: ESRI
This script finds closest facilities from one or more incidents based on a specified network cost.
It is intended to be used in a geoprocessing service.
'''

#Import the modules
import arcpy
import os
import sys
import traceback
import time
import fnmatch
#from xml.etree import ElementTree as ET
import uuid
import NAUtils as nau

#set some constants
DEBUG = False
NA_LAYER = "FindClosestFacilities_ClosestFacility"
#POLYGONS_SUBLAYER = NA_LAYER + os.sep + "Polygons"
ROUND_PRECISION = 5
TIME_UNITS = ('minutes','hours','days', 'seconds')
INFINITY = sys.maxint
ID_FIELD_NAME = "ID"
#Field names from input features sets. These need to be updated if we change schema for inputs
FACILITIES_FIELDS = (u'Name', u'ID', u'AdditionalTime', u'AdditionalDistance', u'CurbApproach')
INCIDENTS_FIELDS = FACILITIES_FIELDS
POINT_BARRIER_FIELDS = (u'Name', u'BarrierType', u'Additional_Time', u'Additional_Distance')
LINE_BARRIER_FIELDS = (u'Name')
POLYGON_BARRIER_FIELDS = (u'Name', u'BarrierType', u'ScaledTimeFactor', u'ScaledDistanceFactor')
ATTRIBUTE_PARAMETER_FIELDS = (u'AttributeName', u'ParameterName', u'ParameterValue')
TOOL_NAME = "FindClosestFacilities_na"


#functions
def max_distance_between_points(point_feature_sets):
    '''Return the maximum straight line distance in meters between the point features. point_feature_sets is
    the two value list of feature sets containing input points. All feature classes are assumed to be in same spatial
    reference. The spatial reference of first feature class is used for calculations. The maximum distance is
    calculated as the maximum of the width or height for the combined extent of all the point feature classes.
    In case of an exception, return sys.maxint as we want to use hierarchy if we cannot figure out how to enforce hierarchy. '''
    max_distance = INFINITY
    try:
        #convert the feature sets into feature classes so that we get all the properties like extent and spatial ref
        point_feature_classes = []
        point_array = arcpy.Array()
        for i,fs in enumerate(point_feature_sets):
            point_fc = "in_memory{0}pfc{1}".format(os.sep,i)
            fs.save(point_fc)
            point_feature_classes.append(point_fc)

        #Convert each feature class extents to polygons
        extent_polygons = []
        extent_lower_left_points = []
        for fc in point_feature_classes:
            desc_fc = arcpy.Describe(fc)
            fc_extent = desc_fc.extent
            extent_lower_left_points.append(fc_extent.lowerLeft)
            point_array.add(fc_extent.lowerLeft)
            point_array.add(fc_extent.lowerRight)
            point_array.add(fc_extent.upperRight)
            point_array.add(fc_extent.upperLeft)
            point_array.add(fc_extent.lowerLeft)
            extent_polygons.append(arcpy.Polygon(point_array, desc_fc.spatialReference))
            point_array.removeAll()
        #union the two polygons to get the merged extent
        combined_extent_polygon = extent_polygons[0].union(extent_polygons[1])

        #Get the width and height of combined extent
        #Get the diagonal line from the combined extent
        combined_extent = combined_extent_polygon.extent
        #For feature classes with single point, the combined extent after union comes out to be null
        #In such cases just construct a line using the lower left extent point for feature classes.
        point_array.removeAll()
        if combined_extent.width > 0:
            #point_array.add(combined_extent.lowerLeft)
            #point_array.add(combined_extent.upperRight)
            #combined_extent_diagonal = arcpy.Polyline(point_array,combined_extent.spatialReference)
            point_array.add(combined_extent.lowerLeft)
            point_array.add(combined_extent.lowerRight)
            combined_extent_width = arcpy.Polyline(point_array,combined_extent.spatialReference).getLength("GEODESIC")
            point_array.removeAll()
            point_array.add(combined_extent.lowerLeft)
            point_array.add(combined_extent.upperLeft)
            combined_extent_height = arcpy.Polyline(point_array,combined_extent.spatialReference).getLength("GEODESIC")
            point_array.removeAll()
            max_distance =  max((combined_extent_height, combined_extent_width))
        else:
            point_array.add(extent_lower_left_points[0])
            point_array.add(extent_lower_left_points[1])
            max_distance = arcpy.Polyline(point_array,combined_extent.spatialReference).getLength("GEODESIC")
            point_array.removeAll()
    except Exception as ex:
        max_distance = INFINITY

    return max_distance


#ParameterName to Parameter Index mapping. If the parameter index changes, make sure that this mapping
#is upto date.

parameter_names = ('incidents', 'facilities', 'measurement_units','network_dataset', 
                   'out_gdb_workspace','out_routes_name', 'out_directions_name',
                   'out_facilities_name', 'num_facilities_to_find', 'default_cutoff', 'travel_direction',
                   'time_of_day', 'time_of_day_usage', 'time_zone_usage','uturn_policy',
                   'point_barriers', 'line_barriers', 'polygon_barriers', 'time_attribute',
                   'time_attribute_units', 'distance_attribute', 'distance_attribute_units',
                   'use_hierarchy', 'restrictions', 'attribute_parameters', 'accumulate_attributes',
                   'max_snap_tolerance', 'feature_locator_where_clause', 'route_shape',
                   'route_line_simplification_tolerance', 'populate_directions', 
                   'directions_language', 'directions_distance_units','directions_style_name',
                   'max_features_point_barriers', 'max_features_line_barriers',
                   'max_features_polygon_barriers', 'max_facilities', 'max_facilities_to_find',
                   'max_incidents', 'force_hierarchy_beyond_distance', 'save_output_layer', 
                   'solve_succeeded', 'out_routes', 'out_directions', 'out_facilities')

parameter_index = {value:index for index,value in enumerate(parameter_names)}
parameter_info = arcpy.GetParameterInfo(TOOL_NAME)

#Get all the input parameter values
facilities = arcpy.GetParameter(parameter_index['facilities'])
incidents = arcpy.GetParameter(parameter_index['incidents'])
network_dataset = arcpy.GetParameterAsText(parameter_index['network_dataset'])
measurement_units = arcpy.GetParameterAsText(parameter_index['measurement_units'])
out_gdb_workspace = arcpy.GetParameterAsText(parameter_index['out_gdb_workspace'])
out_routes_name = arcpy.GetParameterAsText(parameter_index['out_routes_name'])
out_directions_name = arcpy.GetParameterAsText(parameter_index['out_directions_name'])
out_facilities_name = arcpy.GetParameterAsText(parameter_index['out_facilities_name'])
num_facilities_to_find = arcpy.GetParameter(parameter_index['num_facilities_to_find'])
str_default_cutoff = arcpy.GetParameterAsText(parameter_index['default_cutoff'])
default_cutoff = float(str_default_cutoff) if str_default_cutoff else None
travel_direction = arcpy.GetParameterAsText(parameter_index['travel_direction'])
time_of_day = arcpy.GetParameter(parameter_index['time_of_day'])
time_of_day_usage = arcpy.GetParameterAsText(parameter_index['time_of_day_usage'])
time_zone_usage = arcpy.GetParameterAsText(parameter_index['time_zone_usage'])
uturn_policy = arcpy.GetParameterAsText(parameter_index['uturn_policy'])
point_barriers = arcpy.GetParameter(parameter_index['point_barriers'])
line_barriers = arcpy.GetParameter(parameter_index['line_barriers'])
polygon_barriers = arcpy.GetParameter(parameter_index['polygon_barriers'])
time_attribute = arcpy.GetParameterAsText(parameter_index['time_attribute'])
time_attribute_units = arcpy.GetParameterAsText(parameter_index['time_attribute_units'])
distance_attribute = arcpy.GetParameterAsText(parameter_index['distance_attribute'])
distance_attribute_units = arcpy.GetParameterAsText(parameter_index['distance_attribute_units'])
use_hierarchy = arcpy.GetParameter(parameter_index['use_hierarchy'])
restrictions = arcpy.GetParameterAsText(parameter_index['restrictions'])
attribute_parameters = arcpy.GetParameter(parameter_index['attribute_parameters'])
accumulate_attributes = arcpy.GetParameterAsText(parameter_index['accumulate_attributes'])
max_snap_tolerance = arcpy.GetParameterAsText(parameter_index['max_snap_tolerance'])
feature_locator_where_clause = arcpy.GetParameterAsText(parameter_index['feature_locator_where_clause'])
route_shape = arcpy.GetParameterAsText(parameter_index['route_shape'])
route_line_simplification_tolerance = arcpy.GetParameterAsText(parameter_index['route_line_simplification_tolerance'])
populate_directions = arcpy.GetParameter(parameter_index['populate_directions'])
directions_language = arcpy.GetParameterAsText(parameter_index['directions_language'])
directions_distance_units = arcpy.GetParameterAsText(parameter_index['directions_distance_units'])
directions_style_name = arcpy.GetParameterAsText(parameter_index['directions_style_name'])
str_max_features_point_barriers = arcpy.GetParameterAsText(parameter_index['max_features_point_barriers'])
str_max_features_line_barriers = arcpy.GetParameterAsText(parameter_index['max_features_line_barriers'])
str_max_features_polygon_barriers = arcpy.GetParameterAsText(parameter_index['max_features_polygon_barriers'])
str_max_facilities = arcpy.GetParameterAsText(parameter_index['max_facilities'])
str_max_facilities_to_find = arcpy.GetParameterAsText(parameter_index['max_facilities_to_find'])
str_max_incidents = arcpy.GetParameterAsText(parameter_index['max_incidents'])
str_force_hierarchy_beyond_distance = arcpy.GetParameterAsText(parameter_index['force_hierarchy_beyond_distance'])
save_output_layer = arcpy.GetParameter(parameter_index['save_output_layer'])

#Derived outputs values. These are set to parameter values in finally block.
out_routes_fc = os.path.join(out_gdb_workspace, out_routes_name)
out_directions_fc = os.path.join(out_gdb_workspace, out_directions_name)
out_facilities_fc = os.path.join(out_gdb_workspace, out_facilities_name)
solve_succeeded = False
cf_layer_exists = False

#These are deleted in finally block if datasets referenced by objects exists
input_copies = []



try:
    #Check out network analyst extension
    arcpy.CheckOutExtension("network")

    measurement_method = "TRAVEL_TIME" if measurement_units.lower() in TIME_UNITS else "TRAVEL_DISTANCE"
    #Convert constraint values from strings to number. If empty string use max Int
    max_features_point_barriers = int(str_max_features_point_barriers) if str_max_features_point_barriers else INFINITY
    max_features_line_barriers = int(str_max_features_line_barriers) if str_max_features_line_barriers else INFINITY
    max_features_polygon_barriers = int(str_max_features_polygon_barriers) if str_max_features_polygon_barriers else INFINITY
    max_facilities = int(str_max_facilities) if str_max_facilities else INFINITY
    max_facilities_to_find = int(str_max_facilities_to_find) if str_max_facilities_to_find else INFINITY
    max_incidents = int(str_max_incidents) if str_max_incidents else INFINITY
    force_hierarchy_beyond_distance = float(str_force_hierarchy_beyond_distance) if str_force_hierarchy_beyond_distance else INFINITY
    
    #Check if the output feature class names are valid. Fail with first invalid name
    nau.check_valid_table_name(out_routes_name, out_gdb_workspace, 30101,
                               parameter_info[parameter_index['out_routes_name']].displayName)
    nau.check_valid_table_name(out_directions_name, out_gdb_workspace, 30101,
                               parameter_info[parameter_index['out_directions_name']].displayName)
    nau.check_valid_table_name(out_facilities_name, out_gdb_workspace, 30101,
                               parameter_info[parameter_index['out_facilities_name']].displayName)
    
    desc_nds = arcpy.Describe(network_dataset)
    desc_nds_attributes = desc_nds.attributes
    
    #Convert all input features to feature sets or recordsets if they are not
    #This is required as if input is passed a feature layer or feature class
    #We will end up directly modifying the inputs
    
    facilities_obj = nau.InputFeatureClass(facilities)
    #Store the OBJECTID field for facilities as it will used later when exporting output facilities
    orig_input_facilities_oid = facilities_obj.origOIDFieldName
    #Store all the fields names from input facilities to be used later when exporting output facilities
    orig_input_facilities_fld_names = facilities_obj.fieldNames
    incidents_obj = nau.InputFeatureClass(incidents)
    point_barriers_obj = nau.InputFeatureClass(point_barriers)
    line_barriers_obj = nau.InputFeatureClass(line_barriers)
    polygon_barriers_obj = nau.InputFeatureClass(polygon_barriers)
    attribute_parameters_obj = nau.InputTable(attribute_parameters)
    #Keep a list of input copies so we can delete them just before exit
    input_copies = (facilities_obj, incidents_obj, point_barriers_obj, line_barriers_obj,
                    polygon_barriers_obj, attribute_parameters_obj)    
    
    #If the network dataset does not support hierarchy, set the useHierarchy parameter to false.
    nds_has_hierarchy = nau.nds_supports_hierarchy(desc_nds_attributes)
    if not nds_has_hierarchy:
        use_hierarchy = False

    #determine whether we should use time based or distance based impedance attribute based on measurement method
    impedance_attribute = time_attribute if measurement_method == "TRAVEL_TIME" else distance_attribute
    impedance_units = nau.verify_impedance_units(time_attribute, time_attribute_units, distance_attribute,
                                                 distance_attribute_units, desc_nds_attributes, False)[impedance_attribute]

    #If the Cutoff is specified, convert the cutoff value from user specified unit to impedance unit
    if default_cutoff:
        converted_cutoff = nau.convert_units(default_cutoff, measurement_units, impedance_units)
    else:
        converted_cutoff = default_cutoff

    #Get counts for facilities, incidents, barrier features and attribute parameters
    facility_count = facilities_obj.count
    incident_count = incidents_obj.count
    
    #Convert inputs from record sets to feature classes if they are not empty.
    if facility_count:
        facilities_obj.copyFeatures(out_gdb_workspace, FACILITIES_FIELDS)
        facilities = facilities_obj.catalogPath
    
    if incident_count:
        incidents_obj.copyFeatures(out_gdb_workspace, INCIDENTS_FIELDS)
        incidents = incidents_obj.catalogPath
    
    if point_barriers_obj.count:
        point_barriers_obj.copyFeatures(out_gdb_workspace, POINT_BARRIER_FIELDS)
        point_barriers = point_barriers_obj.catalogPath
    
    if line_barriers_obj.count:
        line_barriers_obj.copyFeatures(out_gdb_workspace, LINE_BARRIER_FIELDS)
        line_barriers = line_barriers_obj.catalogPath
    
    if polygon_barriers_obj.count:
        polygon_barriers_obj.copyFeatures(out_gdb_workspace, POLYGON_BARRIER_FIELDS)
        polygon_barriers = polygon_barriers_obj.catalogPath
    
    if attribute_parameters_obj.count:
        attribute_parameters_obj.copyFeatures(out_gdb_workspace, ATTRIBUTE_PARAMETER_FIELDS)
        attribute_parameters = attribute_parameters_obj.catalogPath
    

    ##Determine if the throttling conditions are met. If not raise an exception and quit
    ##If throttling parameters have zero value, then do not perform throttling checks.
    # Throttling Check 1: Check for number of facilities
    if facility_count == 0:
        arcpy.AddIDMessage("ERROR",30125)
        raise nau.InputError()
    if str_max_facilities and facility_count > max_facilities:
        arcpy.AddIDMessage("ERROR", 30096,"Facilities", max_facilities)
        raise nau.InputError()
    # Throttling Check 2: Check for number of incidents
    if incident_count == 0:
        arcpy.AddIDMessage("ERROR",30125)
        raise nau.InputError()
    if str_max_incidents and incident_count > max_incidents:
        arcpy.AddIDMessage("ERROR", 30096,"Incidents", max_incidents)
        raise nau.InputError()    

    #Throttling Check 3: Check for number of facilities to find
    if str_max_facilities_to_find and num_facilities_to_find > max_facilities_to_find:
        arcpy.AddIDMessage("ERROR",30126, num_facilities_to_find, max_facilities_to_find)
        raise nau.InputError()
    
    #Throttling Check 4: Check if hierarchy needs to be forced
    if str_force_hierarchy_beyond_distance and use_hierarchy == False:
        #force to use hierarchy. If the NDS does not support hierarchy raise an error and quit.
        if nds_has_hierarchy:
            max_distance_between_locations = max_distance_between_points((facilities, incidents))
            converted_max_distance = float(nau.convert_units(max_distance_between_locations, "Meters", distance_attribute_units))
            if converted_max_distance > force_hierarchy_beyond_distance:
                use_hierarchy = True
                #Report the exceeded value in measurement units if using TRAVEL_DISTANCE. Otherwise report the
                #exceeded value in distance attribute units which are input units for force hierarchy constraint
                if measurement_method == "TRAVEL_DISTANCE":
                    converted_force_hierarchy_beyond_distance = nau.convert_units(force_hierarchy_beyond_distance,
                                                                                  distance_attribute_units,
                                                                                  measurement_units)
                    report_value_with_units = "{0} {1}".format(converted_force_hierarchy_beyond_distance, measurement_units)
                else:
                    report_value_with_units = "{0} {1}".format(force_hierarchy_beyond_distance, distance_attribute_units)                
                arcpy.AddIDMessage("WARNING", 30109)
                arcpy.AddIDMessage("WARNING", 30127, report_value_with_units)
        else:
            arcpy.AddIDMessage("ERROR", 30119, "Force Hierarchy beyond Distance")
            raise nau.InputError()            



    #Throttling Check 5: Check if the number of barrier features (point, line and polygon) are within maximum allowed
    load_point_barriers, load_line_barriers, load_polygon_barriers = nau.check_barriers(point_barriers_obj, line_barriers_obj,
                                                                                        polygon_barriers_obj, max_features_point_barriers,
                                                                                        max_features_line_barriers,
                                                                                        max_features_polygon_barriers, desc_nds)
    ##Perform the closest facility analysis as all throttling conditions are met.
    #Get the restrictions and accumulate attributes that are valid for the network dataset
    if restrictions:
        restrictions_to_use = nau.get_valid_attributes(desc_nds_attributes, restrictions)
    else:
        restrictions_to_use = []
    
    #Determine the accumulation attributes to use
    #Get only the attributes that are valid for the current network dataset.
    if accumulate_attributes:    
        accumulate_attributes = nau.get_valid_attributes(desc_nds_attributes, accumulate_attributes,
                                                                "Cost", 30128)
        #remove time attribute and distance attribute from the list of accumulate attributes as we will manage
        #these attributes seperately.
        if time_attribute in accumulate_attributes:
            accumulate_attributes.remove(time_attribute)
        if distance_attribute in accumulate_attributes:
            accumulate_attributes.remove(distance_attribute)
            
    else:
        accumulate_attributes = []
    #Always accumate time or distance attribute based on measurement method.
    if measurement_method == "TRAVEL_TIME":
        system_accumulate_attribute = [distance_attribute]
    else:
        system_accumulate_attribute = [time_attribute]
    accumulate_attributes_to_use = accumulate_attributes + system_accumulate_attribute    
    
    #Make a new closest facility layer
    cf_layer = arcpy.na.MakeClosestFacilityLayer(network_dataset, NA_LAYER, impedance_attribute, travel_direction,
                                                 converted_cutoff, num_facilities_to_find, accumulate_attributes_to_use,
                                                 uturn_policy, restrictions_to_use,use_hierarchy,None, route_shape,
                                                 time_of_day, time_of_day_usage).getOutput(0)
    cf_layer_exists = True
    na_class_names = arcpy.na.GetNAClassNames(cf_layer)
    solver_props = arcpy.na.GetSolverProperties(cf_layer)
    
    #Set time zone usage if time of day is specified
    if time_of_day:
        solver_props.timeZoneUsage = time_zone_usage
    
    #Add attribute parameters if specified
    nau.update_attribute_parameters(cf_layer, attribute_parameters,
                                    restrictions_to_use + accumulate_attributes_to_use + [impedance_attribute], desc_nds_attributes)
    #Add Barriers before loading facilities and incidents as we want to exclude restricted portions
    if load_point_barriers:
        #point_barrier_fields = arcpy.ListFields(point_barriers)
        nau.add_locations(cf_layer, "Barriers", point_barriers_obj, impedance_attribute, impedance_units,
                          measurement_units, max_snap_tolerance, feature_locator_where_clause, measurement_method)
    if load_line_barriers:
        #line_barrier_fields = arcpy.ListFields(line_barriers)
        nau.add_locations(cf_layer, "PolylineBarriers", line_barriers_obj, impedance_attribute, impedance_units,
                          measurement_units, max_snap_tolerance, feature_locator_where_clause, measurement_method)
    if load_polygon_barriers:
        #polygon_barrier_fields = arcpy.ListFields(polygon_barriers)
        nau.add_locations(cf_layer, "PolygonBarriers", polygon_barriers_obj, impedance_attribute,
                          impedance_units, measurement_units, max_snap_tolerance, feature_locator_where_clause,
                          measurement_method)        

    #Add facilities
    #facility_fields = arcpy.ListFields(facilities)
    facility_fields = facilities_obj.describeObject.fields
    facility_id_field = nau.find_field(facilities, facility_fields, ID_FIELD_NAME)
    propogate_facility_ids = True if facility_id_field else False
    nau.add_locations(cf_layer, "Facilities", facilities_obj, impedance_attribute, impedance_units,
                      measurement_units, max_snap_tolerance, feature_locator_where_clause, measurement_method, 
                      propogate_facility_ids, facility_id_field)

    #Add Incidents
    #incident_fields = arcpy.ListFields(incidents)
    incident_fields = incidents_obj.describeObject.fields
    incident_id_field = nau.find_field(incidents, incident_fields, ID_FIELD_NAME)
    propogate_incident_ids = True if incident_id_field else False
    nau.add_locations(cf_layer, "Incidents", incidents_obj, impedance_attribute, impedance_units,
                      measurement_units, max_snap_tolerance, feature_locator_where_clause, measurement_method,
                      propogate_incident_ids, incident_id_field)

    #Solve
    solve_result = arcpy.na.Solve(cf_layer,"SKIP","TERMINATE", route_line_simplification_tolerance)
    cf_sub_layers = {k.datasetName:k for k in arcpy.mapping.ListLayers(cf_layer)[1:]}
    routes_sub_layer = cf_sub_layers["CFRoutes"]
    routes_sub_layer_name = na_class_names["CFRoutes"]
    if solve_result.getOutput(1).lower() == 'true':
        solve_succeeded = True
    else:
        solve_succeeded = False
    if solve_result.maxSeverity == 1:
        nau.print_message(solve_result.getMessages(1), 1)
        
    #Get a list of cost attributes and their units to check if we need to calculate new fields when reporting
    #accumulated attribute values.
    cost_attributes = {}
    for attr in desc_nds_attributes:
        if attr.usageType == "Cost":
            cost_attributes[attr.name] = attr.units
    #Get a list of Total_ fields from the routes sub layer
    routes_sub_layer_field_names = [f.name for f in arcpy.Describe(routes_sub_layer).fields]
    cost_field_names = fnmatch.filter(routes_sub_layer_field_names, "Total_*")

    initial_facility_id_field_name = "Facilities" + ID_FIELD_NAME
    initial_incident_id_field_name = "Incidents" + ID_FIELD_NAME
    
    #Transfer the FacdilityOID and IncidentOID fields from incidents and facilities to routes
    #Propogate incident or facilities ID to routes layer if required.
    facility_join_fields = ["FacilityOID"]
    if propogate_facility_ids:
        facility_join_fields.append(initial_facility_id_field_name)
    arcpy.management.JoinField(routes_sub_layer, "FacilityID", cf_sub_layers["Facilities"], "ObjectID",
                               facility_join_fields)
    incident_join_fields = ["IncidentOID"]
    if propogate_incident_ids:
        incident_join_fields.append(initial_incident_id_field_name)
    arcpy.management.JoinField(routes_sub_layer, "IncidentID", cf_sub_layers["Incidents"], "ObjectID",
                               incident_join_fields)
    
    #Save the output layer. The layer name is based on random guid    
    if save_output_layer:
        scratch_folder = arcpy.env.scratchFolder
        uid = str(uuid.uuid4()).replace("-","")
        na_layer_file_name = "_ags_gpna{0}.lyr".format(uid)
        output_layer_file = os.path.join(scratch_folder, na_layer_file_name)
        arcpy.management.SaveToLayerFile(cf_layer,output_layer_file)
        arcpy.AddIDMessage("INFORMATIVE", 30124, na_layer_file_name)    
    
    #Export the selected facilities as a new feature class
    #Get the original facilities features before they were copied
    orig_input_facilities = facilities_obj.inputFeatures
    #Make a layer so we can use AddJoin
    orig_input_facilities_lyr = "OrigInputFacilitiesLayer"
    arcpy.management.MakeFeatureLayer(orig_input_facilities, orig_input_facilities_lyr)
    #Make a join based on FacilityOID from routes sublayer and OID from orig_input_facilities
    arcpy.management.AddJoin(orig_input_facilities_lyr, orig_input_facilities_oid, routes_sub_layer, "FacilityOID")
    where_clause = "CFRoutes.FacilityOID IS NOT NULL"
    arcpy.management.SelectLayerByAttribute(orig_input_facilities_lyr, "NEW_SELECTION", where_clause)
    arcpy.management.RemoveJoin(orig_input_facilities_lyr, "CFRoutes")
    #Transfer all attributes and the OID as ORIG_ID.
    #If ORIG_ID already exists, get a unique field name such as ORIG_ID_1
    fac_fms = arcpy.FieldMappings()
    fac_fms.addTable(orig_input_facilities_lyr)
    fac_fm = arcpy.FieldMap()
    fac_fm.addInputField(orig_input_facilities_lyr, orig_input_facilities_oid)
    out_fld = fac_fm.outputField
    unique_fld_name = nau.get_unique_field_name("ORIG_FID", orig_input_facilities_fld_names)
    out_fld.name = unique_fld_name
    out_fld.aliasName = unique_fld_name
    fac_fm.outputField = out_fld
    fac_fms.addFieldMap(fac_fm)
    arcpy.conversion.FeatureClassToFeatureClass(orig_input_facilities_lyr, out_gdb_workspace,
                                                out_facilities_name,field_mapping=fac_fms)
    #arcpy.management.CopyFeatures(orig_input_facilities_lyr, out_facilities_fc)

    #Prepare the field mappings for the routes layer before exporting it to a feature class.        
    routes_feature_layer = "CFRoutes_Layer"
    arcpy.management.MakeFeatureLayer(routes_sub_layer, routes_feature_layer)
    field_mappings = arcpy.FieldMappings()
    field_mappings.addTable(routes_feature_layer)
    #Change the data type of FacilityID and IncidentID fields from Integer to Text
    type_update = {"type" : "TEXT", "length" : 50}
    nau.update_field_map_output_field(field_mappings, "FacilityID", type_update)
    nau.update_field_map_output_field(field_mappings, "IncidentID", type_update)
    
    name_update = dict.fromkeys(("name", "aliasName"), "")
    #Rename all accumate_attribute fields to Total_attributename_units
    for attr in accumulate_attributes:
        orig_name = "Total_" + attr
        new_name = "Total_{0}_{1}".format(attr, cost_attributes.get(attr, ""))
        name_update["name"] = new_name
        name_update["aliasName"] = new_name
        nau.update_field_map_output_field(field_mappings, orig_name, name_update)
    #Rename the time attribute and distance attribute as Total_Units
    time_cost_field = "Total_{0}".format(time_attribute_units)
    distance_cost_field = "Total_{0}".format(distance_attribute_units)
    name_update["name"] = time_cost_field
    name_update["aliasName"] = time_cost_field
    nau.update_field_map_output_field(field_mappings, "Total_" + time_attribute, name_update)
    name_update["name"] = distance_cost_field
    name_update["aliasName"] = distance_cost_field
    nau.update_field_map_output_field(field_mappings, "Total_" + distance_attribute, name_update)        

    out_routes_fc_fld_names = [f.name for f in field_mappings.fields]
    #save routes to the feature class
    arcpy.conversion.FeatureClassToFeatureClass(routes_sub_layer, out_gdb_workspace, out_routes_name,"",
                                                field_mappings)
    
    #Make sure the cost is reported in expected units
    #values in the dict are the field from which to derive the value, units for field value, units to convert the value into.    
    system_unit_cost_field_names = {"Total_Minutes" : (0, time_attribute_units, "Minutes"),
                                    "Total_Miles" : (1, distance_attribute_units, "Miles"),
                                    "Total_Kilometers": (1, distance_attribute_units, "Kilometers")
                                    }
    measurement_unit_cost_field = "Total_" + measurement_units.replace(" ", "")
    if not measurement_unit_cost_field in system_unit_cost_field_names:
        if measurement_method == "TRAVEL_TIME":
            system_unit_cost_field_names[measurement_unit_cost_field] = (0, time_attribute_units, measurement_units)
        else:
            system_unit_cost_field_names[measurement_unit_cost_field] = (1, distance_attribute_units, measurement_units)
    #determine the cost fields we need to convert units and store how the value should be converted
   
    cost_fields_to_calc = []
    for system_unit in system_unit_cost_field_names:
        if not system_unit in out_routes_fc_fld_names:
            arcpy.management.AddField(out_routes_fc, system_unit, "DOUBLE")
            cost_fields_to_calc.append(system_unit)
    
    if cost_fields_to_calc:
        
        with arcpy.da.UpdateCursor(out_routes_fc, [time_cost_field, distance_cost_field] + cost_fields_to_calc) as cursor:
            cursor_fld_names = cursor.fields
            for row in cursor:
                for i in range(2,len(cost_fields_to_calc) + 2):
                    field_name = cursor_fld_names[i]
                    src_value, from_unit, to_unit = system_unit_cost_field_names[field_name]
                    row[i] = nau.convert_units(row[src_value], from_unit, to_unit)
                cursor.updateRow(row)
        
    #Update IncidentID and FacilityID fields if ids were propogated
    if propogate_facility_ids:
        arcpy.management.CalculateField(out_routes_fc, "FacilityID", 
                                        "!{0}!".format(initial_facility_id_field_name),"PYTHON")
        arcpy.management.DeleteField(out_routes_fc, initial_facility_id_field_name)
    if propogate_incident_ids:
        arcpy.management.CalculateField(out_routes_fc, "IncidentID",
                                        "!{0}!".format(initial_incident_id_field_name),"PYTHON")
        arcpy.management.DeleteField(out_routes_fc, initial_incident_id_field_name)

    #Save directions
    streetdirprops = None
    if populate_directions:
        
        streetdirprops = solver_props.streetDirectionsProperties
        if not streetdirprops:
            arcpy.AddIDMessage("WARNING",30129)
            populate_directions = False

    if populate_directions:                   
        statemgr = nau.StreetDirPropsStateResetManager(streetdirprops)

        streetdirprops.timeAttribute = time_attribute
        streetdirprops.lengthUnits = directions_distance_units
        try:
            if directions_language:
                streetdirprops.language = directions_language
        except Exception as ex:
            default_language = streetdirprops.language
            if default_language != directions_language:
                arcpy.AddIDMessage("WARNING",30099, default_language, directions_language)
        try:
            if directions_style_name:
                streetdirprops.styleName = directions_style_name
        except Exception as ex:
            default_style_name = streetdirprops.styleName
            if default_style_name != directions_style_name:
                arcpy.AddIDMessage("WARNING", 30100, default_style_name, directions_style_name)
        
        streetdirprops.outputSpatialReference = arcpy.env.outputCoordinateSystem

        arcpy.na.GenerateDirectionsFeatures(cf_layer, out_directions_fc, False)

        del statemgr
    else:
        arcpy.na.GenerateDirectionsFeatures(cf_layer, out_directions_fc, True)        

    streetdirprops = None
    
        

except nau.InputError as ex:
    #Handle errors due to throttling conditions
    solve_succeeded = False
    if ex.message:
        nau.print_message(ex.message)
except arcpy.ExecuteError:
    #Handle GP exceptions
    solve_succeeded = False    
    if DEBUG:
        #Get the line number at which the GP error occurred
        tb = sys.exc_info()[2]
        nau.print_message("A geoprocessing error occurred in File %s, line %s" % (__file__, tb.tb_lineno))
    else:
        nau.print_message("A geoprocessing error occurred.")
    warning_messages = arcpy.GetMessages(1) 
    if warning_messages:    
        nau.print_message(warning_messages, 1)
    nau.print_message(arcpy.GetMessages(2))
except:
    #Handle python errors
    solve_succeeded = False
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
    if cf_layer_exists:
        try:
            arcpy.management.Delete(cf_layer)
        except:
            pass
    #Delete copies of inputs
    for obj in input_copies:
        if obj:
            obj.deleteCopy()
    
    arcpy.SetParameter(parameter_index['solve_succeeded'], solve_succeeded)
    arcpy.SetParameterAsText(parameter_index['out_routes'], out_routes_fc)
    arcpy.SetParameterAsText(parameter_index['out_directions'], out_directions_fc)
    arcpy.SetParameterAsText(parameter_index['out_facilities'], out_facilities_fc)
