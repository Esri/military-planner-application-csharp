##------------------------------------------------------------------------
##Tool Name: Transpose Time Fields
##Source Name: Transpose.py
##Author: Environmental Systems Research Institute, Inc.
##
##Required Arguments: An input feature class or table 
##                    A set of fields to transpose
##                    An output feature class or table
##                    A time field name
##                    A value field name
##Optional Arguments: A set of attribute fields from the input to be 
##                    included in the output
##
##Description: This tool shifts fields that have time as a field name 
##             and their values from columns to rows in a table or 
##             feature class. When a table or feature class is transposed, 
##             each row will be repeated multiple times depending on
##             how many fields you are transposing, and each repeated 
##             row has a different time stamp. 
##------------------------------------------------------------------------

import arcgisscripting, os, sys, math, string
gp = arcgisscripting.create(9.3)

try:
    inTable = gp.GetParameterAsText(0) 
    inFields = gp.GetParameterAsText(1) 
    outTable = gp.GetParameterAsText(2) 
    outTimeField = gp.GetParameterAsText(3) 
    outValueField = gp.GetParameterAsText(4)
    attrFields = gp.GetParameterAsText(5)
    
    #split inFields & outTable
    inFields = inFields.split(";")
    attrFields = attrFields.split(";")
    outPath, outName = os.path.split(outTable)

    #verify input field names
    #Message "Verifying input fields..."
    gp.AddMessage(gp.GetIDMessage(86177))
    verifiedSuccess = 1
    fieldCount = 0
    for eachQuotedFieldPair in inFields:
        fieldCount = fieldCount + 1
        fieldPairRaw = eachQuotedFieldPair.split("'")
        fieldPair = fieldPairRaw[1]
        fieldPair = fieldPair.rsplit()
        namePart = fieldPair[0]
        inFieldList = gp.ListFields(inTable, "*", "all")
        #aField = inFieldList.Next()
        flagFieldExist = 0
        for aField in inFieldList:
            if aField.Name == namePart:
                flagFieldExist = 1
                break
            #aField = inFieldList.Next()
        if flagFieldExist == 0:
            verifiedSuccess = 0
            break

    if verifiedSuccess == 0:
        #Message "Input field '" + namePart + "' does not exist in the input feature class or table."
        gp.AddError(gp.GetIDMessage(86178) % namePart)
        raise StandardError, gp.GetMessages(2)

    #create progressor
    #Message "Running transpose time fields..."
    gp.SetProgressor("step",gp.GetIDMessage(86179) , 0, fieldCount * 3 + 1)

    #describe input (feature class or table)
    dscInput = gp.Describe(inTable)

    #create the output table or feature class
    if dscInput.DatasetType == "Table":
        #create a table
        #Message "Creating output table..."
        gp.AddMessage(gp.GetIDMessage(86180))
        gp.CreateTable_management(outPath, outName, inTable)
        dscOutput = gp.describe(outTable)
        must_have_list = [ ]
        must_have_list.append(dscOutput.OIDFieldName.upper())
    elif dscInput.DatasetType == "FeatureClass":
        #create a feature class
        #Message "Creating output feature class..."
        gp.AddMessage(gp.GetIDMessage(86181))
        gp.CreateFeatureClass_management(outPath, outName, dscInput.ShapeType, inTable, "SAME_AS_TEMPLATE", "SAME_AS_TEMPLATE", dscInput.SpatialReference)
        dscOutput = gp.describe(outTable)
        must_have_list = [ ]
        must_have_list.append(dscOutput.OIDFieldName.upper())
        must_have_list.append(dscOutput.ShapeFieldName.upper())
    else:
        #Message "Dataset type not supported. Please input either a table or a feature class."
        gp.AddError(gp.GetIDMessage(86182))
        raise StandardError, gp.GetMessages(2)
    gp.SetProgressorPosition()

    #drop extra fields
    for eachQuotedFieldPair in inFields:
        fieldPairRaw = eachQuotedFieldPair.split("'")
        fieldPair = fieldPairRaw[1]
        fieldPair = fieldPair.rsplit()
        fieldName = fieldPair[0]
        must_have_list.append(fieldName.upper())

    for eachItem in attrFields:
        must_have_list.append(eachItem.upper())
        
    outFieldList = gp.ListFields(outTable, "*", "all")
    #eachField = outFieldList.Next()
    for eachField in outFieldList:
        if eachField.Name.upper() not in must_have_list:
            try:
                gp.DeleteField_management(outTable, eachField.Name)
            except:                
                pass
        #eachField = outFieldList.Next()

    #append records to the output table
    #Message "Appending records..."
    gp.AddMessage(gp.GetIDMessage(86183))
    transCount = 0
    for eachFieldPair in inFields:
        gp.Append_management(inTable, outTable, "NO_TEST")
        transCount = transCount + 1 
        gp.SetProgressorPosition()

    results1 = gp.GetCount_management(inTable)
    results2 = gp.GetCount_management(outTable)
    countInputRows = int(results1.GetOutput(0))
    countOutputRows = int(results2.GetOutput(0))
    if countOutputRows <> countInputRows*transCount:
        #Message "Output rows count incorrect. Failed to append."
        gp.AddError(gp.GetIDMessage(86189))
        gp.ResetProgressor()
        raise StandardError, "Failed to append."
   
    #add two fields - a value field and a time field
    #Message "Adding time field and value field..."
    gp.AddMessage(gp.GetIDMessage(86184))
    quotedPair = inFields[0]
    quotedPair = quotedPair.split("'")
    fieldPair1 = quotedPair[1]
    fieldPair1 = fieldPair1.rsplit()
    namePart = fieldPair1[0]
    inFieldList = gp.ListFields(inTable, "*", "all")
    #aField = inFieldList.Next()
    for aField in inFieldList:
        if aField.Name == namePart:
            valueFieldType = aField.Type
            break
        #aField = inFieldList.Next()
        
    if valueFieldType == "SmallInteger":
        valueFieldType = "short"
    elif valueFieldType == "Integer":
        valueFieldType = "long"
    elif valueFieldType == "Single":
        valueFieldType = "float"
    elif valueFieldType == "String":
        valueFieldType = "text"
    elif valueFieldType == "Double":
        valueFieldType = "double"
    elif valueFieldType == "Date":
        valueFieldType = "date"
    elif valueFieldType == "OID":
        valueFieldType = "long"
    else:
        #Message "Time field type not supported."
        gp.AddError(gp.GetIDMessage(86190))
        raise StandardError, gp.GetMessages(2)
            
    outTimeField = gp.ValidateFieldName(outTimeField, os.path.dirname(outTable))
    gp.AddField_management(outTable, outTimeField, "text", "", "", 20, outTimeField, "", "", "")
    outValueField = gp.ValidateFieldName(outValueField, os.path.dirname(outTable))
    gp.AddField_management(outTable, outValueField, valueFieldType, "", "", "", outValueField, "", "", "")
    
    #Find out the starting value of OID
    srows = gp.SearchCursor(outTable, "", "", "", dscOutput.OIDFieldName + " A")
    srow = srows.Next()
    firstOIDValue = srow.GetValue(dscOutput.OIDFieldName)
    del srows

    dscOutputData = gp.Describe(outTable)
    dscOutputWorkspace = gp.Describe(outPath)

    #Create a table view or feature layer for output
    table_view = "DDBA6F01_3610_42C7_9FE3_DFAA1656B41A"
    if dscOutputData.DatasetType == "Table":
        gp.MakeTableView_management(outTable, table_view)
    elif dscOutputData.DatasetType == "FeatureClass":
        gp.MakeFeatureLayer_management(outTable, table_view)

    #Calculate fields
    #Message "Updating time field and value field..."
    gp.AddMessage(gp.GetIDMessage(86185))
    i = 0
    selectStart = firstOIDValue
    dbExtension = outPath[-4:]
    while i < transCount:
        #Select rows
        selectEnd = selectStart + countInputRows
        if dscOutputWorkspace.WorkspaceType.upper() == "LOCALDATABASE" and dbExtension.upper() == ".MDB":
            queryExpression = "[" + dscOutputData.OIDFieldName + "]" + " >= " + str(selectStart) + " AND " \
                              + "[" + dscOutputData.OIDFieldName + "]" + " < " + str(selectEnd)                
        elif dscOutputWorkspace.WorkspaceType.upper() == "REMOTEDATABASE":
            queryExpression = dscOutputData.OIDFieldName + " >= " + str(selectStart) + " AND " \
                              + dscOutputData.OIDFieldName + " < " + str(selectEnd)
        else:
            queryExpression = '"' + dscOutputData.OIDFieldName + '"' + " >= " + str(selectStart) + " AND " \
                              + '"' + dscOutputData.OIDFieldName + '"' + " < " + str(selectEnd)                       
        gp.SelectLayerByAttribute_management(table_view, "NEW_SELECTION", queryExpression)        
        selectStart = selectStart + countInputRows
        #Verify the number of selected rows
        results3 = gp.GetCount_management(table_view)
        selectedRowsCount = int(results3.GetOutput(0))
        if selectedRowsCount <> countInputRows:
            #Message "Selected rows count incorrect. Failed to SelectLayerByAttribute."
            gp.AddError(gp.GetIDMessage(86186))
            gp.ResetProgressor()
            raise StandardError, gp.GetMessages(2)
        #Calculate time field and value field for the selected rows
        quotedPair = inFields[i]
        quotedPair = quotedPair.split("'")
        fieldPair = quotedPair[1]
        fieldPair = fieldPair.rsplit()
        fieldName = fieldPair[0]
        time = fieldPair[1]
        timeExpression = time
        valueExpression = "[" + fieldName + "]"
        gp.CalculateField_management(table_view, outTimeField, timeExpression, "VB") 
        gp.CalculateField_management(table_view, outValueField, valueExpression, "VB")    
        i = i + 1
        gp.SetProgressorPosition()

    #drop time fields that have been transposed
    #Message"Dropping unuseful fields..."
    gp.AddMessage(gp.GetIDMessage(86191))
    for eachQuotedFieldPair in inFields:
        fieldPairRaw = eachQuotedFieldPair.split("'")
        fieldPair = fieldPairRaw[1]
        fieldPair = fieldPair.rsplit()
        fieldName = fieldPair[0]
        try:
            gp.DeleteField_management(outTable, fieldName)
        except:
            pass
        gp.SetProgressorPosition()
    #Message "%s fields have been transposed successfully..."
    gp.AddMessage(gp.GetIDMessage(86187) % str(transCount))    
    
except:
    #Message "Failed to execute Transpose Time Fields."
    gp.AddError(gp.GetIDMessage(86188))
    gp.ResetProgressor()
