"""********************************************************************************************************************
FeatureClassConversion.py
Version: ArcGIS 10.1
 
Description: Converts or copies one or more feature classes to a GeoDatabase or folder.
The input feature classes can be shapefiles, coverage feature classes, VPF Coverage feature classes, or
Geodatabase featureclasses. Depending on which tool is calling this script, the output parameter will be a
SDE or a personal Geodatabase which means the output will be geodatabase feature classes, the output parameter
will be a folder, which means the output will be shapefiles.

The name of the output feature classes will be based on the name of the input feature class name.
If the input feature class is contained in a dataset (ie. feature dataset, coverage, CAD Dataset)
the name of the output feature class will be based on the name of the input feature class and the
dataset it contains (ie. input: covname/arc, output: covname_arc)

Author: ESRI, Redlands
                
Usage: FeatureClassToGeodatabase <in_feature_class;in_feature_class...> <out_workspace>
Usage: FeatureClassToShapefile <in_feature_class;in_feature_class...> <out_folder>
*********************************************************************************************************************"""

import ConversionUtils
import time

ConversionUtils.gp.Overwriteoutput = 1

#Define message constants so they may be translated easily
msgErrorInvalidOutPath = ConversionUtils.gp.GetIDMessage(86127) #"Output path does not exist"
msgSuccess = ConversionUtils.gp.GetIDMessage(86128) #" successfully converted to "
msgFailed = ConversionUtils.gp.GetIDMessage(86129) # "Failed to convert "

# Argument 1 is the list of feature classes to be converted
inFeatureClasses = ConversionUtils.gp.GetParameterAsText(0)

# The list is split by semicolons ";"
inFeatureClasses = ConversionUtils.SplitMultiInputs(inFeatureClasses)

# The output workspace where the shapefiles are created
outWorkspace = ConversionUtils.gp.GetParameterAsText(1)

# Set the destination workspace parameter (which is the same value as the output workspace)
# the purpose of this parameter is to allow connectivity in Model Builder.
ConversionUtils.gp.SetParameterAsText(2,outWorkspace)

# Set the progressor 
#Message "Converting multiple feature classes ..."
ConversionUtils.gp.SetProgressor("step",ConversionUtils.gp.GetIDMessage(86145) , 0, len(inFeatureClasses))

# Loop through the list of input feature classes and convert/copy each to the output geodatabase or folder
for inFeatureClass in inFeatureClasses:
    try:
        # Set the progressor label
        #Message "Converting.."
        ConversionUtils.gp.SetProgressorLabel(ConversionUtils.gp.GetIDMessage(86130) + inFeatureClass)
        
        # Generate a valid output output name
        outFeatureClass = ConversionUtils.GenerateOutputName(inFeatureClass, outWorkspace)
        
        # Copy/Convert the inFeatureClasses to the outFeatureClasses
        ConversionUtils.CopyFeatures(inFeatureClass, outFeatureClass)

        # If the Copy/Convert was successfull add a message stating this
        ConversionUtils.gp.AddMessage("%s %s %s" % (inFeatureClass, msgSuccess, outFeatureClass))

    except Exception, ErrorDesc:
        # Except block for the loop. If the tool fails to convert one of the feature classes, it will come into this block
        #  and add warnings to the messages, then proceed to attempt to convert the next input feature class.
        msgWarning = msgFailed + "%s" % inFeatureClass
        msgStr = ConversionUtils.gp.GetMessages(2)
        ConversionUtils.gp.AddWarning(ConversionUtils.ExceptionMessages(msgWarning, msgStr, ErrorDesc))

    ConversionUtils.gp.SetProgressorPosition()
    
time.sleep(0.5) 
