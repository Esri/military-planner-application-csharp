import arcpy
import numpy
import math

def AddGeometryAttributes(fc, geomProperties, lUnit, aUnit, cs):
    """-------------------------------------------------------------------------
    Tool:               Add Geometry Attributes (Data Management Tools)
    Source Name:        AddGeometryAttributes.py
    Version:            ArcGIS 10.2.1
    Author:             Esri, Inc.
    Usage:              arcpy.AddGeometryAttributes_management(
                                                  Input_Features,
                                                  Geometry_Properties,
                                                  {Length_Unit},
                                                  {Area_Unit},
                                                  {Coordinate_System})
    Required Arguments: Input Features
                        Geometry Properties
    Optional Arguments: Length Unit
                        Area Unit
                        Coordinate System
    Description:        Adds attribute fields to the input features containing
                        measurements and coordinate properties of the feature
                        geometries (for example, length or area).
    Updated:            Not yet.
    ------------------------------------------------------------------------"""

    desc = arcpy.Describe(fc)
    hasZ, hasM = desc.hasZ, desc.hasM
    if cs:
        sr = arcpy.SpatialReference()
        sr.loadFromString(cs)
        try:
            srMetersPerUnit = sr.metersPerUnit
        except:
            srMetersPerUnit = 1
    else:
        try:
            srMetersPerUnit = desc.spatialReference.metersPerUnit
        except:
            srMetersPerUnit = 1
    shapeDict = {"POINT":1,
                 "MULTIPOINT":1.5,
                 "POLYLINE":2,
                 "POLYGON":3,}
    shapeDim = shapeDict[str(desc.shapeType).upper()]
    del desc

    fields = CreateOutputFields(fc, geomProperties, hasZ, hasM)

    arcpy.SetProgressor("STEP", arcpy.GetIDMessage(86174), 0,
                        int(arcpy.GetCount_management(fc).getOutput(0)), 1)

    hasNulls = False
    # Calculate geometry properties into new fields
    with arcpy.da.UpdateCursor(fc,fields + ["SHAPE@"],"",cs) as ucur:
        for row in ucur:
            geom = row[len(fields)]
            if geom:
                if shapeDim == 1:
                    if "POINT_X_Y_Z_M" in geomProperties:
                        row[fields.index("POINT_X")] = geom.firstPoint.X
                        row[fields.index("POINT_Y")] = geom.firstPoint.Y
                        if hasZ:
                            row[fields.index("POINT_Z")] = geom.firstPoint.Z
                        if hasM:
                            row[fields.index("POINT_M")] = geom.firstPoint.M
                if shapeDim>1:
                    if "PART_COUNT" in geomProperties:
                        row[fields.index("PART_COUNT")] = geom.partCount
                    if "CENTROID" in geomProperties:
                        row[fields.index("CENTROID_X")] = geom.trueCentroid.X
                        row[fields.index("CENTROID_Y")] = geom.trueCentroid.Y
                        if hasZ:
                            row[fields.index("CENTROID_Z")]= geom.trueCentroid.Z
                        if hasM:
                            row[fields.index("CENTROID_M")]= geom.trueCentroid.M
                    if "EXTENT" in geomProperties:
                        row[fields.index("EXT_MIN_X")] = geom.extent.XMin
                        row[fields.index("EXT_MIN_Y")] = geom.extent.YMin
                        row[fields.index("EXT_MAX_X")] = geom.extent.XMax
                        row[fields.index("EXT_MAX_Y")] = geom.extent.YMax
                if shapeDim>=2:
                    if "POINT_COUNT" in geomProperties:
                        row[fields.index("PNT_COUNT")] = geom.pointCount
                    if "LINE_START_MID_END" in geomProperties:
                        row[fields.index("START_X")] = geom.firstPoint.X
                        row[fields.index("START_Y")] = geom.firstPoint.Y
                        if shapeDim ==2:
                            midPoint = geom.positionAlongLine(0.5,
                                                                True).firstPoint
                        else:
                            line = arcpy.Polyline(geom.getPart(0), "#",
                                                                     hasZ, hasM)
                            if line.length > 0:
                                midPoint = line.positionAlongLine(0.5,
                                                                True).firstPoint
                            else:
                                hasNulls = True
                            del line
                        row[fields.index("MID_X")] = midPoint.X
                        row[fields.index("MID_Y")] = midPoint.Y
                        row[fields.index("END_X")] = geom.lastPoint.X
                        row[fields.index("END_Y")] = geom.lastPoint.Y
                        if hasZ:
                            row[fields.index("START_Z")] = geom.firstPoint.Z
                            row[fields.index("MID_Z")] = midPoint.Z
                            row[fields.index("END_Z")] = geom.lastPoint.Z
                        if hasM:
                            row[fields.index("START_M")] = geom.firstPoint.M
                            row[fields.index("MID_M")] = midPoint.M
                            row[fields.index("END_M")] = geom.lastPoint.M
                        del midPoint
                    if "CENTROID_INSIDE" in geomProperties:
                        row[fields.index("INSIDE_X")] = geom.centroid.X
                        row[fields.index("INSIDE_Y")] = geom.centroid.Y
                        if hasZ:
                            row[fields.index("INSIDE_Z")] = geom.centroid.Z
                        if hasM:
                            row[fields.index("INSIDE_M")] = geom.centroid.M
                if shapeDim==2:
                    if "LINE_BEARING" in geomProperties:
                        lat1 = geom.firstPoint.Y
                        lon1 = geom.firstPoint.X
                        lat2 = geom.lastPoint.Y
                        lon2 = geom.lastPoint.X
                        row[fields.index("BEARING")] = (90 -
                           math.degrees(math.atan2(lat2-lat1, lon2-lon1))) % 360
                        del lat1, lon1, lat2, lon2
                    if "LENGTH" in geomProperties:
                        row[fields.index("LENGTH")] = ConvertFromMeters(
                                                                "LINEAR",
                                                                geom.length,
                                                                lUnit,
                                                                srMetersPerUnit)
                    if "LENGTH_3D" in geomProperties:
                        row[fields.index("LENGTH_3D")] = ConvertFromMeters(
                                                                "LINEAR",
                                                                geom.length3D,
                                                                lUnit,
                                                                srMetersPerUnit)
                    if "LENGTH_GEODESIC" in geomProperties:
                        row[fields.index("LENGTH_GEO")] =  ConvertFromMeters(
                                               "LINEAR",
                                               geom.getLength("PRESERVE_SHAPE"),
                                               lUnit,
                                               srMetersPerUnit)
                if shapeDim==3:
                    if "PERIMETER_LENGTH" in geomProperties:
                        row[fields.index("PERIMETER")] = ConvertFromMeters(
                                                                "LINEAR",
                                                                geom.length,
                                                                lUnit,
                                                                srMetersPerUnit)
                    if "AREA" in geomProperties:
                        row[fields.index("POLY_AREA")] = ConvertFromMeters(
                                                                "AREA",
                                                                geom.area,
                                                                aUnit,
                                                                srMetersPerUnit)
                    if "AREA_GEODESIC" in geomProperties:
                        row[fields.index("AREA_GEO")] = ConvertFromMeters(
                                                 "AREA",
                                                 geom.getArea("PRESERVE_SHAPE"),
                                                 aUnit,
                                                 srMetersPerUnit)
                    if "PERIMETER_LENGTH_GEODESIC" in geomProperties:
                        row[fields.index("PERIM_GEO")] = ConvertFromMeters(
                                               "LINEAR",
                                               geom.getLength("PRESERVE_SHAPE"),
                                               lUnit,
                                               srMetersPerUnit)
                ucur.updateRow(row)
            else:
                hasNulls = True
            arcpy.SetProgressorPosition()
    if hasNulls:
        arcpy.AddIDMessage("WARNING", 957)

