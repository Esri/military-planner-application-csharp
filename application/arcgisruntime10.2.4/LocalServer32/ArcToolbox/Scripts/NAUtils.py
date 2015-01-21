"""
Source Name:   NAUtils.py
Version:       ArcGIS 10.2.1
Author:        Environmental Systems Research Institute Inc.
Description:   Utility Functions for Network Analyst Script Tools.
"""

#Imports
import arcpy
import sys
import os
import locale

class InputError(Exception):
    '''Raise this expection whenever a throtlling condition is not met'''
    pass

class StreetDirPropsStateResetManager(object):
    """Support for stateless export directions usage.

    The directions properties that can be edited for a given
    analysis are restored when objects of this class are deleted if
    intialized before editing properties.
    """    

    streetDirProps = None
    propvalues = {}

    def __init__(self, streetDirProps=None):      
        self.backup(streetDirProps)

    def __del__(self):
        self.restore()

    def backup(self, streetDirProps):      
        self.streetDirProps = streetDirProps	  
        if streetDirProps == None: return

        try:     
            self.propvalues["timeAttribute"] = streetDirProps.timeAttribute
            self.propvalues["lengthUnits"] = streetDirProps.lengthUnits
            self.propvalues["outputSpatialReference"] = streetDirProps.outputSpatialReference
            self.propvalues["language"] = streetDirProps.language
            self.propvalues["styleName"] = streetDirProps.styleName
        except Exception as ex:
            pass

    def restore(self):      
        if self.streetDirProps == None: return

        try:
            self.streetDirProps.timeAttribute = self.propvalues["timeAttribute"]
            self.streetDirProps.lengthUnits = self.propvalues["lengthUnits"]
            self.streetDirProps.outputSpatialReference = self.propvalues["outputSpatialReference"]
            try:
                self.streetDirProps.language = self.propvalues["language"]
            except:
                pass
            try:   
                self.streetDirProps.styleName = self.propvalues["styleName"]
            except:
                pass
        except Exception as ex:
            pass

def print_message(message, severity=2, log_file=None):
    '''Adds a GP message based on severity. If a log file object is given, the messages is also
    written to the logfile. When writing to a file, a new line will be added to the message
    '''
    message = message.strip()
    if message:
        if severity == 0:
            arcpy.AddMessage(message)
        elif severity == 1:
            arcpy.AddWarning(message)
        elif severity == 2:
            arcpy.AddError(message)
        if log_file:
            log_file.write(message)
            log_file.write("\n")


def nds_supports_hierarchy(network_attributes):
    '''Returns a boolean indicating if a network dataset supports hierarchy. The input argument is a list of network dataset 
    attributes object obtained from network dataset describe object'''
    supports_hierarchy = True
    for attr in network_attributes:
        if attr.usageType.lower() == 'hierarchy':
            supports_hierarchy = True
            break
    else:
        #reach here only if break statement is never reached in for loop.
        supports_hierarchy = False
    return supports_hierarchy

def float_to_string(value, rounding_precision=5):
    '''Converts a floating point number to a string rouding off the number to the given number of digits. 
    For example, float_to_string(2.0, 5) returns 2.00000. Note that float_to_string(0, 5) returns 0.00000 
    '''
    if isinstance(value, (float,int,long)):
        floatToStringConverter = "%." + str(rounding_precision) + "f"
        return locale.format(floatToStringConverter, value)
    else:
        return value     
    #float_to_string_converter = "%." + str(rounding_precision) + "f"
    #return float_to_string_converter % float(value)

