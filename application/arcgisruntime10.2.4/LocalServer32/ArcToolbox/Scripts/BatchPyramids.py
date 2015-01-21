"""********************************************************************************************************************
TOOL NAME: BatchBuildPyramids
SOURCE NAME: BatchPyramids.py
VERSION: ArcGIS 9.0
AUTHOR: Environmental Systems Research Institute Inc.
REQUIRED ARGUMENTS: Input rasters

TOOL DESCRIPTION: Build pyramids of the input rasters in a batch operation, the input
rasters can be file rasters, geodatabase rasters, or rasters in a raster catalog

Date Created: 11/20/2003
Updated: 9/20/2007
                 - use arcgisscripting.create(9.3)
                 - add progress bar to indicate percent of work done
                 - centralize error messages with error number
                 - add new pyramid option parameter

Usage: BatchBuildPyramids <Input_Raster_Datasets;Input_Raster_Datasets...> {pyramids_options}
*********************************************************************************************************************"""

#Importing standard library modules
import ConversionUtils, time

msgSuccess= ConversionUtils.gp.GetIDMessage(86115) #"Successfully built pyramids on "
msgFail=ConversionUtils.gp.GetIDMessage(86116) #"Failed to build pyramids on "
msgBuilding = ConversionUtils.gp.GetIDMessage(86117) #"Building pyramids on "

#The input rasters
rasterlist = ConversionUtils.gp.GetParameterAsText(0)
pyramidlevel = ConversionUtils.gp.GetParameterAsText(1)
pyramidskip = ConversionUtils.gp.GetParameterAsText(2)
pyramidresample = ConversionUtils.gp.GetParameterAsText(3)
pyramidcompress = ConversionUtils.gp.GetParameterAsText(4)
pyramidquality = ConversionUtils.gp.GetParameterAsText(5)
skipexisting = ConversionUtils.gp.GetParameterAsText(6)

# The list is split by semicolons ";"
rasterlist = ConversionUtils.SplitMultiInputs(rasterlist)

rastercnt = len(rasterlist)
#Message "Building pyramids..."
ConversionUtils.gp.SetProgressor("step",ConversionUtils.gp.GetIDMessage(86118) , 0, rastercnt, 1)
currentloc = 1

for raster in rasterlist:
    try:
        ConversionUtils.gp.SetProgressorLabel(msgBuilding + "%s (%d/%d)" % (raster, currentloc, rastercnt))
        ConversionUtils.gp.BuildPyramids_management(raster, pyramidlevel, pyramidskip, pyramidresample, pyramidcompress,
                                                    pyramidquality, skipexisting)
        ConversionUtils.gp.AddMessage(msgSuccess + "%s" % raster)
        currentloc += 1
    except Exception, ErrorDesc:
        # Except block for the loop. If the tool fails to build for one of the Rasters, it will come into this block
        #  and add warnings to the messages, then proceed to attempt to build the next input Raster.
        msgWarning = msgFail + "%s" % raster
        msgStr = ConversionUtils.gp.GetMessages(2)
        ConversionUtils.gp.AddWarning(ConversionUtils.ExceptionMessages(msgWarning, msgStr, ErrorDesc))

    ConversionUtils.gp.SetProgressorPosition()
