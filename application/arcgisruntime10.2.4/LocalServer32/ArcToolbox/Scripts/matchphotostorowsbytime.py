'''-------------------------------------------------------------------------------------------
Tool:               Match Photos To Rows By Time
Source Name:        matchphotostorowsbytime.py
Version:            ArcGIS 10.1
Author:             Esri, Inc.
Usage:              arcpy.MatchPhotosToRecordsByTime_management(Photo_Folder, Input_Records, Input_Time_Field, Output_Table, {Unmatched_Photos_Table}, {Add_Photos_As_Attachments}, {Time_Match_Tolerance}, {Time_Offset})
Required Arguments: Input Folder
                    Input Rows
                    Input Time Field
                    Output Table
Optional Arguments: Unmatched Photos Table
                    Add Photos As Attachments (ADD_ATTACHMENTS | NO_ATTACHMENTS)
                    Time Tolerance
                    Clock Offset
Description:        Matches photo files to table or feature class records according to the capture time of the photo
                    and the timestamp of the record. Creates a new table containing the OBJECTIDs from the Input
                    Records and the matching photo path. Optionally adds matching photo files to the Input Records
                    as geodatabase attachments.
Updated:            not yet
----------------------------------------------------------------------------------------------'''
import arcpy
import arcpy.da as da
import ExifUtils
import os
import datetime
import time

arcpy.env.overwriteOutput = True

# Match Photos to Rows based on timestamp
def MatchPhotos2Rows(folder, fc, timefield, outtable, badphotostable="", attachphotos="", timetol=0, offset=0):
    try:
        # Convert text from boolean parameters to Python True | False
        attachphotos = True if attachphotos.lower() in ["true", "add_attachments", ""] else False

        oidfield = arcpy.Describe(fc).OIDFieldName
        dict = {}
        # Create dictionary of timestamps in Input Table
        for row in da.SearchCursor(fc, [oidfield, timefield]):
            dict[row[0]] = row[1]

        # Get all photo files from Input Folder
        photolist = ExifUtils.ListPhotos(folder)

        # Create outputs
        CreateOutputs(outtable, badphotostable, photolist)
        foundone = 0
        icur = incurbad = None
        # Set progress bar
        arcpy.SetProgressor("step", "", 0, len(photolist), 1)

        try:
            with arcpy.da.Editor(os.path.dirname(outtable)) as edit_session:
                # Open an InsertCursor to write matches to the Output Table
                icur = da.InsertCursor(outtable, ["IN_FID", "Photo_Path", "Photo_Name", "Match_Diff"])
                # Open an InsertCursor to write a list of non-matching photos
                incurbad = da.InsertCursor(badphotostable, ["Photo"]) if badphotostable else None
                # Get DateTime information from each photo
                for file in photolist:
                    photo = ExifUtils.GetExifMetadata(file)
                    # If the photo has a valid Exif header with DateTime information
                    if photo.m:
                        # Turn timestamp string into a Python datetime class
                        photo.m = datetime.datetime.fromtimestamp(time.mktime(time.strptime(photo.m, '%Y:%m:%d %H:%M:%S')))
                        # If a time offset was specified, change the photo timestamp
                        if offset:
                            photo.m += datetime.timedelta(seconds=offset)
                        # Find a match for this DateTime
                        closestID = ClosestTime(photo.m, dict.items())
                        # Determine if the time difference between this photo and row is within the tolerance
                        closestDif = abs(dict[closestID] - photo.m).total_seconds()
                        # If the difference is within the tolerance, make a match by writing an output row
                        if closestDif <= timetol or timetol == 0:
                            icur.insertRow([closestID, photo.file, os.path.basename(photo.file), closestDif])
                            foundone = 1
                        else:
                            # Write the photo path to the Unmatched Photos Table
                            if badphotostable:
                                incurbad.insertRow([photo.file])
                    else:
                        # Write the photo path to the Unmatched Photos Table
                        if badphotostable:
                            incurbad.insertRow([photo.file])
                    arcpy.SetProgressorPosition()
        except:
            raise
        finally:
            if icur:
                del icur
            if incurbad:
                del incurbad

        # Attach photos if option specified
        if attachphotos:
            arcpy.EnableAttachments_management(fc)
            arcpy.AddAttachments_management(fc, oidfield, outtable, "IN_FID", "Photo_Path", "")

        # If none of the photos were matched give the standard empty output warning
        if not foundone:
            arcpy.AddIDMessage("WARNING", 117)
    except:
        if arcpy.Exists(outtable):
            arcpy.Delete_management(outtable)
        if arcpy.Exists(badphotostable):
            arcpy.Delete_management(badphotostable)
        arcpy.AddIDMessage("ERROR", 999999)
        sys.exit()

def ClosestTime(target, collection):
    # return the Input Row ID with the closest timestamp to a given photo
    return min((abs(target - i[1]), i[0]) for i in collection)[1]

def CreateOutputs(outtable, badphotostable, photoslist):
    # Create the output table
    arcpy.CreateTable_management(os.path.dirname(outtable), os.path.basename(outtable))
    # Find the longest photo file path and name in folder
    longestpath = len(max(photoslist, key=len))
    longestname = len(max([os.path.basename(photo) for photo in photoslist], key=len))
    # Add IN_FID, Path, Name, and Match Difference fields
    arcpy.AddField_management(outtable, "IN_FID", "LONG")
    arcpy.AddField_management(outtable, "Photo_Path", "TEXT", "", "", longestpath)
    arcpy.AddField_management(outtable, "Photo_Name", "TEXT", "", "", longestname)
    arcpy.AddField_management(outtable, "Match_Diff", "DOUBLE")
    # Delete Field1 field if outtable is a dbf
    if outtable.lower().find(".dbf") > -1:
        arcpy.DeleteField_management(outtable, "Field1")

    # Create the Invalid Photos Table
    if badphotostable:
        ExifUtils.CreateBadPhotosTable(badphotostable, longestpath)

#run the script
if __name__ == '__main__':
    # Get Parameters
    folder = arcpy.GetParameterAsText(0)
    fc = arcpy.GetParameterAsText(1)
    timefield = arcpy.GetParameterAsText(2)
    outtable = arcpy.GetParameterAsText(3)
    badphotostable = arcpy.GetParameterAsText(4)
    attachphotos = arcpy.GetParameterAsText(5)
    timetol = abs(arcpy.GetParameter(6))
    offset = arcpy.GetParameter(7)

    # Run the main script
    MatchPhotos2Rows(folder, fc, timefield, outtable, badphotostable, attachphotos, timetol, offset)
    print "finished"