def convert_units(value, from_unit, to_unit, rounding_precision=5):
    '''Convert values from one unit to another. value can be a list or a single number represented as 
    string. The function maintains the type for the returned value. For example, If the input value is list
    of string numbers, the output is list of converted string numbers. A single number is always returned 
    as a string as we are using floats for performing arithmetic and don't want to loose precision.
    '''
    TIME_UNITS = ('minutes','hours','days', 'seconds')
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()
    if from_unit == "nautical miles":
        from_unit = "nauticalmiles"
    if to_unit == "nautical miles":
        to_unit == "nauticalmiles"
    #determine if the value is a list. If not we assume it is a single number passed as a number or a string.    
    is_input_value_list = isinstance(value,list)
    #if the from and to units are same, just return the original value
    if from_unit == to_unit:
        if is_input_value_list:
            #return a copy of the original list but converted to string of necessary precision
            converted_value = [float_to_string(val, rounding_precision) for val in value]
            return converted_value
        else:
            #make sure for a single number we always returned a string that is rounded as per global 
            #precision.
            return float_to_string(value, rounding_precision)
    #Determine if we are doing a conversion between time units or distance units    
    BASE_DISTANCE_UNIT = 'meters'
    BASE_TIME_UNIT = 'minutes'
    #python ternary operator. A if C else B
    base_unit = BASE_TIME_UNIT if from_unit in TIME_UNITS else BASE_DISTANCE_UNIT
    #Store the constants that convert from one unit to another in a dictionary. Key is the tuple (from unit, to unit)
    #Value is the conversion constant.    
    conversion_from_meters = {('meters', 'kilometers') : 0.001,
                              ('meters', 'feet') : 3.2808399,
                              ('meters', 'miles') : 0.000621371192,
                              ('meters', 'yards') : 1.0936133,
                              ('meters', 'nauticalmiles') : 0.000539956803,
                              }
    conversion_to_meters = {('kilometers', 'meters') : 1000.0,
                            ('feet', 'meters') : 0.3048,
                            ('miles', 'meters') : 1609.344,
                            ('yards', 'meters') : 0.9144,
                            ('nauticalmiles', 'meters') : 1852.0,
                            ('meters', 'meters') : 1.0
                            }
    conversion_from_minutes = {('minutes', 'hours') : 0.0166666667,
                               ('minutes', 'days') : 0.000694444444,
                               ('minutes', 'seconds') : 60.0,
                               }
    conversion_to_minutes = {('hours', 'minutes') : 60.0,
                             ('days', 'minutes') : 1440.0,
                             ('seconds', 'minutes') : 0.0166666667,
                             ('minutes', 'minutes') : 1.0,
                             }
    #We first convert value in the 'from unit' to a value in the base unit and then from base unit to the to unit.        
    dict_key1 = (from_unit,base_unit)
    dict_key2 = (base_unit, to_unit)
    #Get the first and second conversion constants from the appropriate dicts. If key is not found use conversion
    #constant equal to 1.    
    if base_unit == BASE_DISTANCE_UNIT:        
        first_constant_to_use = conversion_to_meters.get(dict_key1,1.0)
        second_constant_to_use = conversion_from_meters.get(dict_key2,1.0)
    else:
        first_constant_to_use = conversion_to_minutes.get(dict_key1,1.0)
        second_constant_to_use = conversion_from_minutes.get(dict_key2,1.0)
    #If the input value is not a list, then it must be a number    
    if is_input_value_list:
        converted_value = []
        for val in value:
            new_val = (locale.atof(val) * first_constant_to_use) * second_constant_to_use
            converted_value.append(float_to_string(new_val,rounding_precision))
    else:
        if isinstance(value, (str, unicode)):
            converted_value = (locale.atof(value) * first_constant_to_use) * second_constant_to_use
        else:
            converted_value = (float(value) * first_constant_to_use) * second_constant_to_use
        converted_value = float_to_string(converted_value, rounding_precision)
    return converted_value

def verify_impedance_units(time_impedance, time_impedance_units, distance_impedance, distance_impedance_units,
                           desc_nds_attributes, use_describe=False):
    '''Determine the units for the distance and time impedance attributes. Returns a dictionary with key as
    impedance attribute name and value as impedance units. use_describe determines if we find the units based
    on the network dataset describe object or just use the function arguments.
    '''

    impedance_units = {time_impedance: '', distance_impedance: ''}
    #If we somehow don't have impedance units, then use describe even if use_describe is false.
    if time_impedance:
        if not time_impedance_units:
            use_describe = True
    if distance_impedance:
        if not distance_impedance_units:
            use_describe = True
    if use_describe:    
        for attr in desc_nds_attributes:
            # we don't want to loop through all the attributes. So if all the dict values no longer
            #contain empty strings, then break
            if all(impedance_units.values()):
                break
            else:
                if attr.UsageType == 'Cost':
                    if attr.name in impedance_units:
                        impedance_units[attr.name] = attr.units
    else:
        impedance_units[time_impedance] = time_impedance_units
        impedance_units[distance_impedance] = distance_impedance_units
    return impedance_units

