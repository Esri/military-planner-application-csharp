""" *******************************************************************************************
 NAME: MultipleProject
 Source Name: Multipleproject.py
 Version: ArcGIS 9.0
 Author: Environmental Systems Research Institute Inc.
 Usage: MultipleProject <input_data>, <Output_workspace>, {output_coordinate_system}, {template_featureclass}, {transformation}
 Required Arguments: A set of input feature classes or feature layers
                     An output workspace. This can be a folder or a geodatabase.
 Optional Arguments: A Coordinate System. This is not required if a template feature class is used.
                     A template feature class. This is not required if a Coordinate System is used.
                     A geographic transformation.
 Description: Projects multiple input feature classes. The output workspace is required. This is the location where
             new feature classes are created. The names of the feature classes will be the same as in the input unless
             a feature class with that same name exists. If this is the case the name will that of the input and include
             a number (featureclass_1).
             A coordinate system can be specified by defining it manually or using the coordinate system of an
             existing feature class. Either of them must be provided.
 Date Created: 12/15/2003
 Updated: 6/02/2005 (use gp.GetParameterAsText as opposed to sys.argv)
 Updated: 9/20/2007
                 - use arcgisscripting.create(9.3)
                 - add progress bar to indicate percent of work done
                 - centralize error messages with error number
********************************************************************************************** """

#Import required modules
import ConversionUtils, time

#Define message constants so they may be translated easily
msgWorkspace = ConversionUtils.gp.GetIDMessage(86109) # Message "Output workspace does not exist: "
msgCoordinateSystem = ConversionUtils.gp.GetIDMessage(86110)  #Message "Must Enter a Spatial Reference or Template Feature Class."
msgFail =  ConversionUtils.gp.GetIDMessage(86111) # Message "Failed to project "

#Set the input datasets
inputs = ConversionUtils.gp.GetParameterAsText(0)
# The list is split by semicolons ";"
inputs = ConversionUtils.SplitMultiInputs(inputs)  

#Set the output workspace
output_workspace = ConversionUtils.gp.GetParameterAsText(1)

#Set the spatial reference
output_coordinate_system = ConversionUtils.gp.GetParameterAsText(2)

#Set the template dataset
template_dataset = ConversionUtils.gp.GetParameterAsText(3)
        
#Set the transformation
transformation = ConversionUtils.gp.GetParameterAsText(4)
#Message 86112   "Projecting multiple datasets ..."
ConversionUtils.gp.SetProgressor("step",ConversionUtils.gp.GetIDMessage(86112), 0, len(inputs))

if (output_coordinate_system == "" or output_coordinate_system == "#") and (template_dataset == "" or template_dataset == "#"):
    raise ConversionUtils.GPError(msgCoordinateSystem) 
elif (output_coordinate_system != "") and (output_coordinate_system != "#"):
    sr = output_coordinate_system
elif (template_dataset != "") and (template_dataset != "#"):
    dsc = ConversionUtils.gp.Describe(template_dataset)
    sr = dsc.SpatialReference

for input in inputs:
    try:
        outdata = ConversionUtils.GenerateOutputName(input, output_workspace)
        #Message 86113 "Projecting "
        ConversionUtils.gp.SetProgressorLabel(ConversionUtils.gp.GetIDMessage(86113) + input)        
        ConversionUtils.gp.Project_management(input, outdata, sr, transformation) 
        #Message 86114 "Projected %s to %s successfully."
        ConversionUtils.gp.AddIDMessage("INFORMATIVE", 86114, input, outdata)
        
    except Exception, ErrorDesc:
        msgWarning = msgFail + "%s" % input
        msgStr = ConversionUtils.gp.GetMessages(2)
        ConversionUtils.gp.AddWarning(ConversionUtils.ExceptionMessages(msgWarning, msgStr, ErrorDesc))
        
    ConversionUtils.gp.SetProgressorPosition()
    
time.sleep(0.5)

