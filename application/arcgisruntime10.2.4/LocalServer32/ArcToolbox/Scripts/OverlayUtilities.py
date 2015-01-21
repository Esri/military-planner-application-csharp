"""********************************************************************************************************************
OverlayUtilities.py

Description: CheckResources determines whether a potential overlay operation will require the use of standard overlay
tools in the Analysis toolbox or the use of overlay tools in the Large Overlay toolbox.

CreatePartitionFeatureClass creates a partitioned shapefile that can be used to break your features into smaller
feature classes that are processable by your system.

Requirements: The first argument must be a semi-colon separated list of feature classes.

Author: ESRI, Redlands

Date: 7/26/2004

Usage: CheckResources <Input_Features;Input_Features...> {MAX | MIN}
Usage: CreatePartitionFeatureClass <Input_Features;Input_Features...> <Output_Shapefile> {MAX | MIN}
*********************************************************************************************************************"""

#Import required modules
import win32com.client, win32api, sys, os

#Create the Geoprocessor Object
GP = win32com.client.Dispatch("esriGeoprocessing.GPDispatch.1")

#Set overwriteoutput to on
GP.Overwriteoutput = 1

#Define message constants so they may be translated easily
msgErrorTooFewParams = "Insufficient number of parameters provided"
msgErrorSplittingInput = "Problem encountered parse input list"

def SplitMultiInputs(multiInputs):
    try:
        #Remove the single quotes and parathesis around each input featureclass
        multiInputs = multiInputs.replace("(","").replace(")","").replace("'","")

        #split input tables by semicolon ";"
        return multiInputs.split(";")
    except:
        raise Exception, msgErrorSplittingInput

try:
    # To run as CheckResources, requires 2 + 2 (derived boolean) + 1 (python also passes the name
    # of the py file) = 5 arguments
    # To run as CreatePartitionFeatureClass, requires 3 + 1 arguments

    optionlist = ['MAX','MIN']

    if len(sys.argv) < 5 and optionlist.count(str(sys.argv[2]).upper()) == 1:
        raise Exception, msgErrorTooFewParams
    if len(sys.argv) < 4 and optionlist.count(str(sys.argv[2]).upper()) == 0:
        raise Exception, msgErrorTooFewParams

    # Use location to assume folder of executable
    location = os.path.dirname(sys.argv[0])

    # Format string of inputs
    inputs = sys.argv[1]
    inputlist = SplitMultiInputs(inputs)
    inputs = ""
    for input in inputlist:
        inputs = inputs + ";" + "\"" + input + "\""
    inputs = inputs[1:]

    # Acquire options for CheckResources
    if optionlist.count(str(sys.argv[2]).upper()) == 1:
        option = "TEST"
        extent = str(sys.argv[2]).upper()
    # Acquire options for CreatePartitionFeatureClass    
    else:
        option = "TILE"
        output = sys.argv[2]
        extent = str(sys.argv[3]).upper()
        
    # Determine scratch workspace to use for file messages
    scratchWS = GP.scratchWorkspace
    if scratchWS:
        desc = GP.Describe(scratchWS)
        if desc.WorkspaceType <> "FileSystem":
            scratchWS = win32api.GetEnvironmentVariable("TEMP")         
    else:
        scratchWS = win32api.GetEnvironmentVariable("TEMP")

    messagetarget = scratchWS + "/xxxResources.txt"

    # Execute for CheckResources
    if option == "TEST":
        os.system(location + "/testgpram.exe" + " " + inputs + " " + option + " " + messagetarget + " " + extent)
    # Execute for CreatePartitionFeatureClass
    else:
        os.system(location + "/testgpram.exe" + " " + inputs + " " + option + " " + "\"" + output + "\"" + " " + extent + " " + messagetarget)

    # Return GP Messages
    messagefile = open(messagetarget, 'r')
    messagestring = messagefile.read()
    # Messages for CheckResources
    if option == "TEST":
        L = []
        for i in messagestring.split(","):
            L.append(i)
        if L[0][:4] == "PASS":
            GP.AddMessage("These dataset(s) will be successfully overlayed using normal overlay tools.")
            # Return true for normal overlay tools
            GP.SetParameterAsText(2, "true")
            GP.SetParameterAsText(3, "false")
        if L[0][:4] == "FAIL":
            GP.AddWarning("These dataset(s) should be used with the tools in the Large Overlay Tools toolbox.")
            # Return true for large overlay tools
            GP.SetParameterAsText(3, "true")
            GP.SetParameterAsText(2, "false")
        GP.AddMessage("The input dataset(s) contain " + L[1] + " segments.")
        GP.AddMessage("There are " + L[2][:-1] + " bytes of available virtual memory.")
    # Messages for CreatePartitionFeatureClass
    if option == "TILE":
        GP.AddMessage(messagestring[:-1])

except Exception, ErrorDesc:
    # Except block if the tool could not run at all.
    # For example, not all parameters are provided, or if the output path doesn't exist.
    GP.AddError(str(ErrorDesc))
    print str(ErrorDesc)