def check_barriers(point_barriers_obj, line_barriers_obj, polygon_barriers_obj,
                   max_features_point_barriers, max_features_line_barriers,
                   max_features_polygon_barriers, desc_nds ):
    '''Checks if the input point, line and polygons barriers do not intersect more than specified
    edge features. Returns a three value boolean list (point barriers, line barriers, polygon barriers)
    indicating which barrier types should be loaded for analysis.
    inputs barriers are NAUtils.InputFeatureClass objects
    '''
    INFINITY = sys.maxint
    #point_barrier_count = int(arcpy.management.GetCount(point_barriers).getOutput(0))
    #line_barrier_count = int(arcpy.management.GetCount(line_barriers).getOutput(0))
    #polygon_barrier_count = int(arcpy.management.GetCount(polygon_barriers).getOutput(0))
    nds_catalog_path = desc_nds.catalogPath
    barriers_to_load = [False,False,False]
    edge_feature_class = ""
    #Check for point barriers
    if point_barriers_obj.count:
        point_barriers_lyr = arcpy.management.MakeFeatureLayer(point_barriers_obj.catalogPath, "PointBarriersLayer").getOutput(0)
        if max_features_point_barriers != INFINITY and not arcpy.na.CheckIntersectingFeatures(nds_catalog_path,
                                                                                              point_barriers_lyr,
                                                                                              max_features_point_barriers):
            barriers_to_load[0] = False
            arcpy.AddIDMessage("ERROR", 30095, "Barriers", max_features_point_barriers)
            raise InputError()
        else:
            #we do not check how many edges are intersected by point barriers. We assume that each point
            #barrier intersects one edge            
            barriers_to_load[0] = True  
    else:
        barriers_to_load[0] = False
    #Check for line barriers
    if line_barriers_obj.count:
        if max_features_line_barriers != INFINITY:
            line_barriers_lyr = arcpy.management.MakeFeatureLayer(line_barriers_obj.catalogPath, "LineBarriersLayer").getOutput(0)
            if arcpy.na.CheckIntersectingFeatures(nds_catalog_path, line_barriers_lyr, max_features_line_barriers):
                barriers_to_load[1] = True
            else:
                barriers_to_load[1] = False
                arcpy.AddIDMessage("ERROR", 30095, "PolylineBarriers", max_features_line_barriers)                
                raise InputError()
        else:
            barriers_to_load[1] = True
    else:
        barriers_to_load[1] = False
    #Check for polygon barriers    
    if polygon_barriers_obj.count:
        if max_features_polygon_barriers != INFINITY:
            polygon_barriers_lyr = arcpy.management.MakeFeatureLayer(polygon_barriers_obj.catalogPath, "PolygonBarriersLayer").getOutput(0)
            if arcpy.na.CheckIntersectingFeatures(nds_catalog_path, polygon_barriers_lyr, max_features_polygon_barriers):
                barriers_to_load[2] = True
            else:
                barriers_to_load[2] = False
                arcpy.AddIDMessage("ERROR", 30095, "PolygonBarriers", max_features_polygon_barriers)                
                raise InputError()
        else:
            barriers_to_load[2] = True
    else:
        barriers_to_load[2] = False
    return barriers_to_load

