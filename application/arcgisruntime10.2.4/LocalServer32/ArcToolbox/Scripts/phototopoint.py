'''--------------------------------------------------------------------------------------------
Tool:               GeoTagged Photos To Points
Source Name:        phototopoint.py
Version:            ArcGIS 10.1
Author:             Esri, Inc.
Usage:              arcpy.GeoTaggedPhotosToPoints_management(Input_Folder, Output_Feature_Class, {Invalid_Photos_Table}, {Include_Non_GeoTagged_Photos}, {Add_Photos_As_Attachments})
Required Arguments: Input Folder
                    Output Feature Class
Optional Arguments: Invalid Photos Table
                    Include Non-GeoTagged Photos (ALLPHOTOS | ONLY_GEOTAGGED)
                    Add Photos As Attachments (ADD_ATTACHMENTS | NO_ATTACHMENTS)
Description:        Creates points from the X, Y, and Z coordinate information stored in geotagged photo files.
                    Optionally adds photo files to features in the Output Feature Class as geodatabase attachments.
Updated:            not yet
------------------------------------------------------------------------------------------------'''
import arcpy
import arcpy.da as da
import ExifUtils
import os
import sys

arcpy.env.overwriteOutput = True

# Create point features from Geotagged photos
def GeoPhotoToPoint(folder, fc, badphotostable="", addnongps="", attachphotos=""):
    try:
        # Convert text from boolean parameters to Python True | False
        addnongps = True if addnongps.lower() in ["true", "all_photos", ""] else False
        attachphotos = True if attachphotos.lower() in ["true", "add_attachments", ""] else False

        # Get all photo files from Input Folder
        photolist = ExifUtils.ListPhotos(folder)
        # Create outputs
        CreateOutputs(fc, badphotostable, photolist)
        foundone = 0
        incur = incurbad = None
        # Set progress bar
        arcpy.SetProgressor("step", "", 0, len(photolist), 1)

        try:
            with arcpy.da.Editor(os.path.dirname(fc)) as edit_session:
                # Open an InsertCursor to write point locations to a new feature class
                incur = da.InsertCursor(fc, ["Path", "Name", "DateTime", "SHAPE@X", "SHAPE@Y", "SHAPE@Z", "Direction"])
                # Open an InsertCursor to write a list of photos with no GPS coordinates
                incurbad = da.InsertCursor(badphotostable, ["Photo"]) if badphotostable else None
                # Get GPS information from each photo
                for file in photolist:
                    photo = ExifUtils.GetExifMetadata(file)
                    # If the photo has a valid Exif header with coordinate information
                    if (photo.x and photo.y) or addnongps:
                        # Create the point with geometry and attributes
                        incur.insertRow([photo.file, os.path.basename(photo.file), photo.m, photo.x, photo.y, photo.z, photo.d])
                        foundone = 1
                    if (not photo.x or not photo.y) and badphotostable:
                        # Write the photo path to the Invalid Photos Table output
                        incurbad.insertRow([photo.file])
                    arcpy.SetProgressorPosition()
        except:
            raise
        finally:
            if incur:
                del incur
            if incurbad:
                del incurbad

        # If none of the photos were geotagged, give the standard empty output warning
        if not foundone:
            arcpy.AddIDMessage("WARNING", 117)

        # Attach photos if option specified
        if attachphotos:
            if foundone or addnongps:
                oidfield = arcpy.Describe(fc).OIDFieldName
                arcpy.EnableAttachments_management(fc)
                arcpy.AddAttachments_management(fc, oidfield, fc, oidfield, "Path", "")
    except:
        # Delete outputs if failure occurs
        if arcpy.Exists(fc):
            arcpy.Delete_management(fc)
        if arcpy.Exists(badphotostable):
            arcpy.Delete_management(badphotostable)
        arcpy.AddIDMessage("ERROR", 999999)
        sys.exit()

def CreateOutputs(fc, badphotostable, photoslist):
    # Create the Output Feature Class
    arcpy.CreateFeatureclass_management(os.path.dirname(fc), os.path.basename(fc), "POINT", "", "", "ENABLED", "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],VERTCS['WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PARAMETER['Vertical_Shift',0.0],PARAMETER['Direction',1.0],UNIT['Meter',1.0]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119522E-09;0.001;0.001;IsHighPrecision")
    # Find the longest photo file path and name in folder
    longestpath = len(max(photoslist, key=len))
    longestname = len(max([os.path.basename(photo) for photo in photoslist], key=len))
    # Add Path, Name, and DateTime fields
    arcpy.AddField_management(fc, "Path", "TEXT", "", "", longestpath)
    arcpy.AddField_management(fc, "Name", "TEXT", "", "", longestname)
    arcpy.AddField_management(fc, "DateTime", "TEXT", "", "", 100)
    arcpy.AddField_management(fc, "Direction", "DOUBLE")
    # When creating shapefile, an unnecessary ID field is added, so delete it
    if fc.lower().find(".shp") > -1:
        arcpy.DeleteField_management(fc, "ID")

    # Create the Invalid Photos Table
    if badphotostable:
        ExifUtils.CreateBadPhotosTable(badphotostable, longestpath)

#run the script
if __name__ == '__main__':
    # Get Parameters
    folder = arcpy.GetParameterAsText(0)
    fc = arcpy.GetParameterAsText(1)
    badphotostable = arcpy.GetParameterAsText(2)
    addnongps = arcpy.GetParameterAsText(3)
    attachphotos = arcpy.GetParameterAsText(4)

    # Run the main script
    GeoPhotoToPoint(folder, fc, badphotostable, addnongps, attachphotos)
    print "finished"