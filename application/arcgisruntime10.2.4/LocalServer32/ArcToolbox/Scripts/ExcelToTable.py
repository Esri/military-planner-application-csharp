# -*- coding: utf-8 -*-
"""
Tool name: Excel To Table
Source: ExcelToTable.py
Author: ESRI

Convert a Microsoft Excel (xls or xlsx) file to an geodatabase, dbf or INFO table.
"""
import arcpy
import os
import sys
from datetime import datetime
import xlrd
import time

class clsField(object):
    """ Class to hold properties and behavior of the output fields """

    def __init__(self, name, workspace, is_gdb=True, fields=[]):
        """ Validate name of field based on output table format as well
              as existing/used field names
        """
        self.ftype = None
        self.length = None
        self.is_gdb= is_gdb
        self.alias = name if name else None

        name = arcpy.ValidateFieldName(name, workspace)

        if not is_gdb:
            # dbf can't take non-alpha character to begin field name
            if not name[0].isalpha():
                name = 'f' + name
            name = name[:10]
        elif not name:
            name = 'field'
        elif name.lower() == 'oid':
            # uncaught 'invalid' name
            name += '_'

        names = [f.name.lower() for f in fields] + ['objectid']

        # if name not unique, add _i to it
        i = 0
        while names.count(name.lower()) != 0:
            i+=1
            name = "{0}_{1}".format(name[:8], i)
        self.name = name

    def __repr__(self):
        """ Nice repr for debugging. """
        return u'<clsfield.name="{}", alias={}, ftype="{}", length="{}">'.format(
                                                                self.name,
                                                                self.alias,
                                                                self.ftype,
                                                                self.length)

    def set_field_type(self, workbook, sheet, i, eval_count):
        """ Set the output field type based on first n records """
        fieldmap ={1: 'Text', 2: 'Double', 3: 'Date', 4: 'Long'}

        # Get list of all typse in cloumn (don't count blank 0,5,6)
        cell_types = set(sheet.col_types(colx = i,
                                         start_rowx = 1,
                                         end_rowx = eval_count)) - set((0, 5, 6))

        if len(cell_types) == 1:
            # if all cells are the same type use that type
            self.ftype = fieldmap[list(cell_types)[0]]

            # no such thing as Integer in excel, but if all look like integer, use integer
            if self.ftype == 'Double':
                try:
                    for row in xrange(1, eval_count):
                        value = sheet.cell(row, i).value
                        if value:
                            assert((value % 1) == 0.0)  # no remainder then Integer
                            assert(value <  2.1e+9)     # limit for Long Integer
                            assert(value > -2.1e+9)     # limit for Long Integer
                    self.ftype = 'Long'
                except:
                    pass

        else:
            self.ftype = 'Text'

        # if text in a gdb, set field's length based on longest value
        if self.ftype == 'Text' and self.is_gdb:
            maxlen = 255
            for row in xrange(1, eval_count):
                value = sheet.cell(row,i).value
                if value and type(value) in [str, unicode]:
                    maxlen = max(maxlen, len(value) + 10)
            self.length = maxlen

    def validate_value(self, value, datemode):
        """ Validate the value against the output field
        """
        if self.ftype == 'Date' and value:
            value = xlrd.xldate_as_tuple(value, datemode)
            if value[:3] == (0,0,0):
                # time only is no good for datetime.datetime() use
                value = (1899, 12, 30, value[3], value[4], value[5])
            value = datetime(*value)

        # Non-gdb do not support None/Null (except with Date)
        if not self.is_gdb:
            if value in [None, '']:
                if self.ftype == 'Text':
                    value = ""
                elif self.ftype == 'Date':
                    value = None
                else:
                    value = 0

        # Cannot set '' into a numeric or date field in a gdb
        elif self.ftype in ['Double', 'Date', 'Long'] and value == '':
            value = None

        # Return the validated value
        return value

def get_sheet_names(in_excel):
    """ Returns a list of sheet names for the selected excel file.
          This function is used in the script tool's Validation
    """
    workbook = xlrd.open_workbook(in_excel)
    return [sheet.name for sheet in workbook.sheets()]

