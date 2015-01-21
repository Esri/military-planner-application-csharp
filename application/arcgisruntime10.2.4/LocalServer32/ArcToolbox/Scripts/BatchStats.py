"""********************************************************************************************************************
TOOL NAME: BatchBuildPyramids
SOURCE NAME: BatchPyramids.py
VERSION: ArcGIS 9.0
AUTHOR: Environmental Systems Research Institute Inc.
REQUIRED ARGUMENTS: Input rasters
OPTIONAL ARGUMENTS:   Skip factor X
                      Skip factor y
                      Ignore values

TOOL DESCRIPTION: Calculate statistics of the input rasters in a batch operation, the input
rasters can be file rasters, geodatabase rasters, or rasters in a raster catalog. The optional
parameters instructs how the stats will be calculated.

Date Created: 11/20/2003
Updated:  4/27/2007 -- add progressor
Updated: 9/20/2007
                 - use arcgisscripting.create(9.3)
                 - add progress bar to indicate percent of work done
                 - centralize error messages with error number

Usage: BatchCalculateStatistics <Input_Raster_Datasets;Input_Raster_Datasets...> {Number_of_columns_to_skip} {Number_of_rows_to_skip} {Ignore_values;Ignore_values...}

*********************************************************************************************************************"""

#Importing standard library modules
import ConversionUtils, time

msgSuccess= ConversionUtils.gp.GetIDMessage(86119)#"Successfully calculated statistics : "
msgFail=ConversionUtils.gp.GetIDMessage(86120)#"Failed to calculate statistics : "
msgCalculating = ConversionUtils.gp.GetIDMessage(86121) #"Calculating statistics on "


#The input rasters
rasterlist = ConversionUtils.gp.GetParameterAsText(0)
# The list is split by semicolons ";"
rasterlist = ConversionUtils.SplitMultiInputs(rasterlist)

# The x skip factor
xskip = ConversionUtils.gp.GetParameterAsText(1)

# The y skip factor
yskip = ConversionUtils.gp.GetParameterAsText(2)

#The ignore values
ignore = ConversionUtils.gp.GetParameterAsText(3)

#Skip existing stats
skipexist = ConversionUtils.gp.GetParameterAsText(4)

rastercnt = len(rasterlist)
#Message "Calculating statistics..."
ConversionUtils.gp.SetProgressor("step", ConversionUtils.gp.GetIDMessage(86122), 0, rastercnt, 1)
currentloc = 1

for raster in rasterlist:
    try:
        ConversionUtils.gp.SetProgressorLabel(msgCalculating + "%s (%d/%d)" % (raster, currentloc, rastercnt))
        ConversionUtils.gp.CalculateStatistics_management(raster,xskip,yskip,ignore,skipexist)
        ConversionUtils.gp.AddMessage(msgSuccess + "%s" % raster)
        currentloc += 1

    except Exception, ErrorDesc:
        # Except block for the loop. If the tool fails to calculate for one of the Rasters, it will come into this block
        #  and add warnings to the messages, then proceed to attempt to calculate the next input Raster.
        msgWarning = msgFail + "%s" % raster
        msgStr = ConversionUtils.gp.GetMessages(2)
        ConversionUtils.gp.AddWarning(ConversionUtils.ExceptionMessages(msgWarning, msgStr, ErrorDesc))

    ConversionUtils.gp.SetProgressorPosition()

time.sleep(0.5)