def get_valid_attributes(desc_nds_attributes, input_attributes, attribute_type="Restriction", warning_message_id=30113):
    '''Return a list of attributes such as restrictions and cost that are valid for the network dataset. 
    Report invaid attributes as warnings. input_attributes is the semicolon seperated string containing the
    attributes specified as input.'''

    #Get a list of all the attributes that the network dataset supports
    nds_attributes = [attribute.name for attribute in desc_nds_attributes
                      if attribute.usageType == attribute_type]
    nds_attributes_set = set(nds_attributes)
    #ensure that we do not have single quotes in multi word attribute names
    #For example split will give us "'Non-routeable Segments'" but we need "Non-routeable Segments"
    input_attributes_set = set([x.lstrip("'").rstrip("'") for x in input_attributes.split(";")])
    attributes_to_use_set = input_attributes_set.intersection(nds_attributes_set)
    unused_attributes = list(input_attributes_set - attributes_to_use_set) 
    if unused_attributes:
        arcpy.AddIDMessage("WARNING", warning_message_id, ", ".join(unused_attributes))

    return list(attributes_to_use_set)

def update_attribute_parameters(na_layer, attribute_parameters, analysis_attributes, desc_nds_attributes):
    '''update attribute parameters on the network analysis layer.'''

    ATTRIBUTE_PARAMETERS_FIELDS = ("AttributeName", "ParameterName", "ParameterValue")
    #Get the count for attribute parameters.
    attribute_parameter_count = int(arcpy.management.GetCount(attribute_parameters).getOutput(0))

    if attribute_parameter_count:
        na_layer_solver_props = arcpy.na.GetSolverProperties(na_layer)
        nds_attributes = [attr.name for attr in desc_nds_attributes]
        #if the record set does not have necessary fields, raise and error message and quit
        attribute_parameters_field_names = set([f.name for f in arcpy.ListFields(attribute_parameters)])
        required_attribute_parameter_field_names = set(ATTRIBUTE_PARAMETERS_FIELDS)
        if not required_attribute_parameter_field_names.issubset(attribute_parameters_field_names):
            arcpy.AddIDMessage("ERROR", 30108, "Attribute Parameter Values")
            raise InputError()
        layer_attribute_parameters = na_layer_solver_props.attributeParameters
        with arcpy.da.SearchCursor(attribute_parameters, ATTRIBUTE_PARAMETERS_FIELDS) as cursor:
            for row in cursor:
                attribute_name, attribute_parameter_name, attribute_parameter_value = row
                key = (attribute_name, attribute_parameter_name)
                if layer_attribute_parameters is None or not key in layer_attribute_parameters:
                    #Add the message only if the attribute associated with the attribute parameter
                    #is actually used in the analysis.
                    if attribute_name in analysis_attributes:
                        arcpy.AddIDMessage("WARNING", 30130, attribute_parameter_name, attribute_name)
                    else:
                        if not attribute_name in nds_attributes:
                            arcpy.AddIDMessage("WARNING", 30114, attribute_name, attribute_parameter_name)
                    continue
                if not attribute_parameter_value == None:
                    if attribute_parameter_value.lower() == "none":
                        attribute_parameter_value = ""
                    if attribute_name in analysis_attributes:
                        layer_attribute_parameters[key] = attribute_parameter_value
        if layer_attribute_parameters:
            try:
                na_layer_solver_props.attributeParameters = layer_attribute_parameters
            except ValueError as ex:
                #print_message(str(ex),2)
                #get the attribute name and parameter name for value  that caused error
                msg = ex.args[0]
                start_index = msg.find("[")
                end_index = msg.find("]")
                if start_index != -1 and end_index != -1:
                    key = eval(msg[start_index: end_index + 1])
                    if key:
                        for val in key:
                            arcpy.AddIDMessage("ERROR", 30132, val[1], val[0])
                        raise arcpy.ExecuteError
                    else:
                        print_message(str(ex),2)
                        raise                        
                else:
                    print_message(str(ex),2)
                    raise