def open_excel_table(in_excel, sheet_name):
    """ Open the excel file, return sheet and workbook. """

    try:
        workbook = xlrd.open_workbook(in_excel)
        worksheet = workbook.sheet_by_name(sheet_name)
        return worksheet, workbook

    except Exception as err:
        arcpy.AddError(err)
        if __name__ == '__main___':
            sys.exit()
        else:
            raise

def validate_fields(in_excel, out_table, sheet_name, rows=100):
    """ Validates field names, eliminating duplicate names and invalid
        characters. This is only used in the script tool's Validation.
    """
    # Code works, but xlrd.open_workbook can be quite slow, don't want
    #  to pay this cost in updateParameter (called in tool dialog).
    return []

    workbook = xlrd.open_workbook(in_excel)
    sheet, workbook = open_excel_table(in_excel, sheet_name)
    out_path, out_table_name = os.path.split(out_table)
    is_gdb = not arcpy.Describe(out_path).workspaceType == "FileSystem"
    return [f.name for f in gen_out_fields(workbook,
                                           sheet,
                                           out_path,
                                           is_gdb,
                                           rows)]

def gen_out_fields(workbook, sheet, out_path, is_gdb, eval_count=None):
    """ Generate the list of output field names based on inputs """

    if sheet.nrows == 0:
        return []

    if eval_count is None:
        eval_count = sheet.nrows
    else:
        eval_count = min(eval_count, sheet.nrows)

    out_fields = []
    # Generate the list of output fields
    for f in sheet.row_values(0):
        out_fields.append(clsField(f, out_path, is_gdb, out_fields))

    # Set the Field types based on values
    for i in xrange(0, len(out_fields)) :
        out_fields[i].set_field_type(workbook, sheet, i, eval_count)

    return out_fields

def excel_to_table(in_excel, out_table, sheet_name=None):
    """ Convert an excel sheet to a gdb table, dbf, or info table """

    if sheet_name in [None, '', '#']:
        sheet_name = get_sheet_names(in_excel)[0]

    if arcpy.Exists(out_table):
        if arcpy.env.overwriteOutput == False:
            arcpy.AddIDMessage("ERROR", 258, out_table)
            if __name__ == '__main__':
                print u'ERROR ' + arcpy.GetIDMessage(258)
                sys.exit(1)
            else:
                raise arcpy.ExecuteError, arcpy.GetIDMessage(258)

    sheet, workbook = open_excel_table(in_excel, sheet_name)

    out_path, out_table_name = os.path.split(out_table)
    is_gdb = not arcpy.Describe(out_path).workspaceType == "FileSystem"

    out_fields = gen_out_fields(workbook, sheet, out_path, is_gdb)

    # For performance reasons, add the fields to an in_memory table
    tmp_table = os.path.join('in_memory','tmp_exceltotable_template')
    if arcpy.Exists(tmp_table):
        arcpy.Delete_management(tmp_table)

    arcpy.CreateTable_management(*os.path.split(tmp_table))

    # Add the fields that were validates using the previous function
    for f in out_fields:
        arcpy.AddField_management(tmp_table,
                                  f.name,
                                  field_type = f.ftype,
                                  field_length = f.length,
                                  field_alias = f.alias)

    # Now create the actual output table based on
    arcpy.CreateTable_management(out_path,
                                 out_table_name,
                                 template=tmp_table)

    arcpy.Delete_management(tmp_table)

    # Output info table has trouble with OBJECTID field
    if not is_gdb and not out_table.lower().endswith('.dbf') and \
                      not out_table.lower().startswith('in_memory'):
        arcpy.DeleteField_management(out_table, 'OBJECTID')

    # If the sheet has no rows, warn and exit
    if sheet.nrows < 2:
        arcpy.AddIDMessage('WARNING', 117)
        return

    # Loop through each row and insert values into the output table
    with arcpy.da.InsertCursor(out_table, [f.name for f in out_fields]) as cursor:
        for rowid in xrange(1, sheet.nrows):
            row = sheet.row_values(rowid)
            for i, field in enumerate(out_fields):
                row[i] = field.validate_value(row[i], workbook.datemode)
            try:
                cursor.insertRow(row)
            except Exception as e:
                print e

if __name__ == "__main__":
    # Get the parameters from the script tool
    excel_to_table(arcpy.GetParameterAsText(0),
                   arcpy.GetParameterAsText(1),
                   arcpy.GetParameterAsText(2))