def CreateOutputFields(fc, geomProperties, hasZ, hasM):
    propDict = {"POINT_X_Y_Z_M":            ["POINT_X",
                                             "POINT_Y",
                                             "POINT_Z",
                                             "POINT_M"],
                "PART_COUNT":               ["PART_COUNT"],
                "CENTROID":                 ["CENTROID_X",
                                             "CENTROID_Y",
                                             "CENTROID_Z",
                                             "CENTROID_M"],
                "EXTENT":                   ["EXT_MIN_X",
                                             "EXT_MIN_Y",
                                             "EXT_MAX_X",
                                             "EXT_MAX_Y"],
                "POINT_COUNT":              ["PNT_COUNT"],
                "LINE_START_MID_END":       ["START_X",
                                             "START_Y",
                                             "START_Z",
                                             "START_M",
                                             "MID_X",
                                             "MID_Y",
                                             "MID_Z",
                                             "MID_M",
                                             "END_X",
                                             "END_Y",
                                             "END_Z",
                                             "END_M"],
                "LINE_BEARING":             ["BEARING"],
                "CENTROID_INSIDE":          ["INSIDE_X",
                                             "INSIDE_Y",
                                             "INSIDE_Z",
                                             "INSIDE_M"],
                "LENGTH":                   ["LENGTH"],
                "PERIMETER_LENGTH":         ["PERIMETER"],
                "AREA":                     ["POLY_AREA"],
                "LENGTH_GEODESIC":          ["LENGTH_GEO"],
                "AREA_GEODESIC":            ["AREA_GEO"],
                "LENGTH_3D":                ["LENGTH_3D"],
                "PERIMETER_LENGTH_GEODESIC":["PERIM_GEO"],
                }
    if not hasZ:
        propDict["POINT_X_Y_Z_M"].remove("POINT_Z")
        propDict["CENTROID"].remove("CENTROID_Z")
        propDict["CENTROID_INSIDE"].remove("INSIDE_Z")
        propDict["LINE_START_MID_END"].remove("START_Z")
        propDict["LINE_START_MID_END"].remove("MID_Z")
        propDict["LINE_START_MID_END"].remove("END_Z")
    if not hasM:
        propDict["POINT_X_Y_Z_M"].remove("POINT_M")
        propDict["CENTROID"].remove("CENTROID_M")
        propDict["CENTROID_INSIDE"].remove("INSIDE_M")
        propDict["LINE_START_MID_END"].remove("START_M")
        propDict["LINE_START_MID_END"].remove("MID_M")
        propDict["LINE_START_MID_END"].remove("END_M")

    addList = []
    geomPropertiesList = []
    currentFields = [field.name for field in arcpy.ListFields(fc)]
    for prop in geomProperties:
        for field in propDict[prop.upper()]:
            geomPropertiesList.append(field)
            if field not in currentFields:
                addList.append(field)
            else:
                arcpy.AddIDMessage("WARNING", 1097, field)

    if addList:
        narray = numpy.array([], numpy.dtype([("_ID", numpy.int)] +
                                           [(n, numpy.float) for n in addList]))
        arcpy.da.ExtendTable(fc, "OID@", narray, "_ID")

    return geomPropertiesList

