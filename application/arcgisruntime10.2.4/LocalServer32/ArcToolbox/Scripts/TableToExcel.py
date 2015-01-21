"""
Tool name: Table To Excel
Source: TableToExcel.py
Author: ESRI

Convert an table to a MS Excel spreadsheet.
"""
import arcpy
import os
import sys
import xlwt
import datetime

class clsField(object):
    """ Class to hold properties and behavior of the output fields
    """
    @property
    def alias(self):
        return self._field.aliasName

    @property
    def name(self):
        return self._field.name

    @property
    def domain(self):
        return self._field.domain

    @property
    def type(self):
        return self._field.type

    @property
    def length(self):
        return self._field.length

    def __init__(self, f, i, subtypes):
        """ Create the object from a describe field object
        """
        self.index = None
        self._field = f
        self.subtype_field = ''
        self.domain_desc = {}
        self.subtype_desc = {}
        self.index = i

        # Inception inspired dictionary in a dictionary
        for st_key, st_val in subtypes.iteritems():
            if st_val['SubtypeField'] == f.name:
                self.subtype_desc[st_key] = st_val['Name']
                self.subtype_field = f.name
            for k, v in st_val['FieldValues'].iteritems():
                if k == f.name:
                    if len(v) == 2:
                        if v[1]:
                            self.domain_desc[st_key]= v[1].codedValues
                            self.subtype_field = st_val['SubtypeField']

    def __repr__(self):
        """ Nice representation for debugging  """
        return '<clsfield object name={}, alias={}, domain_desc={}>'.format(self.name,
                                                                self.alias,
                                                                self.domain_desc)

    def updateValue(self, row, fields):
        """ Update value based on domain/subtypes """
        value = row[self.index]
        if self.subtype_field:
            subtype_val = row[fields.index(self.subtype_field)]
        else:
            subtype_val = 0

        if self.subtype_desc:
            value = self.subtype_desc[row[self.index]]

        if self.domain_desc:
            try:
                value = self.domain_desc[subtype_val][row[self.index]]
            except:
                pass # not all subtypes will have domain

        # Return the validated value
        return value

def get_field_defs(in_table, use_domain_desc):
    desc = arcpy.Describe(in_table)

    subtypes ={}
    if use_domain_desc:
        subtypes = arcpy.da.ListSubtypes(in_table)

    fields = []
    for i, field in enumerate([f for f in desc.fields
                                if f.type in ["Date","Double","Guid",
                                              "Integer","OID","Single",
                                              "SmallInteger","String"]]):
        fields.append(clsField(field, i, subtypes))

    return fields

def validate_sheet_name(sheet_name):
    """ Validate sheet name to excel limitations
         - 31 character length
         - there characters not allowed : \ / ? * [ ]
    """
    import re
    if len(sheet_name) > 31:
        sheet_name = sheet_name[:31]

    # Replace invalid sheet character names with an underscore
    r = re.compile(r'[:\\\/?*\[\]]')
    sheet_name = r.sub("_", sheet_name)

    return sheet_name

def add_error(id, s=None):
    """ Return errors """

    arcpy.AddIDMessage("ERROR", id, s if s else None)
    if __name__ == '__main__':
        sys.exit(1)
    else:
        raise arcpy.ExecuteError, arcpy.GetIDMessage(id)

def table_to_excel(in_table, output, use_field_alias=False, use_domain_desc=False):
    """ Writes a table to an XLS file """

    fields = get_field_defs(in_table, use_domain_desc)

    if os.path.isfile(output):
        if arcpy.env.overwriteOutput == False:
            add_error(258, output)
        else:
            os.remove(output)

    if int(arcpy.GetCount_management(in_table)[0]) > 65535:
        # Input table exceeds the 256 columns limit of the .xls file format.
        add_error(1531)

    elif len(fields) > 255:
        # Input table exceeds the 65535 rows limit of the .xls file format.
        add_error(1530)

    # Make spreadsheet
    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet(
        validate_sheet_name(os.path.splitext(os.path.basename(output))[0]))

    # Add first (header) row
    header_style = xlwt.easyxf("font: bold on; align: horiz center; pattern: pattern solid, fore-colour 0x16;")

    for index, field in enumerate(fields):
        worksheet.write(0, index, field.alias if use_field_alias else field.name , header_style)
        if field.type == 'String':
            worksheet.col(index).width = min(50, field.length)*256
        else:
            worksheet.col(index).width = 16*256

    # Freeze panes
    worksheet.set_panes_frozen(True)
    worksheet.set_horz_split_pos(1)
    worksheet.set_remove_splits(True)

    # Set cell format/styles for data types
    styleDefault = xlwt.XFStyle()

    styleDate = xlwt.XFStyle()
    styleDate.num_format_str = 'YYYY-MM-DD'

    styleTime = xlwt.XFStyle()
    styleTime.num_format_str = 'h:mm'

    styleDateTime = xlwt.XFStyle()
    styleDateTime.num_format_str = 'YYYY-MM-DD h:mm'

    styleInt = xlwt.XFStyle()
    styleInt.num_format_str = '0'

    field_names = [i.name for i in fields]
    # Loop through input records
    with arcpy.da.SearchCursor(in_table, field_names) as cursor:
        row_index = 1
        for row in cursor:
            for col_index, value in enumerate(row):
                if (fields[col_index].domain_desc or fields[col_index].subtype_desc):
                    value = fields[col_index].updateValue(row, field_names)

                if isinstance(value, datetime.datetime):
                    if (value.hour == 0) and (value.minute == 0):
                        style = styleDate
                    elif (value.year == 1899) and (value.month == 12) and (value.day == 30):
                        style = styleTime
                        value = (value-datetime.datetime(1899, 12,30,0,0,0)).total_seconds()/86400.0
                    else:
                        style = styleDateTime

                elif isinstance(value, int):
                    style = styleInt

                else:
                    style = styleDefault

                # write to the cell
                worksheet.write(row_index, col_index, value, style)
            row_index+=1

    workbook.save(output)

if __name__ == "__main__":
    table_to_excel(arcpy.GetParameterAsText(0),
                   arcpy.GetParameterAsText(1),
                   arcpy.GetParameter(2),
                   arcpy.GetParameter(3))