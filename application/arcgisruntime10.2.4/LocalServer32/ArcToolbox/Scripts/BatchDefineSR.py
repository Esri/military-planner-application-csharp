"""
 NAME: BatchDefineSR
 Source Name: BatchDefineSR.py
 Version: ArcGIS 9.0
 Author: Environmental Systems Research Institute Inc.
 Usage: BatchDefineSR <input_data>, {output_coordinate_system}, {template_geodataset}
 Required Arguments: A set of input geodatasets or layers
                     
 Optional Arguments: A Coordinate System. This is not required if a template feature class is used.
                     A template geodataset. This is not required if a Coordinate System is used.
 Description: Define spatial reference on multiple input geodatasets.  
             A coordinate system can be specified by defining it manually or using the coordinate system of an
             existing geodataset. 
 Date Created: June 4, 2003
 Updated: February, 15, 2005
 Updated: September 20, 2007
                 - use arcgisscripting.create(9.3)
                 - add progress bar to indicate percent of work done
                 - centralize error messages with error number
"""

###Import required modules
import ConversionUtils, time

#Define message constants so they may be translated easily
msgCoordinateSystem = "Must Enter a Spatial Reference or Template Geodataset."
msgInvalidParameters = "Invalid number of parameters. Spatial Reference or Template must be provided."
msgPrjAlreadyDefine = "The dataset already has a projection defined."
unknown_projection = "Unknown"

try:

    #Set the input datasets
    inputs  = ConversionUtils.gp.GetParameterAsText(0)
    inDatasets = ConversionUtils.SplitMultiInputs(inputs)
    
    #Set the spatial reference
    out_CS = ConversionUtils.gp.GetParameterAsText(1)

    #Set the template dataset
    temp_data = ConversionUtils.gp.GetParameterAsText(2)

    #Set output boolean parameter "Completed" to false by default.    
    ConversionUtils.gp.SetParameterAsText(3, 0)

    #Set output boolean parameter "Error" to false by default.        
    ConversionUtils.gp.SetParameterAsText(4, 0)

    #Set the spatial reference. Check for template dataset.
    if (out_CS == "" or out_CS == "#") and (temp_data == "" or temp_data == "#"):
        raise ConversionUtils.GPError(msgCoordinateSystem) 
    elif (out_CS != "") and (out_CS != "#"):
        sr = out_CS
    elif (temp_data != "") and (temp_data != "#"):
        dsc = ConversionUtils.gp.Describe(temp_data)
        sr = dsc.SpatialReference

    ConversionUtils.gp.SetProgressor("step", "Defining projection for multiple datasets", 0, len(inDatasets))
    
    #Loop through each dataset and define projection on it.
    for dataset in inDatasets:
        try:
            ConversionUtils.gp.SetProgressorLabel("Defining projection for " + dataset) 
            #Describe input dataset to check if a projection is already defined.
            dsc_Dataset = ConversionUtils.gp.Describe(dataset)
            cs_Dataset = dsc_Dataset.SpatialReference
            #Check if a projection is already define for the input dataset.
            if cs_Dataset.Name != unknown_projection:
                ConversionUtils.gp.AddWarning(msgPrjAlreadyDefine)
            #Define the Projection
            ConversionUtils.gp.DefineProjection_management(dataset, sr)
            ConversionUtils.gp.AddMessage("Defined projection for %s successfully" % (dataset))
        except:
            #If an error set output boolean parameter "Error" to True.
            err = ConversionUtils.gp.GetMessages(2)
            ConversionUtils.gp.SetParameterAsText(3, 0)
            ConversionUtils.gp.SetParameterAsText(4, 1)
            ConversionUtils.gp.AddWarning(err)
            #ConversionUtils.gp.AddError(err)
            
        ConversionUtils.gp.SetProgressorPosition()
    
    time.sleep(0.5)

    #If output boolean parameter remains false after define projection, set Completed to True.    
    if ConversionUtils.gp.GetParameterAsText(4) == "false":
        ConversionUtils.gp.SetParameterAsText(3, 1)
            
except Exception, ErrorDesc:
    #If an error set output boolean parameter "Error" to True.
    ConversionUtils.gp.SetParameterAsText(3, 0)
    ConversionUtils.gp.SetParameterAsText(4, 1)
    ConversionUtils.gp.AddError(str(ErrorDesc))
