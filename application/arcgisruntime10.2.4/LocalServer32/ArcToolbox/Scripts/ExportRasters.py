"""********************************************************************************************************************
TOOL NAME: RasterToOtherFormat
SOURCE NAME: ExportRasters.py
AUTHOR: Environmental Systems Research Institute Inc.
REQUIRED ARGUMENTS: Input rasters
                    Output geodatabase
OPTIONAL ARGUMENTS: Raster format

TOOL DESCRIPTION: Converts or copies one or more Rasters to a workspace, the input Rasters can be file Rasters, or Geodatabase Rasters, the output parameter will be a workspace.
The optional raster format controls the outpur raster datset format, by default, the format is GRID

The name of the output Raster will be based on the name of the input name, but will be unique for
the destination workspace.

Date Created: 11/20/2003
Update: 5/26/2005
Updated: 4/27/2007 add progressor
Updated: 9/18/2007
                 - use arcgisscripting.create(9.3)
                 - add progress bar to indicate percent of work done
                 - centralize error messages with error number
                 
Usage: RasterToOtherFormat <Input_rasters;Input_rasters...> <Output_workspace> {GRID | IMAGINE Image | TIFF | }

*********************************************************************************************************************"""

import ConversionUtils, time

msgWorkspace=ConversionUtils.gp.GetIDMessage(86127) #"Output location does not exist: "
msgSuccess= ConversionUtils.gp.GetIDMessage(86128) #"Successfully converted: "
msgFail=ConversionUtils.gp.GetIDMessage(86129) #"Failed to convert: "
msgConverting = ConversionUtils.gp.GetIDMessage(86130) #"Converting "

# Argument 1 is the list of Rasters to be converted
inRasters = ConversionUtils.gp.GetParameterAsText(0)

# The list is split by semicolons ";"
inRasters = ConversionUtils.SplitMultiInputs(inRasters)

# The output workspace where the shapefiles are created
outWorkspace = ConversionUtils.gp.GetParameterAsText(1)

# Set the destination workspace parameter (which is the same value as the output workspace)
# the purpose of this parameter is to allow connectivity in Model Builder.
# ConversionUtils.gp.SetParameterAsText(2,outWorkspace)
ext = ConversionUtils.gp.GetParameterAsText(2)

# Get proper extension based on the format string
if (ext == "IMAGINE Image"):
    ext = ".img"
elif (ext == "TIFF"):
    ext = ".tif"
elif (ext == "BMP"):
    ext = ".bmp"
elif (ext == "PNG"):
    ext = ".png"
elif (ext == "JPEG"):
    ext = ".jpg"
elif (ext == "JP2000"):
    ext = ".jp2"
elif (ext == "GIF"):
    ext = ".gif"
elif (ext == "GRID"):
    ext = ""
elif (ext == "BIL"):
    ext = ".bil"
elif (ext == "BIP"):
    ext = ".bip"
elif (ext == "BSQ"):
    ext = ".bsq"
elif (ext == "ENVI DAT"):
    ext = ".dat"

# Add progressor
rastercnt = len(inRasters)
ConversionUtils.gp.SetProgressor("step", msgConverting, 0, rastercnt, 1)
currentloc = 1

# Loop through the list of input Rasters and convert/copy each to the output geodatabase or folder
for raster in inRasters: 
    try:
        ConversionUtils.gp.SetProgressorLabel(msgConverting + "%s (%d/%d)" % (raster, currentloc, rastercnt))
        raster = ConversionUtils.ValidateInputRaster(raster)
        
        outRaster = ConversionUtils.GenerateRasterName(raster, outWorkspace, ext)

        # Copy/Convert the inRaster to the outRaster
        ConversionUtils.CopyRasters(raster, outRaster, "")
        
        # If the Copy/Convert was successfull add a message stating this
        ConversionUtils.gp.AddMessage(msgSuccess + "%s To %s" % (raster, outRaster))

        currentloc += 1

    except Exception, ErrorDesc:
        # Except block for the loop. If the tool fails to convert one of the Rasters, it will come into this block
        #  and add warnings to the messages, then proceed to attempt to convert the next input Raster.
        msgWarning = msgFail + "%s" % input
        msgStr = ConversionUtils.gp.GetMessages(2)
        ConversionUtils.gp.AddWarning(ConversionUtils.ExceptionMessages(msgWarning, msgStr, ErrorDesc))
        
    ConversionUtils.gp.SetProgressorPosition()
    
time.sleep(0.5)

