"""********************************************************************************************************************
TOOL NAME: RasterToGeodatabase
SOURCE NAME: RasterConversion.py
VERSION: ArcGIS 9.0
AUTHOR: Environmental Systems Research Institute Inc.
REQUIRED ARGUMENTS: Input rasters
                    Output geodatabase
OPTIONAL ARGUMENTS: Configuration keyword for enterprise geodatabase

TOOL DESCRIPTION: Converts or copies one or more Rasters to a workspace, the input Rasters can be file Rasters, or Geodatabase Rasters. Depending on which tool is
calling this script, the output parameter will be a workspace.

The name of the output Raster will be based on the name of the input name, but will be unique for
the destination geodatabase.

Date Created: 11/20/2003
Updated: 9/20/2007
                 - use arcgisscripting.create(9.3)
                 - add progress bar to indicate percent of work done
                 - centralize error messages with error number
                 
Usage: RasterToGeodatabase <Input_Rasters;Input_Rasters...> <Output_Geodatabase> {Configuration_Keyword}
*********************************************************************************************************************"""

import ConversionUtils, time

msgWorkspace=ConversionUtils.gp.GetIDMessage(86127)#"Output location does not exist: "
msgParams=ConversionUtils.gp.GetIDMessage(86152)#"Insufficient number of parameters provided"
msgSuccess=ConversionUtils.gp.GetIDMessage(86128)#"Successfully converted: "
msgFail= ConversionUtils.gp.GetIDMessage(86153) #"Failed to convert "
msgConverting = ConversionUtils.gp.GetIDMessage(86130) #"Converting "

# Argument 1 is the list of Rasters to be converted
inRasters = ConversionUtils.gp.GetParameterAsText(0)

# The list is split by semicolons ";"
inRasters = ConversionUtils.SplitMultiInputs(inRasters) 

# The output workspace where the shapefiles are created
outWorkspace = ConversionUtils.gp.GetParameterAsText(1)

# The configuration keyword    
keyword = ConversionUtils.gp.GetParameterAsText(2)

# Set the destination workspace parameter (which is the same value as the output workspace)
# the purpose of this parameter is to allow connectivity in Model Builder.
# ConversionUtils.gp.SetParameterAsText(2,outWorkspace)

rastercnt = len(inRasters)
ConversionUtils.gp.SetProgressor("step", msgConverting, 0, rastercnt, 1)
currentloc = 1

# Loop through the list of input Rasters and convert/copy each to the output geodatabase or folder
for raster in inRasters:
    try:
        raster = ConversionUtils.ValidateInputRaster(raster)
        ConversionUtils.gp.SetProgressorLabel(msgConverting + "%s (%d/%d)" % (raster, currentloc, rastercnt))
        
        outRaster = ConversionUtils.GenerateRasterName(raster, outWorkspace, "")

        # Copy/Convert the inRaster to the outRaster
        ConversionUtils.CopyRasters(raster, outRaster, keyword)
        
        # If the Copy/Convert was successfull add a message stating this
        ConversionUtils.gp.AddMessage(msgSuccess + " %s To %s" % (raster, outRaster))
        currentloc += 1

    except Exception, ErrorDesc:
        # Except block for the loop. If the tool fails to convert one of the Rasters, it will come into this block
        #  and add warnings to the messages, then proceed to attempt to convert the next input Raster.
        msgWarning = msgFail + "%s" % raster
        msgStr = ConversionUtils.gp.GetMessages(2)
        ConversionUtils.gp.AddWarning(ConversionUtils.ExceptionMessages(msgWarning, msgStr, ErrorDesc))
        
    ConversionUtils.gp.SetProgressorPosition()
    
time.sleep(0.5)
