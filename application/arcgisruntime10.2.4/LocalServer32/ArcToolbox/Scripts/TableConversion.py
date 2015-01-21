"""********************************************************************************************************************
TableConversion.py
Version: ArcGIS 10.1
 
Description: Converts or copies one or more tables to a GeoDatabase or folder.
The input tables can be dBase, INFO tables, or Geodatabase tables. Depending on which tool is
calling this script, the output parameter will be a SDE or a personal Geodatabase which means
the output will be geodatabase feature classes, the output parameter will be a folder, which means
the output will be DBase.

The name of the output table will be based on the name of the input name, but will be unique for
the destination workspace or folder.

Author: ESRI, Redlands
                 
Usage: TableToGeodatabase <in_table;in_table...> <out_workspace>
Usage: TableToDBase <in_table;in_table...> <out_folder>
*********************************************************************************************************************"""

import ConversionUtils
import time

#Define message constants so they may be translated easily
msgFail = ConversionUtils.gp.GetIDMessage(86153) #"Failed to convert "
msgConverting = ConversionUtils.gp.GetIDMessage(86130) #"Converting "

# Argument 1 is the list of tables to be converted
inTables = ConversionUtils.gp.GetParameterAsText(0)

# The list is split by semicolons ";"
inTables = ConversionUtils.SplitMultiInputs(inTables)

# The output workspace where the shapefiles are created
outWorkspace = ConversionUtils.gp.GetParameterAsText(1)

# Set the destination workspace parameter (which is the same value as the output workspace)
# the purpose of this parameter is to allow connectivity in Model Builder.
ConversionUtils.gp.SetParameterAsText(2,outWorkspace)
#message "Converting multiple tables ..."
ConversionUtils.gp.SetProgressor("step",ConversionUtils.gp.GetIDMessage(86175) , 0, len(inTables))
   
# Loop through the list of input tables and convert/copy each to the output geodatabase or folder
for inTable in inTables:

    try: 
        # Generate a valid output output name
        outTable = ConversionUtils.GenerateOutputName(inTable, outWorkspace)
        
        # Set the progressor label
        ConversionUtils.gp.SetProgressorLabel(msgConverting + inTable)
        
        # Copy/Convert the inTable to the outTable
        ConversionUtils.CopyRows(inTable, outTable)
        #Message "Converted %s to %s successfully." 
        ConversionUtils.gp.AddIDMessage("Informative", 86176, inTable, outTable)

    except Exception, ErrorDesc:
        # Except block for the loop. If the tool fails to convert one of the tables, it will come into this block
        #  and add warnings to the messages, then proceed to attempt to convert the next input table.        
        msgWarning = msgFail + "%s" % inTable
        msgStr = ConversionUtils.gp.GetMessages(2)
        ConversionUtils.gp.AddWarning(ConversionUtils.ExceptionMessages(msgWarning, msgStr, ErrorDesc))

    ConversionUtils.gp.SetProgressorPosition()
    
time.sleep(0.5) 