def add_locations(na_layer, na_class, locations_obj, impedance_attribute, impedance_units, input_units,
                  search_tolerance, search_query, measurement_method=None, propogate_ids=False, id_field=None,
                  exclude_restricted_elements=True):
    '''Add locations such as barriers or facilities or incidents to the NA layer. if propogate_ids is TRue, id_field should be
    the field object from input locations that should be propogated to sub layer within na layer.'''
    
    locations = locations_obj.catalogPath
    locations_fields_list = locations_obj.describeObject.fields
    na_class_names = arcpy.na.GetNAClassNames(na_layer)
    solver_props = arcpy.na.GetSolverProperties(na_layer)
    
    if na_class == "Barriers":
        #If we have added cost point barriers, convert the AdditionalCost value from break units to 
        #Impedance units. The where clause is to avoid the conversion for restriction barriers.
        if measurement_method:
            cost_field_name = "Additional_Time" if measurement_method == "TRAVEL_TIME" else "Additional_Distance"
        else:
            #For service area we use AdditionalCost field in point barriers
            cost_field_name = "AdditionalCost"
                
        sub_layer_name = na_class_names[na_class]
        field_mappings = arcpy.na.NAClassFieldMappings(na_layer, sub_layer_name, False, locations_fields_list)
        if "BarrierType" in locations_obj.fieldNames:
            if cost_field_name in locations_obj.fieldNames:
                if input_units != impedance_units:
                    where_clause = '"BarrierType" = 2 AND "{0}" > 0'.format(cost_field_name)
                    with arcpy.da.UpdateCursor(locations, cost_field_name, where_clause) as cursor:
                        for row in cursor:
                            new_added_cost = convert_units(row[0],input_units, impedance_units)
                            row[0] = new_added_cost
                            cursor.updateRow(row)
                field_mappings["Attr_" + impedance_attribute].mappedFieldName = cost_field_name
            else:
                field_mappings["Attr_" + impedance_attribute].defaultValue = 0
        else:
            #if BarrierType field does not exists on input features, load them as restriction barriers
            field_mappings["BarrierType"].defaultValue = 0

        arcpy.na.AddLocations(na_layer, sub_layer_name, locations, field_mappings, search_tolerance,
                              search_query=search_query)
    elif na_class == "PolylineBarriers":        
        arcpy.na.AddLocations(na_layer,na_class_names[na_class], locations, "#", search_tolerance,
                              search_query=search_query)
    elif na_class == "PolygonBarriers":
        sub_layer_name = na_class_names[na_class]
        field_mappings = arcpy.na.NAClassFieldMappings(na_layer, sub_layer_name, False, locations_fields_list)
        if measurement_method:
            scaled_cost_factor_field_name = "ScaledTimeFactor" if measurement_method == "TRAVEL_TIME" else "ScaledDistanceFactor"
        else:
            #ScaledCostFactor is used by service area tool.
            scaled_cost_factor_field_name = "ScaledCostFactor"
        field_mappings["Attr_" + impedance_attribute].mappedFieldName = scaled_cost_factor_field_name
        arcpy.na.AddLocations(na_layer, sub_layer_name, locations, field_mappings, search_tolerance,
                              search_query=search_query)
    elif na_class in ("Facilities", "Incidents"):
        #Load CF facilities and incidents.
        #if solver_props.solverName == "Closest Facility Solver":
        sub_layer_name = na_class_names[na_class]
        
        #Add the FacilityOID or IncidentOID field that can be used to transfer objectIDs from
        #input
        oid_field_name = "FacilityOID" if na_class == "Facilities" else "IncidentOID"
        arcpy.na.AddFieldToAnalysisLayer(na_layer, sub_layer_name, oid_field_name, "LONG",
                                         field_alias=oid_field_name)
        #Check if we have an ID field in input.
        #Propogate the ID field if the first row from input has an ID value.
        #we are assuming that if first row has ID, all records have ID.
        if propogate_ids and id_field:
            id_field_name = id_field.name
            #Add the ID field to the analysis sub layer
            #Get the properties for ID field from input feature set
            arcpy.na.AddFieldToAnalysisLayer(na_layer, sub_layer_name, na_class+id_field_name, id_field.type,
                                             field_length=id_field.length)
        #The default field mappings will match Name and CurbApproach fields from input locations to 
        #sub layer
        field_mappings = arcpy.na.NAClassFieldMappings(na_layer, sub_layer_name, False, locations_fields_list)
        #map the objectID field from input as FacilityOID or IncidentOID
        input_oid_field_name = locations_obj.origOIDFieldName
        field_mappings[oid_field_name].mappedFieldName = input_oid_field_name
        if propogate_ids and id_field:
            field_mappings[na_class+id_field_name].mappedFieldName = id_field_name
        #Use AdditionalTime and AdditionalDistance field based on measurement method.
        if measurement_method:
            attr_field_name = "AdditionalTime" if measurement_method == "TRAVEL_TIME" else "AdditionalDistance"            
            if attr_field_name in locations_obj.fieldNames:
                #Convert values from measurement units to impedance units if two units are different
                if input_units != impedance_units:
                    with arcpy.da.UpdateCursor(locations, attr_field_name, "{0} > 0".format(attr_field_name)) as cursor:
                        for row in cursor:
                            new_added_cost = convert_units(row[0],input_units, impedance_units)
                            row[0] = new_added_cost
                            cursor.updateRow(row)
                field_mappings["Attr_" + impedance_attribute].mappedFieldName = attr_field_name
            else:
                field_mappings["Attr_" + impedance_attribute].defaultValue = 0
        arcpy.na.AddLocations(na_layer, sub_layer_name, locations, field_mappings, search_tolerance,
                              exclude_restricted_elements=exclude_restricted_elements, search_query=search_query)            
    return

