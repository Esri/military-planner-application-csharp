##-----------------------------------------------------------------------
##Tool Name: Calculate End Date
##Source Name: CalculateEndDate.py
##Author: Environmental Systems Research Institute Inc.
##
##Required Arguments: An input table
##                    A start date field
##                    An end date field
##
##Description: This tool populates the values for a specified end date 
##             field with values calculated using the start date field 
##             specified. The table is first sorted by entity (the 
##             Unique ID Fields), and then by time stamp. With the 
##             start date field sorted in ascending order, the end date 
##             of any row is the same as the start date of the next row.
##------------------------------------------------------------------------

import arcgisscripting, sys, string
gp = arcgisscripting.create(9.3)

try:

    table = gp.GetParameterAsText(0)
    id_field_string = gp.GetParameterAsText(1)
    start_date_field = gp.GetParameterAsText(2)
    end_date_field = gp.GetParameterAsText(3)
    gp.SetParameterAsText(4, table)
    
    id_field_list = id_field_string.split(";")
    
    #Describe input table and get the oid field name
    dscInTable = gp.Describe(table)
    oid_field = dscInTable.OIDFieldName

    results1 = gp.getcount_management(table)
    row_count = int(results1.GetOutput(0))

    gp.SetProgressor("step", "Running calculate end date...", 0, row_count*2)
    #This variable stores the list of end dates
    end_dates = {}
    
    #Create a value_fields string for the search cursor
    value_fields = ""
    unique_id_fields = ""
    for id_field in id_field_list:
        if (id_field <> "#" and id_field <> ""):
            unique_id_fields = unique_id_fields + id_field + "; "
    value_fields = unique_id_fields + start_date_field + "; " + end_date_field

    #Create a sort_fields string for the search cursor
    sort_fields = ""
    unique_id_fields_sort = ""
    for id_field in id_field_list:
        if (id_field <> "#" and id_field <> ""):
            unique_id_fields_sort = unique_id_fields_sort + id_field + " A; "
    sort_fields = unique_id_fields_sort + start_date_field + " D" 
       
    #Get a search cursor to create a list of end dates
    rows = gp.SearchCursor(table, "", "", value_fields, sort_fields)
    row = rows.Next()

    #Decide the end_date value of the top record
    if (row):
        oid_value = row.GetValue(oid_field)
        date_value_previous = row.GetValue(start_date_field)
        id_value_previous_list = []
        for id_field in id_field_list:
            if (id_field <> "#" and id_field <> ""):
                id_value_previous = row.GetValue(id_field)
            else:
                id_value_previous = ""
            id_value_previous_list.append(id_value_previous)            
        end_dates[oid_value] = date_value_previous     
        row = rows.Next()
        gp.SetProgressorPosition()
        
    #Pass 1, get the end-dates values, and populate them in end_dates
    while row:
        oid_value = row.GetValue(oid_field)
        id_value_list = []        
        for id_field in id_field_list:
            if (id_field <> "#" and id_field <> ""):
                id_value = row.GetValue(id_field)
            else:
                id_value = ""            
            id_value_list.append(id_value)
            
        if (id_value_list == id_value_previous_list):
            end_dates[oid_value] = date_value_previous
            date_value_previous = row.GetValue(start_date_field)
        else:
            date_value_previous = row.GetValue(start_date_field)
            end_dates[oid_value] = date_value_previous

        id_value_previous_list = id_value_list        
        row = rows.Next()
        gp.SetProgressorPosition()

    del(rows)

    #Get an update cursor and update the end date field
    rows = gp.UpdateCursor(table, "", "", value_fields)
    row = rows.Next()
    
    while row:
        oid_value = row.GetValue(oid_field)        
        end_date_value = end_dates[oid_value]
        row.SetValue(end_date_field, end_date_value)
        rows.UpdateRow(row)
        row = rows.Next()
        gp.SetProgressorPosition()

    del(rows)    

except:
    gp.AddError(gp.GetMessages(2))
        
    
