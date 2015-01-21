##""********************************************************************************************************************
##TOOL NAME: DirToGeodatabase
##SOURCE NAME: DirToGeodatabase.py
##VERSION: ArcGIS 9.0
##AUTHOR: Environmental Systems Research Institute Inc.
##REQUIRED ARGUMENTS: Input workspace
##                    Output raster
##OPTIONAL ARGUMENTS: Configuration Keyword
##
##TOOL DESCRIPTION: Convert all rasters in the input workspace to the output geodatabase, the output dataset names
##are based on the input raster dataset names
##
##DATE: 2/9/2004
##
##Usage: DirToGeodatabase <Input_Workspace> <Output_Geodatabase> {Config_Keyword}{background_value} {nodata_value} {NONE | OneBitTo8Bit} {NONE | ColormapToRGB}
##
##*********************************************************************************************************************"""

#Importing ScriptUtils which imports required librarys and creates the geoprocssing object
import ConversionUtils, os
msgNonExist="Specified location does not exist: "
msgSuccess="Successfully converted : "
msgFail="Failed to convert "

try:
    #The input workspace
    workspace = ConversionUtils.gp.GetParameterAsText(0)

    #The output workspace
    out_gdb = ConversionUtils.gp.GetParameterAsText(1)
    #Check existence
    if not ConversionUtils.gp.Exists(workspace):
        raise Exception, msgNonExist + " %s" % (workspace)

    if not ConversionUtils.gp.Exists(out_gdb):
        raise Exception, msgNonExist + " %s" % (out_gdb)

    keyword = ConversionUtils.gp.GetParameterAsText(2)

    ConversionUtils.gp.workspace = workspace

    ConversionUtils.gp.SetParameterAsText(3,out_gdb)
    
    #The raster datasets in the input workspace
    in_raster_datasets = ConversionUtils.gp.ListRasters()

    #Loop through the array copying each raster dataset to the output workspace
    #in_raster_dataset = in_raster_datasets.next()

    #while in_raster_dataset <> None:
    for in_raster_dataset in in_raster_datasets:
        out_raster = ConversionUtils.GenerateRasterName(workspace + os.sep + in_raster_dataset, out_gdb, "")
        try:
            # Copy/Convert the inRaster to the outRaster
 
            ConversionUtils.CopyRasters(in_raster_dataset, out_raster, keyword)
            ConversionUtils.gp.AddMessage(msgSuccess + " %s to %s" % (in_raster_dataset, out_raster))
      
        except Exception, ErrorDesc:
            # Except block for the loop. If the tool fails to convert one of the Rasters, it will come into this block
            #  and add warnings to the messages, then proceed to attempt to convert the next input Raster.
            WarningMessage = (msgFail + " %s to %s" %(in_raster_dataset,out_raster))
            ConversionUtils.gp.AddWarning(WarningMessage)

        #in_raster_dataset = in_raster_datasets.next()
      
except Exception, ErrorDesc:
    # Except block if the tool could not run at all.
    #  For example, not all parameters are provided, or if the output path doesn't exist.
    ConversionUtils.gp.AddError(str(ErrorDesc))
    