def find_field(dataset, dataset_fields, field_name):
    '''returns the field object from the dataset if the field exists in the input dataset and if the first
    record in the dataset does not contain Null value for the field.'''
    field = None
    dataset_field_names = [f.name for f in dataset_fields]
    if field_name in dataset_field_names:
        with arcpy.da.SearchCursor(dataset, field_name) as cursor:
            first_row = cursor.next()
            if first_row[0] in (None, ""):
                field = None
            else:
                field = dataset_fields[dataset_field_names.index(field_name)]
    return field

def update_field_map_output_field(field_mappings, field_name, field_updates):
    '''Makes changes to the output field of a field map object within a field mappings object'''
    
    field_map_index = field_mappings.findFieldMapIndex(field_name)
    #continue only if the field exists.
    if field_map_index != -1:
        field_map = field_mappings.getFieldMap(field_map_index)
        output_field = field_map.outputField
        for prop in field_updates:
            setattr(output_field, prop, field_updates[prop])
        field_map.outputField = output_field
        field_mappings.replaceFieldMap(field_map_index, field_map)
    return

class InputDataset(object):
    '''Represents the copy of a feature class. It contains all the properties that are commonly
    used from a feature class such as describe object and count of features.'''
    
    def __init__(self, features):
        '''Can be instantiated with any value that works as features in arcpy such as layers,
        catalog paths to feature classes and feature sets.'''
        self.count = long(arcpy.management.GetCount(features).getOutput(0))
        self.describeObject = arcpy.Describe(features)
        self.inputFeatures = features
        self.isCopy = False
    
    @property
    def fieldNames(self):
        '''Read only property that returns the list of field names'''
        return [f.name for f in self.describeObject.fields]
    
    @property
    def catalogPath(self):
        '''Read only property that returns the catalog path of the feature class'''
        return self.describeObject.catalogPath
    
    @property
    def origOIDFieldName(self):
        '''Read only property that returns the original oid field name. This is OID field name 
        if features are not copied yet'''
        return "ORIG_FID" if self.isCopy else self.describeObject.oidFieldName
    
        
        
    
    def __copyFeatures(self, out_workspace, output_fields=None, data_type="FEATURE_CLASS"):
        '''Copies inputs to a new feature class preserving the objectids and output_fields if present
        on the input. This is used to make a copy of the input feature sets before modifying them.
        output_fields is a list of field names. If output_fields is None only OID and Shape field from
        inputs is preserved as "ORIG_FID". output_fields should NOT contain shape field.
        data_type can be 'FEATURE_CLASS or TABLE and determines if copy is made as feature class or
        table'''
        
        if self.count == 0:
            self.isCopy = False
            return
        
        copy_functions = {"FEATURE_CLASS" : arcpy.conversion.FeatureClassToFeatureClass,
                         "TABLE" : arcpy.conversion.TableToTable}
        if data_type in copy_functions:
            copy_function = copy_functions[data_type]
        else:
            raise arcpy.ExecuteError("unsupported data type {0} for copying inputs".format(data_type))
        input_oid_field_name = self.describeObject.oidFieldName
        #Convert input field names to upper case to perform a case insensitive exists check
        input_field_names = [f.upper() for f in self.fieldNames]
        
        #Create a unique name for the inputs in the out_workspace
        unique_name = "TempInput"            
        output_feature_class = arcpy.CreateUniqueName(unique_name, out_workspace)
        output_feature_class_name = os.path.basename(output_feature_class)
        
        #Create a field mappings to only transfer output_fields present on input_features
        field_mappings = arcpy.FieldMappings()
        #Transfer the OID field from input as ORIG_ID
        if self.describeObject.hasOID:
            oid_field_map = arcpy.FieldMap()
            try:
                oid_field_map.addInputField(self.inputFeatures, input_oid_field_name)
            except Exception as ex:
                oid_field_map.addInputField(self.describeObject.catalogPath, input_oid_field_name)
            output_fld = oid_field_map.outputField
            output_fld.name = "ORIG_FID"
            output_fld.aliasName = "ORIG_FID"
            oid_field_map.outputField = output_fld
            field_mappings.addFieldMap(oid_field_map)        
            
        for fld in output_fields:
            #Skip if field with name SHAPE exists as copy will copy shape field.
            ucase_fld_name = fld.upper()
            if ucase_fld_name == "SHAPE":
                continue
            if ucase_fld_name in input_field_names:
                field_map = arcpy.FieldMap()
                try:
                    field_map.addInputField(self.inputFeatures,fld)
                except Exception as ex:
                    field_map.addInputField(self.describeObject.catalogPath, fld)
                field_mappings.addFieldMap(field_map)
        
        #Make sure we don't use arcpy.env.extent or arcpy.env.outputCoordinateSystem when making
        #a copy as we want all features from inputs and in same spatial reference.
        orig_extent = arcpy.env.extent
        orig_outsr = arcpy.env.outputCoordinateSystem
        arcpy.env.extent = None
        arcpy.env.outputCoordinateSystem = None
        try:
            copy_function(self.inputFeatures, out_workspace, output_feature_class_name,
                          field_mapping=field_mappings)
        finally:
            arcpy.env.extent = orig_extent
            arcpy.env.outputCoordinateSystem = orig_outsr            
        #Update the describe object
        self.isCopy = True
        self.describeObject = arcpy.Describe(output_feature_class)
    
    def deleteCopy(self):
        '''Deletes the copy of the input features'''
        
        if self.isCopy and arcpy.Exists(self.catalogPath):
            try:
                arcpy.management.Delete(self.catalogPath)
            except Exception as ex:
                arcpy.AddIDMessage("WARNING", 30133, self.catalogPath)

