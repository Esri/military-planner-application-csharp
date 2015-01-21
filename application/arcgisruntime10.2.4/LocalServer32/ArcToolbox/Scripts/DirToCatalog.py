##""********************************************************************************************************************
##TOOL NAME: DirToCatalog
##SOURCE NAME: DirToCatalog.py
##VERSION: ArcGIS 9.0
##AUTHOR: Environmental Systems Research Institute Inc.
##REQUIRED ARGUMENTS: Input workspace
##                    Output location
##                    Output name
##OPTIONAL ARGUMENTS: Keyword
##                  : Managed/unmanaged
##TOOL DESCRIPTION: Load all rasters in the input workspace to the output raster catalog, the raster and geometry
##                  columns have the same spatial reference as the first raster dataset in the list
##
##DATE: 5/31/2004
##UPDATED: 1/25/2005 for ArcGIS 9.2
##Usage: DirToMosaic <Input_Directory> <Output_Location> <Output_Name><Keyword>{managed/unmanaged}
##
##NOTE ADDED AT ARCGIS 9.2: In ArcGIS 9.2, a new Geoprocessing tool WorkspaceToRasterCatalog is the quivalent to
##                           what this sample script does and it performs better.
##
##*********************************************************************************************************************"""
##

#Importing ScriptUtils which imports required librarys and creates the geoprocssing object
import ConversionUtils, os
msgNonExist="Output locations does not exist: "
msgSuccess="Successfully loaded: "
msgFail="Failed to load: "
msgNotGDB="Output location is not GDB type: "
msgCreate="Successfully created: "
msgExist="Output raster catalog exists: "

try:
    #The input workspace
    workspace = ConversionUtils.gp.GetParameterAsText(0)

    #The output workspace
    out_location = ConversionUtils.gp.GetParameterAsText(1)

    #The output name
    out_name = ConversionUtils.gp.GetParameterAsText(2)
    
    #Check existence
    if not ConversionUtils.gp.Exists(workspace):
        raise Exception, msgNonExist + " %s" % (workspace)

    # Check if output workspace is GDB
    outWorkspace = ConversionUtils.gp.Describe(out_location)
    if (outWorkspace.WorkspaceType == "FileSystem"):
        raise Exception, msgNotGDB + " %s" % (out_location)

    keyword = ConversionUtils.gp.GetParameterAsText(3)
    manage = ConversionUtils.gp.GetParameterAsText(4)

    ConversionUtils.gp.workspace = workspace
    
    out_raster = ConversionUtils.gp.QualifyTableName(out_name, out_location)
    out_raster = out_location + os.sep + out_raster
    
    #Check existence
    if ConversionUtils.gp.Exists(out_raster):
        raise Exception, msgExist + " %s" % (out_raster)
    
    ConversionUtils.gp.SetParameterAsText(5,out_raster)
    
    #The raster datasets in the input workspace
    in_raster_datasets = ConversionUtils.gp.ListRasters()

    #The first raster dataset in the list
    #in_raster_dataset = in_raster_datasets.next()


    #Loop through all raster datasets in the list and load to raster catalog.
    #while in_raster_dataset <> None:
    icnt = 1
    for in_raster_dataset in in_raster_datasets:
        if (icnt == 1) :
            dataset = ConversionUtils.gp.Describe(in_raster_dataset)

            #Get spatial reference of first raster dataset, if no spatial reference, set it to unknown.
            try:
                sr = dataset.SpatialReference
            except Exception, ErrorDesc:
                sr = '#'

            #Create raster catalog
            ConversionUtils.gp.CreateRasterCatalog(out_location, out_name, sr, sr, keyword, "#","#","#",manage)
            ConversionUtils.gp.AddMessage(msgCreate + " %s " % (out_raster))
            icnt = 2
        try:
            ConversionUtils.gp.CopyRaster_management(in_raster_dataset, out_raster)
            ConversionUtils.gp.AddMessage(msgSuccess + " %s " % (in_raster_dataset))
        
        except Exception, ErrorDesc:
        # Except block for the loop. If the tool fails to convert one of the Rasters, it will come into this block
        #  and add warnings to the messages, then proceed to attempt to convert the next input Raster.
            WarningMessage = (msgFail + " %s" %(in_raster_dataset))
            ConversionUtils.gp.AddWarning(WarningMessage)

        #in_raster_dataset = in_raster_datasets.next()
       
except Exception, ErrorDesc:
    # Except block if the tool could not run at all.
    #  For example, not all parameters are provided, or if the output path doesn't exist.
    ConversionUtils.gp.AddError(str(ErrorDesc))

