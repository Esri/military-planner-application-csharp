'''----------------------------------------------------------------------------------
 Tool Name:   Multiple Ring Buffer
 Source Name: MultiRingBuffer.py
 Version:     ArcGIS 10.0
 Author:      Environmental Systems Research Institute Inc.
 Required Arguments:
              An input feature class or feature layer
              An output feature class
              A set of distances (multiple set of double values)
 Optional Arguments:
              The name of the field to contain the distance values (default="distance")
              Option to have the output dissolved (default="ALL")
 Description: Creates a set of buffers for the set of input features. The buffers
              are defined using a set of variable distances. The resulting feature
              class has the merged buffer polygons with or without overlapping
              polygons maintained as seperate features.
----------------------------------------------------------------------------------'''

import arcgisscripting
import os
import sys
import types
import locale

gp = arcgisscripting.create(9.3)

#Define message constants so they may be translated easily
msgBuffRings  = gp.GetIDMessage(86149) #"Buffering distance "
msgMergeRings = gp.GetIDMessage(86150) #"Merging rings..."
msgDissolve   = gp.GetIDMessage(86151) #"Dissolving overlapping boundaries..."

def initiateMultiBuffer():


    # Get the input argument values
    # Input FC
    input           = gp.GetParameterAsText(0)
    # Output FC
    output          = gp.GetParameterAsText(1)
    # Distances
    distances       = gp.GetParameter(2)
    # Unit
    unit            = gp.GetParameterAsText(3)
    if unit.lower() == "default":
        unit = ""
    # If no field name is specified, use the name "distance" by default
    fieldName       = checkFieldName(gp, gp.GetParameterAsText(4), os.path.dirname(output))
    #Dissolve option
    dissolveOption  = gp.GetParameterAsText(5)
    # Outside Polygons
    outsidePolygons = gp.GetParameterAsText(6)
    if outsidePolygons.lower() == "true":
        sideType = "OUTSIDE_ONLY"
    else:
        sideType = ""

    createMultiBuffers(gp, input, output, distances, unit, fieldName, dissolveOption, sideType)


def checkFieldName(gp, fieldName, workspace):
    if fieldName == "#" or fieldName == '':
        return "distance"
    else:
        outName = gp.ValidateFieldName(fieldName, workspace)
        outName = outName.replace(" ", "_")
        if outName != fieldName:
            gp.AddIDMessage("WARNING", 648, outName)
        return outName

def convertValueTableToList(valTable):
    outList=[]
    for v in valTable.exporttostring().split(";"):
       outList.append(locale.atof(str(v)))
    return outList

def lowerLicenseUnion(gp, fcList):
    unionFC = None
    tmpFC = gp.Union_analysis(fcList[0:2],
                              gp.CreateUniqueName("union", scratchWks)).getOutput(0)
    for fc in fcList[2:]:
        if unionFC:
            tmpFC = unionFC
        unionFC = gp.Union_analysis([tmpFC, fc],
                                    gp.CreateUniqueName("union", scratchWks)).getOutput(0)
    return unionFC


def createMultiBuffers(gp, input, output, distances, unit, fieldName, dissolveOption, sideType):
    try:
        global scratchWks
        # Assign empty values to aid with cleanup at the end
        #
        oldOW = None

        # Keep track of current settings that should be restored by end
        if not gp.overwriteOutput:
            oldOW = True
            gp.overwriteOutput = True

        scratchWks = gp.scratchGDB

        # Convert the distances into a Python list for ease of use
        distList = convertValueTableToList(distances)

        # Loop through each distance creating a new layer and then buffering the input.
        #  Set the step progressor if there are > 1 rings
        if len(distList) > 1:
            gp.SetProgressor("step", "", 0, len(distList))
            stepProg = True
        else:
            gp.SetProgressor("default")
            stepProg = False

        bufferedList = []

        # Buffer the input for each buffer distance.  If the fieldName is different than
        #  the default, add a new field and calculate the proper value
        for dist in distList:
            if stepProg:
                gp.SetProgressorPosition()
            gp.SetProgressorLabel(msgBuffRings + str(dist) + "...")
            bufDistance = "%s %s" % (dist, unit)
            bufOutput = gp.Buffer_analysis(input, gp.CreateUniqueName("buffer", scratchWks),
                                           bufDistance, sideType, "", dissolveOption).getOutput(0)
            if fieldName.lower() != "buff_dist":
                gp.AddField_management(bufOutput, fieldName, "double")
                gp.CalculateField_management(bufOutput, fieldName, dist, "PYTHON")
            bufferedList.append(bufOutput)

        gp.ResetProgressor()
        gp.SetProgressor("default")
        gp.SetProgressorLabel(msgMergeRings)

        if dissolveOption == "ALL":
            # Set up the expression and codeblock variables for CalculateField to ensure
            #  the distance field is populated properly
            expression = "pullDistance(" + str(distList) + ", "
            for fc in bufferedList:
                expression += "!FID_" + os.path.basename(fc) +  "!, "
            expression = expression[:-2] + ")"

            # If we have a full license then Union all feature classes at once, otherwise
            #  Union the feature classes 2 at a time
            if gp.ProductInfo().upper() in ["ARCINFO", "ARCSERVER"] or len(bufferedList) < 3:
                unionFC = gp.Union_analysis(bufferedList,
                                            gp.CreateUniqueName("union", scratchWks)).getOutput(0)
                codeblock = '''def pullDistance(distL, *fids):
                return min([i for i, j in zip(distL, fids) if j != -1])'''
            else:
                unionFC = lowerLicenseUnion(gp, bufferedList)
                codeblock = '''def pullDistance(distL, *fids):
                return min([i for i, j in zip(distL, fids) if j == 1])'''

            gp.CalculateField_management(unionFC, fieldName, expression, "PYTHON", codeblock)

            # Complete the final Dissolve
            gp.SetProgressorLabel(msgDissolve)
            if dissolveOption.upper() == "ALL":
                gp.Dissolve_management(unionFC, output, fieldName)
        else:
            # Reverse the order of the inputs so the features are appended from
            #  largest to smallest buffer features.
            bufferedList.reverse()
            template = bufferedList[0]
            if gp.OutputCoordinateSystem:
                sr = gp.OutputCoordinateSystem
            else:
                sr = gp.Describe(template).spatialreference
            gp.CreateFeatureclass_management(os.path.dirname(output), os.path.basename(output),
                                             "POLYGON", template, "SAME_AS_TEMPLATE", "SAME_AS_TEMPLATE", sr)
            for fc in bufferedList:
                gp.Append_management(fc, output, "NO_TEST")

            if gp.ListFields(output, "buff_dist"):
                # Remove duplicate field
                gp.DeleteField_management(output, "buff_dist")

        # Set the default symbology
        params = gp.GetParameterInfo()
        if len(params) > 0:
            params[1].symbology = os.path.join(gp.GetInstallInfo()['InstallDir'],
                                               "arctoolbox\\templates\\layers\\multipleringbuffer.lyr")

    except arcgisscripting.ExecuteError:
        gp.AddError(gp.GetMessages(2))

    except Exception as err:
        gp.AddError(err.message)

if __name__ == '__main__':
    initiateMultiBuffer()

