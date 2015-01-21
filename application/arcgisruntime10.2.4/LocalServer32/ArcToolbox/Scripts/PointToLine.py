import arcpy
import os
import types

def convertPoints():
    arcpy.env.overwriteOutput = True

    # Input point FC
    # Output FC
    # Feature Field
    # Sort Field
    # Close Line or Leave Open
    inPts       = arcpy.GetParameterAsText(0)
    outFeatures = arcpy.GetParameterAsText(1)
    IDField     = arcpy.GetParameterAsText(2)
    sortField   = arcpy.GetParameterAsText(3)
    closeLine   = arcpy.GetParameterAsText(4)

    if IDField in ["", "#"]: IDField = None

    if sortField in ["", "#"]:
        cursorSort = IDField
    else:
        if IDField:
            cursorSort = IDField + ";" + sortField
        else:
            cursorSort = sortField

    if not isinstance(closeLine, types.BooleanType):
        if closeLine.lower() == "false":
            close = False
        else:
            close = True

    convertPointsToLine(inPts, outFeatures, IDField, cursorSort, close)

def getZM(propType, hasMZ):
    envValue = getattr(arcpy.env, propType).upper()

    if envValue in ['ENABLED', 'DISABLED']:
        return envValue
    else:
        if hasMZ:
            return "ENABLED"
        else:
            return "DISABLED"

def convertPointsToLine(inPts, outFeatures, IDField, cursorSort, close):
    try:
        # Assign empty values to cursor and row objects
        iCur, sRow, feat = None, None, None

        desc = arcpy.Describe(inPts)
        shapeName = desc.shapeFieldName

        # Create the output feature class
        #
        outPath, outFC = os.path.split(outFeatures)
        arcpy.CreateFeatureclass_management(outPath, outFC, "POLYLINE", "",
                                            getZM("outputMFlag", desc.hasM),
                                            getZM("outputZFlag", desc.hasZ),
                                            inPts)

        # If there is an IDField, add the equivalent to the output
        #
        if IDField:
            f = arcpy.ListFields(inPts, IDField)[0]
            fName = arcpy.ValidateFieldName(f.name, outPath)
            arcpy.AddField_management(outFeatures, fName, f.type, f.precision, f.scale, f.length,
                                      f.aliasName, f.isNullable, f.required, f.domain)

        # Open an insert cursor for the new feature class
        #
        iCur = arcpy.InsertCursor(outFeatures)

        # Create an array needed to create features
        #
        array = arcpy.Array()

        # Initialize a variable for keeping track of a feature's ID.
        #
        ID = -1
        fields = shapeName
        if cursorSort:
            fields += ";" + cursorSort

        for sRow in arcpy.gp.SearchCursor(inPts, "", None, fields, cursorSort, arcpy.env.extent):
            pt = sRow.getValue(shapeName).getPart(0)
            if IDField:
                currentValue = sRow.getValue(IDField)
            else:
                currentValue = None

            if ID == -1:
                ID = currentValue

            if ID <> currentValue:
                if array.count >= 2:

                    # To close, add first point to the end
                    #
                    if close:
                        array.add(array.getObject(0))

                    feat = iCur.newRow()
                    if IDField:
                        if ID: #in case the value is None/Null
                            feat.setValue(IDField, ID)
                    feat.setValue(shapeName, array)
                    iCur.insertRow(feat)
                else:
                    arcpy.AddIDMessage("WARNING", 1059, unicode(ID))

                array.removeAll()

            array.add(pt)
            ID = currentValue

        # Add the last feature
        #
        if array.count > 1:
            # To close, add first point to the end
            #
            if close:
                array.add(array.getObject(0))

            feat = iCur.newRow()
            if IDField:
                if ID: #in case the value is None/Null
                    feat.setValue(IDField, currentValue)
            feat.setValue(shapeName, array)
            iCur.insertRow(feat)
        else:
            arcpy.AddIDMessage("WARNING", 1059, unicode(ID))
        array.removeAll()

    except Exception as err:
        import traceback
        arcpy.AddError(
            traceback.format_exception_only(type(err), err)[0].rstrip())

    finally:
        if iCur:
            del iCur
        if sRow:
            del sRow
        if feat:
            del feat

        try:
            # Update the spatial index(es)
            #
            r = arcpy.CalculateDefaultGridIndex_management(outFeatures)
            arcpy.AddSpatialIndex_management(outFeatures, r.getOutput(0), r.getOutput(1), r.getOutput(2))
        except:
            pass

if __name__ == '__main__':
    convertPoints()

