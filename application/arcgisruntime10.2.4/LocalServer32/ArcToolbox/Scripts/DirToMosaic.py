##""********************************************************************************************************************
##TOOL NAME: DirToMosaic
##SOURCE NAME: DirToMosaic.py
##VERSION: ArcGIS 9.0
##AUTHOR: Environmental Systems Research Institute Inc.
##REQUIRED ARGUMENTS: Input workspace
##                    Output raster
##OPTIONAL ARGUMENTS: Mosaic method
##                    Colormap mode
##                    Background value
##                    Nodata value
##                    One bit to 8
##                    Mosaic tolerance
##
##TOOL DESCRIPTION: Mosaics all rasters in the input workspace to the output raster, the optional
##mosaic method instructs how the overlapping pixels are resolved, and the colormap mode controls
##how the colormaps will be modified
##
##The output Raster must exist
##
##DATE: 2/9/2004
##UPDATED: 1/25/2005
##Usage: DirToMosaic <Input_Directory> <Output_Raster> {FIRST | LAST | MEAN | BLEND | MINIMUM | MAXIMUM} <REJECT | FIRST | LAST | MATCH> {background_value} {nodata_value} {NONE | OneBitTo8Bit} {mosaicking_tolerance}
##
##NOTE ADDED AT ARCGIS 9.2: In ArcGIS 9.2, a Geoprocessing tool WorkspaceToRasterDataset is the equivalent to what
##                          this sample does and it performs better
##*********************************************************************************************************************"""

#Importing ScriptUtils which imports required librarys and creates the geoprocssing object
import os, arcgisscripting
msgNonExist="Output locations does not exist: "
msgSuccess="Successfully mosaicked: "
msgFail="Failed to mosaic to: "

try:
    gp = arcgisscripting.create(9.3)
    #The input workspace
    workspace = gp.GetParameterAsText(0)

    #The output raster
    out_raster =gp.GetParameterAsText(1)
    #Check existence
    if not gp.Exists(workspace):
        raise Exception, msgNonExist + " %s" % (workspace)

    if not gp.Exists(out_raster):
        raise Exception, msgNonExist + " %s" % (out_raster)

    mosaic_mode = gp.GetParameterAsText(2)
    colormap_mode = gp.GetParameterAsText(3)
    background = gp.GetParameterAsText(4)
    nodata = gp.GetParameterAsText(5)
    oneto8 = gp.GetParameterAsText(6)
    if (oneto8): oneto8 = "OneBitTo8Bit"
    
    tolerance = gp.GetParameterAsText(7)

    gp.SetParameterAsText(8,out_raster)
    
    gp.workspace = workspace

    #The raster datasets in the input workspace
    in_raster_datasets = gp.ListRasters()

    #For SDE and FGDB, mosaic one at a time    
    if out_raster.find('.sde') > -1 or out_raster.find('.gdb') > -1:
        for in_raster_dataset in in_raster_datasets:
            try:
##                in_raster_dataset = workspace + os.sep + in_raster_dataset
                gp.Mosaic_management(in_raster_dataset, out_raster, mosaic_mode, colormap_mode,background,nodata,oneto8,tolerance)
                gp.AddMessage(msgSuccess + " %s " % (in_raster_dataset))
            
            except Exception, ErrorDesc:
            # Except block for the loop. If the tool fails to convert one of the Rasters, it will come into this block
            #  and add warnings to the messages, then proceed to attempt to convert the next input Raster.
                WarningMessage = (msgFail + " %s" %(out_raster))
                gp.AddWarning(WarningMessage)
                
    else: #for file or PGDB, mosiac all at once
        in_rasters = ''
        for in_raster_dataset in in_raster_datasets:
           in_rasters = in_rasters + in_raster_dataset + ";"            
            
        in_rasters = in_rasters[:-1]
        try:
            gp.Mosaic_management(in_rasters, out_raster, mosaic_mode, colormap_mode,background,nodata,oneto8,tolerance)
            gp.AddMessage(msgSuccess + " %s " % (out_raster))
            
        except Exception, ErrorDesc:
        # Except block for the loop. If the tool fails to convert one of the Rasters, it will come into this block
        #  and add warnings to the messages, then proceed to attempt to convert the next input Raster.
            WarningMessage = (msgFail + " %s" %(out_raster))
            gp.AddWarning(WarningMessage)
           
except Exception, ErrorDesc:
    # Except block if the tool could not run at all.
    #  For example, not all parameters are provided, or if the output path doesn't exist.
    gp.AddError(str(ErrorDesc))
    
