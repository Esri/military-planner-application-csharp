##""********************************************************************************************************************
##TOOL NAME: DirToNewMosaic
##SOURCE NAME: DirToNewMosaic.py
##VERSION: ArcGIS 9.2
##AUTHOR: Environmental Systems Research Institute Inc.
##REQUIRED ARGUMENTS: Input workspace
##                    Output location
##                    Output name
##OPTIONAL ARGUMENTS: Keyword
##                    Mosaic mode
##                    Colormap mode
##                    Origin
##                    Background value
##                    Nodata value
##                    One bit to 8
##                    Mosaic tolerance
##TOOL DESCRIPTION: Mosaics all rasters in the input workspace to the a new raster, the optional
##mosaic method instructs how the overlapping pixels are resolved, and the colormap mode controls
##how the colormaps will be modified
##
##
##DATE: 5/31/2004
##UPDATED: 1/17/2006 for ArcGIS 9.2
##Usage: DirToMosaic <Input_Directory> <Output_Location> <Output_Name><Keyword>{FIRST | LAST | MEAN | BLEND | MINIMUM | MAXIMUM} <REJECT | FIRST | LAST | MATCH><Origin>{background_value} {nodata_value} {NONE | OneBitTo8Bit} {mosaicking_tolerance}
##
##
##*********************************************************************************************************************"""

#Importing ScriptUtils which imports required librarys and creates the geoprocssing object
import ConversionUtils, os

msgNonExist="Output locations does not exist: "
msgSuccess="Successfully mosaicked to "
msgFail="Failed to mosaic to: "
msgCreate="Successfully created: "
msgWarning="Failed to mosaic: "
msgInSuccess="Successfullly mosaicked "
msgOutExist="Output raster dataset exists: "

def pixel_type(name):
    try:
        if (name == "U1"):
            return "1_bit"
        if (name == "U2"):
            return "2_bit"
        if (name == "U4"):
            return "4_bit"
        if (name == "U8"):
            return "8_bit_unsigned"
        if (name == "S8"):
            return "8_bit_signed"
        if (name == "U16"):
            return "16_bit_unsigned"
        if (name == "S16"):
            return "16_bit_signed"
        if (name =="U32"):
            return "32_bit_unsigned"
        if (name =="S32"):
            return "32_bit_signed"
        if (name =="F32"):
            return "32_bit_float"
        if (name == "D64"):
            return "64_bit"

    except:
        raise Exception, ConversionUtils.gp.GetMessages(2).replace('\n',' ')
    
    
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

    keyword = ConversionUtils.gp.GetParameterAsText(3)
    mosaic_mode = ConversionUtils.gp.GetParameterAsText(4)
    colormap_mode = ConversionUtils.gp.GetParameterAsText(5)
    origin = ConversionUtils.gp.GetParameterAsText(6) # origin
    background = ConversionUtils.gp.GetParameterAsText(7)
    nodata = ConversionUtils.gp.GetParameterAsText(8)
    oneto8 = ConversionUtils.gp.GetParameterAsText(9)
    if (oneto8):
        oneto8 = "OneBitTo8Bit"
    else:
        oneto8 = "NONE"
            
    tolerance = ConversionUtils.gp.GetParameterAsText(10)

    ConversionUtils.gp.workspace = workspace

    #The raster datasets in the input workspace
    in_raster_datasets = ConversionUtils.gp.ListRasters()

    #Get first raster dataset

    #in_raster_dataset = in_raster_datasets.next()
    in_rasters = ""

    out_raster = ConversionUtils.gp.QualifyTableName(out_name, out_location)
    out_raster = out_location + os.sep + out_raster

    #Check existence
    if ConversionUtils.gp.Exists(out_raster):
        raise Exception, msgOutExist + " %s" % (out_raster)
    
    ConversionUtils.gp.SetParameterAsText(11,out_raster) 

    icnt = 1
    bSDE = 0
    if out_location[-4:] == '.sde' or out_location[-4:] == '.gdb' :
        bSDE = 1
    for in_raster_dataset in in_raster_datasets:
        if (icnt == 1):
            dataset = ConversionUtils.gp.Describe(in_raster_dataset)
            bandcnt = dataset.BandCount

            #Get pixel type of the first raster dataset
            if bandcnt > 1:
                bands = dataset.Children
                band = bands.Next()
                pixeltype = pixel_type(band.PixelType)
            else:
                pixeltype = pixel_type(dataset.PixelType)

            #Get spatial reference of the first raster dataset, if empty then set it to unknown
            try:
                sr = dataset.SpatialReference
            except Exception, ErrorDesc:
                sr = '#'
            try:
                ConversionUtils.gp.CreateRasterDataset(out_location, out_name,"#",pixeltype, sr, bandcnt, keyword, "#","#","#",origin)
                ConversionUtils.gp.AddMessage(msgCreate + " %s" %(out_location + os.sep + out_name))
            except Exception, ErrorDesc:
            # Except block for the loop. If the tool fails to convert one of the Rasters, it will come into this block
            #  and add warnings to the messages, then proceed to attempt to convert the next input Raster.
                WarningMessage = (msgFail + " %s" %(out_raster))
                ConversionUtils.gp.AddWarning(WarningMessage)
            icnt = 2
            
        #If the output location is SDE or FGDB, mosaic raster one at a time.  
        if (bSDE == 1):
            try:
                ConversionUtils.gp.Mosaic_management(in_raster_dataset, out_raster, mosaic_mode, colormap_mode, background,nodata,oneto8,tolerance)
                ConversionUtils.gp.AddMessage(msgInSuccess + " %s " % (in_raster_dataset))
            except:
                ConversionUtils.gp.AddWarning(Warning)
        else:
            in_rasters = in_rasters + in_raster_dataset + ";"                        

    if (bSDE == 0):        
        in_rasters = in_rasters[:-1]

        ConversionUtils.gp.AddMessage(in_rasters)
        ConversionUtils.gp.Mosaic_management(in_rasters, out_raster, mosaic_mode, colormap_mode, background,nodata,oneto8,tolerance)
        ConversionUtils.gp.AddMessage(msgSuccess + " %s " % (out_raster))
        

       
except Exception, ErrorDesc:
    # Except block if the tool could not run at all.
    #  For example, not all parameters are provided, or if the output path doesn't exist.
    ConversionUtils.gp.AddError(str(ErrorDesc))

