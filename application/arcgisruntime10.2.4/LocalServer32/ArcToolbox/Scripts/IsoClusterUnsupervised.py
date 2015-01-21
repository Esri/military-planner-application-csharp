## ---------------------------------------------------------------------------
## IsoClusterUnsupervised.py
## Author: Environmental Systems Research Institute, Inc.
## Usage: IsoClusterUnsupervisedClassification ( <Input_raster_bands> <Number_of_classes> 
##			     <Number_of_iterations> <Minimum_class_size> <Sample_interval>
##    			 <Reject_fraction> <A_priori_probability_weighting> <Input_a_priori_probability_file>
##    			 <Output_confidence_raster> <Onput_signature_file> )
## Return Value: <Output_classified_raster>
## Description: This tool does unsupervised classification and outputs classified image directly
## ---------------------------------------------------------------------------

import sys, string, os, arcpy

# Check out spatial analyst license
arcpy.CheckOutExtension("spatial")

# Getting parameters
input_raster_bands = sys.argv[1]
number_of_classes = sys.argv[2]
output_classified_raster = sys.argv[3]
number_of_iterations = "20"
minimum_class_size = sys.argv[4]
if minimum_class_size == '#':
     minimum_class_size = "20"
sample_interval = sys.argv[5]
if sample_interval == '#':
     sample_interval = "10" 
reject_fraction = "0.0" 
a_priori_probability_weighting = "EQUAL" 
input_a_priori_probability_file = "#"
output_confidence_raster = "#"
output_signature_file = sys.argv[6]
no_signature_output = 0
out_sig_path = arcpy.GetSystemEnvironment("Temp")
if output_signature_file == '#':
	no_signature_output = 1	
	output_signature_file = out_sig_path + os.sep + "sigtmpbb9z.gsg" 

# Executing tools
try:
    overwrite_setting = arcpy.env.overwriteOutput
    if no_signature_output:
        arcpy.env.overwriteOutput = 1

    arcpy.gp.IsoCluster_sa(input_raster_bands, output_signature_file, number_of_classes, number_of_iterations, minimum_class_size, sample_interval)   
    arcpy.env.overwriteOutput = overwrite_setting

    outMLClassify = arcpy.gp.MLClassify_sa(input_raster_bands, output_signature_file, output_classified_raster, reject_fraction, a_priori_probability_weighting, input_a_priori_probability_file, output_confidence_raster)

    #Clean up temp signature file
    if no_signature_output:
         try:
              os.remove(output_signature_file)
         except:
              pass

except:
    arcpy.AddError(arcpy.GetMessages(2))
    #Message"Error in executing Iso Cluster Unsupervised Classification."
    arcpy.AddError(arcpy.GetIDMessage(86147))