class InputFeatureClass(InputDataset):
    '''Represents the copy of input as a feature class. '''
    
    def copyFeatures(self, out_workspace, output_fields=None):
        self._InputDataset__copyFeatures(out_workspace, output_fields, "FEATURE_CLASS")

class InputTable(InputDataset):
    '''Represents the copy of input as table. '''
    
    def copyFeatures(self, out_workspace, output_fields=None):
        self._InputDataset__copyFeatures(out_workspace, output_fields, "TABLE")
        

def get_unique_field_name(base_name, field_names):
    '''Returns a unique field name based on the base_name that does not exists in field_names.
    field_names is a list of field names. if base_name already exists a unique name is generated
    by appending a number after base_name such base_name_1 and so on until it is unique.'''
    
    if not base_name in field_names:
        return base_name
    for i in range(0, len(field_names)):
        fld_name = "{0}_{1}".format(base_name, i+1)
        if fld_name in field_names:
            continue
        else:
            break
    return fld_name

def check_valid_table_name(table_name, out_workspace, error_code, add_argument1=None, add_argument2=None):
    '''Check if the table name is valid for the output workspace and fail with an error if the name
    is invalid'''
    
    valid_name = arcpy.ValidateTableName(table_name, out_workspace)
    if valid_name != table_name:
        arcpy.AddIDMessage("ERROR", error_code, add_argument1, add_argument2)
        raise arcpy.ExecuteError