'''----------------------------------------------------------------------------------
 Tool Name:     CreateFeaturesFromTextFile
 Source Name:   CreateFeaturesFromTextFile.py
 Version:       ArcGIS 9.1
 Author:        Environmental Systems Research Institute Inc.
 Required Argumuments:  An Input Text File containing feature coordinates
                        An Input Character designating the decimal separator used in the text file.
                        An output feature class
 Optional Arguments:    A spatial reference can be specified.  This will be the
                        spatial reference of the output fc.
 Description:   Reads a text file with feature coordinates and creates a feature class
                 from the coordinates.
----------------------------------------------------------------------------------'''

import string, os, sys, locale, arcgisscripting
gp = arcgisscripting.create()
gp.overwriteoutput = 1

msgErrorTooFewParams = "Not enough parameters provided."
msgUnknownDataType = " is not a valid datatype. Datatype must be point, multipoint, polyline or polygon."
msgErrorCreatingPoint = "Error creating point %s on feature %s"

# sets all the point properties
def createPoint(point, geometry):
    try:
        point.id = geometry[0]
        point.x = geometry[1]
        point.y = geometry[2]
        # When empty values are written out from pyWriteGeomToTextFile, they come as 1.#QNAN
        # Additionally, the user need not supply these values, so if they aren't in the list don't add them
        if len(geometry) > 3:
            if geometry[3].lower().find("nan") == -1: point.z = geometry[3]
        if len(geometry) > 4:
            if geometry[4].lower().find("nan") == -1: point.m = geometry[4]
        return point
    except:
        raise Exception, msgErrorCreatingPoint


try:
    # get the provided parameters
    inputTxtFile = open(gp.getparameterastext(0))
    fileSepChar = gp.getparameterastext(1)
    outputFC = gp.getparameterastext(2)

    # spatial reference is optional
    outputSR = gp.getparameterastext(3)

    # make sure the text type specified in the text file is valid.
    inDataType = inputTxtFile.readline().strip().lower()
    dataTypes = ["point", "multipoint", "polyline", "polygon"]
    if inDataType.lower() not in dataTypes:
        msgUnknownDataType = "%s%s" % (inDataType, msgUnknownDataType)
        raise Exception, msgUnknownDataType

    # create the new featureclass
    gp.toolbox = "management"
    gp.CreateFeatureclass(os.path.split(outputFC)[0], os.path.split(outputFC)[1], inDataType, "#", "ENABLED", "ENABLED", outputSR)
    # create a new field to assure the id of each feature is preserved.
    idfield = "File_ID"
    gp.addfield(outputFC, idfield, "LONG")
    # get some information about the new featureclass for later use.
    outDesc = gp.describe(outputFC)
    shapefield = outDesc.ShapeFieldName
    # create the cursor and objects necessary for the geometry creation
    rows = gp.insertcursor(outputFC)
    pnt = gp.createobject("point")
    pntarray = gp.createobject("Array")
    partarray = gp.createobject("Array")
    
    locale.setlocale(locale.LC_ALL, '')
    sepchar = locale.localeconv()['decimal_point']
    
    # loop through the text file.
    featid = 0
    lineno = 1
    for line in inputTxtFile.readlines():
        lineno += 1
        # create an array from each line in the input text file
        values = line.replace("\n", "").replace("\r", "").replace(fileSepChar, sepchar).split(" ")

        # for a point feature class simply populate a point object and insert it. 
        if inDataType == "point" and values[0].lower() != "end":
            row = rows.newrow()
            pnt = createPoint(pnt, values)
            row.SetValue(shapefield, pnt)
            row.SetValue(idfield, int(values[0]))
            rows.insertrow(row)

        # for a multipoint the text file is organized a bit differently.  Groups of points must be inserted at the same time.
        elif inDataType == "multipoint":
            if len(values) > 2:
                pnt = createPoint(pnt, values)
                pntarray.add(pnt)
            elif (len(values) == 2 and lineno != 2) or values[0].lower() == "end":
                row = rows.newrow()
                row.SetValue(shapefield, pntarray)
                # store the feature id just in case there is an error. helps track down the offending line in the input text file.
                if values[0].lower() != "end":
                    row.SetValue(idfield, featid)
                    featid = int(values[0])
                else:
                    row.SetValue(idfield, featid)
                rows.insertrow(row)
                pntarray.removeall()
            elif (len(values) == 2 and lineno == 2):
                featid = int(values[0])

        # for polygons and lines.  polygons have a bit of logic for interior rings (donuts).
        # lines use the same logic as polygons (except for the interior rings)
        elif inDataType == "polygon" or inDataType == "polyline":
            #takes care of 
            #adds the point array to the part array and then part array to the feature
            if (len(values) == 2 and float(values[1]) == 0 and lineno != 2) or values[0].lower() == "end":
                partarray.add(pntarray)
                row = rows.newrow()
                row.SetValue(shapefield, partarray)
                # store the feature id just in case there is an error. helps track down the offending line in the input text file.
                if values[0].lower() != "end":
                    row.SetValue(idfield, featid)
                    featid = int(values[0])
                else:
                    row.SetValue(idfield, featid)
                rows.insertrow(row)
                partarray.removeall()
                pntarray.removeall()
            #adds parts and/or interior rings to the part array
            elif (len(values) == 2 and float(values[1]) > 0) or values[0].lower() == "interiorring":
                partarray.add(pntarray)
                pntarray.removeall()
            #add points to the point array
            elif len(values) > 2:
                pnt = createPoint(pnt, values)
                pntarray.add(pnt)
            elif (len(values) == 2 and lineno == 2):
                featid = int(values[0])

    inputTxtFile.close()
    del rows
    del row
    
except Exception, ErrorDesc:
    # handle the errors here. if the point creation fails, want to keep track of which point failed (easier to fix the
    # text file if we do)
    if ErrorDesc[0] == msgErrorCreatingPoint:
        if inDataType.lower() == "point":
            msgErrorCreatingPoint = msgErrorCreatingPoint % (values[0], values[0])
        else:
            msgErrorCreatingPoint = msgErrorCreatingPoint % (values[0], featid)
        gp.AddError(msgErrorCreatingPoint)
    elif ErrorDesc[0] != "":
        gp.AddError(str(ErrorDesc))

    gp.AddError(gp.getmessages(2))

    # make sure to close up the fileinput no matter what.
    if inputTxtFile: inputTxtFile.close()