def ConvertFromMeters(type, value, unit, metersPerUnit):
    if not unit:
        return value
    else:
        distanceUnitInfo = {"METERS": 1.0,
                            "FEET_US": 0.304800609601219,
                            "NAUTICAL_MILES": 1852.0,
                            "MILES_US": 1609.34721869444,
                            "KILOMETERS": 1000.0,
                            "YARDS": 0.914401828803658,}

        areaUnitInfo =     {"ACRES": 4046.86,
                            "HECTARES": 10000.0,
                            "SQUARE_METERS": 1.0,
                            "SQUARE_FEET_US": 0.09290341161327473,
                            "SQUARE_NAUTICAL_MILES": 3429904.0,
                            "SQUARE_MILES_US": 2589998.4703195295,
                            "SQUARE_KILOMETERS": 1000000.0,
                            "SQUARE_YARDS": 0.8361307045194741,}
        if type == "LINEAR":
            return (value*metersPerUnit)/distanceUnitInfo[unit]
        if type == "AREA":
            return (value*math.pow(metersPerUnit,2))/areaUnitInfo[unit]

#run the script
if __name__ == '__main__':
    # Get Parameters
    fc = arcpy.GetParameterAsText(0)
    if arcpy.GetParameterAsText(1).find(";") > -1:
         geomProperties = arcpy.GetParameterAsText(1).upper().split(";")
    else:
         geomProperties = [arcpy.GetParameterAsText(1).upper()]
    lUnit = arcpy.GetParameterAsText(2)
    aUnit = arcpy.GetParameterAsText(3)
    cs = arcpy.GetParameterAsText(4)
    if not cs:
        cs = arcpy.env.outputCoordinateSystem

    # Run the main script
    AddGeometryAttributes(fc, geomProperties, lUnit, aUnit, cs)