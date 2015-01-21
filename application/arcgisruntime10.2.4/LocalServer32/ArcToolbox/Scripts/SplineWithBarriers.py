'''----------------------------------------------------------------------------
 Tool Name:     SplineWithBarriers
 Source Name:   SplineWithBarriers.py
 Version:       ArcGIS 10.0
 Author:        Environmental Systems Research Institute Inc.
 Required Argumuments:  An input point feature class or feature layer
                        An input Z field
                        An input barrier feature class or feature layer
                        An output cell size
                        An output raster dataset
                        An optional smoothing factor
 Description:   Creates a surface from the input points, incorporating barriers.
----------------------------------------------------------------------------'''
import string, os, sys, locale, arcgisscripting, struct
import numpy
import subprocess, platform

gp = arcgisscripting.create()

# Hard coded limits==========================
# The current release of ArcObjects for Java requires
# that users have at least Java 6 installed
JavaVersionNumber =  "1.6.0"
# This software has been tested to create a raster of size ncols x nrows
# However, these values depend on how much memory the Java VM has available
# It is not recommended to change these values
largestOutputSize = 16500 * 16500
# End of hard coded limits===================

#Error and warning messages=================
msgJavaNotInstalled = gp.GetIDMessage(86158)
#"Java is not installed, please see the usage tip in the tool's help for more information."
msgNotEnoughParams = gp.GetIDMessage(86159) 
#"Incorrect number of input parameters."
msgUseValidCellSize = gp.GetIDMessage(86160)
# "Please use a valid cell size."
msgUseValidSmoothFactor = gp.GetIDMessage(86161) 
#"Please use a valid smoothing factor."
msgInvalidPointInput = gp.GetIDMessage(86162) 
#"The first parameter must contain point features"
msgInvalidBarriers = gp.GetIDMessage(86163) 
#"Barriers must be either lines or polygons."
msgInvalidZField = gp.GetIDMessage(86164) 
#"The Shape field does not contain Z Values"
msgOutputTooBig = gp.GetIDMessage(86165) 
#"Output raster has too many cells. Decrease the extent or increase the cell size."
msgNoDataGridFromJava = gp.GetIDMessage(86166) 
#"A problem has been encountered. Please verify that the inputs are correct."
msgJMCunsuccessful = gp.GetIDMessage(86167) 
#"Spline with Barriers failed"
msgNoLicenseAvailable = gp.GetIDMessage(86168) 
#"Spatial Analyst or 3D license required"
msgCurrentJavaVersion = gp.GetIDMessage(86169) % JavaVersionNumber 
#"Java " + JavaVersionNumber + " required." + "\n" + 
# "Please see the usage tip in the tool's help for more information."
msgNumberOfNullValues = gp.GetIDMessage(86170) 
#"Null value(s) in the input data and will be are ignored."
#End of error and warning messages==========

platformName = platform.system()
if platform.system() == "Microsoft":
    platformName = "Windows"

classpathsep = ';'
quotestr = r'"'
if not platformName == "Windows" or os.getenv("WINEPREFIX"):
    classpathsep = ':'
    quotestr = r"'"

def ListToString(list):
    x = len(list)
    outStr = ""
    y = 0
    while y < x:
        outStr = outStr + " " + list[y]
        y +=1
    return outStr

def launchWithoutConsole(command, args):
    """Launches 'command' windowless and waits until finished"""

    #Set up params
    if platformName == "Windows": #Windows or Server on Linux
        import _subprocess
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
        shellValue = False
    else:
        startupinfo = None
        shellValue = True

    #Launch it
    if not os.getenv("WINEPREFIX"): #Anything not Server on Linux
        return subprocess.Popen(command + " " + args, startupinfo=startupinfo, shell=shellValue).wait()
    else: #Server on Linux
        shellcmd = "cmd.exe /c /bin/sh -c"
        proccmd = command
        argslist = args.split()
        for arg in argslist:
            if os.path.isabs(arg):
                proccmd += " " + "'" + pathToWinePath(arg) + "'"
            else:
                proccmd += " " + arg
        fullcmd = shellcmd + " \"" + proccmd + ";echo $?\""
        proc = subprocess.Popen(fullcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, shell=shellValue)
        (stdout, stderr) = proc.communicate()
        returncode = int(stdout.split('\n')[-2].rstrip())
        return returncode


def GetInstallValues():
    # Determines where arcobjects.jar, JMCTool.jar, and the
    #   Java runtime executable can be found
    #
    prodName = gp.GetInstallInfo()['ProductName']
    if prodName == 'Desktop':
        prodHome = gp.GetSystemEnvironment("AGSDESKTOPJAVA")
        aoJar = os.path.join(prodHome, "java", "lib", "arcobjects.jar")
        javaBinary = os.path.join(prodHome, "java", "jre", "bin", "java.exe")
    elif prodName == 'Engine':
        prodHome = gp.GetSystemEnvironment("AGSENGINEJAVA")
        aoJar = os.path.join(prodHome, "java", "lib", "arcobjects.jar")
        #First look in JAVA_HOME/bin and JAVA_HOME/jre/bin
        # Otherwise expect it in the path.
        javaBinary = "java"
        if platformName == "Windows":
            javaExeName = "java.exe"
        else:
            javaExeName = "java"
        #
        jDir = gp.GetSystemEnvironment("JAVA_HOME")
        if not jDir == '':
            javaBinaryTemp = os.path.join(jDir, "bin", javaExeName)
            if os.path.exists(javaBinaryTemp):
                javaBinary = javaBinaryTemp
            else:
                javaBinaryTemp = os.path.join(jDir, "jre", "bin", javaExeName)
                if os.path.exists(javaBinaryTemp):
                    javaBinary = javaBinaryTemp
    elif prodName == 'Server':
        prodHome = gp.GetSystemEnvironment("AGSSERVER")
        aoJar = os.path.join(prodHome, "framework", "lib", "arcobjects.jar")
        if platformName == "Windows" and not os.getenv("WINEPREFIX"):
            # On Windows
            javaBinary = prodHome + "\\framework\\runtime\\jre\\bin\\java.exe"
        else:
            # In Wine on Linux
            javaBinary = prodHome + "/framework/runtime/jre/bin/java"
    else:
        raise Exception, 'NoArcGISProductInstalledError'
    #
    jmcJar = os.path.join(prodHome, "ArcToolbox", "Scripts", "JMCTool.jar")
    if os.getenv("WINEPREFIX"):
        aoJar = pathToWinePath(aoJar)
        jmcJar = pathToWinePath(jmcJar)
    return (aoJar, jmcJar, javaBinary)


def pathToWinePath(wine_winpath):
    import subprocess
    p1 = subprocess.Popen("/bin/sh -c \"winepath -u '" + wine_winpath + "'\"", stdout=subprocess.PIPE)
    winepath = p1.stdout.read()
    winepath = winepath.rstrip()
    p2 = subprocess.Popen("/bin/sh -c \"readlink -f '" + winepath + "'\"", stdout=subprocess.PIPE)
    nixpath = p2.stdout.read()
    return nixpath.rstrip()

gp.overwriteoutput = 1
# The progress bar will print messages for
#    Verifying Java version
#    Reading input features
#    Interpolating ...
#    Writing output ...
#Message "Verifying Java version"
gp.SetProgressorLabel(gp.GetIDMessage(86171))     
try:

    (arcobjectsJar, jmcJarfile, javaExe) = GetInstallValues()

    try:
        JavaNotInstalled = launchWithoutConsole(javaExe, "-version")
    except Exception, ErrorDesc:
        raise Exception, msgJavaNotInstalled          

    if JavaNotInstalled == 1:
           raise Exception, msgJavaNotInstalled          
    
    javaHeapSpace = "-Xmx512m -Xss2m" #stack size added at 9.3 for Linux

    
    # need java version JavaVersionNumber or higher to run
    #
    # The wierd extra doublequotes in here ( r'"' ) handle the case where
    #  ArcGIS is installed in a path with spaces in it.
    versionArgs = []
    versionArgs.append(r"-cp")
    versionArgs.append(quotestr + arcobjectsJar + quotestr + classpathsep + quotestr + jmcJarfile + quotestr)
    versionArgs.append(r"com.esri.asmutils.VersionTest")
    versionArgs.append(str(JavaVersionNumber))
    #gp.AddMessage("java runtime: "+javaExe)
    CurrentJavaVersion = launchWithoutConsole(javaExe,ListToString(versionArgs))
    if CurrentJavaVersion <> 0:
           raise Exception,  msgCurrentJavaVersion          

    if sys.argv.count < 4: raise Exception, msgNotEnoughParams
    inputs = gp.GetParameterAsText(0)
    ZField = gp.GetParameterAsText(1)
    barriers = gp.GetParameterAsText(2)
    if not barriers:
        barrierExist = False
    else:
        barrierExist = True
        
    cellSizeString = gp.GetParameterAsText(3)
    if len(cellSizeString) ==0:
        cellSizeString="0"
    outRaster = gp.GetParameterAsText(4)
    smoothFactor = gp.GetParameterAsText(5)
    try:
        cellSize = locale.atof(cellSizeString)
    except:
        msgUseValidCellSize
    
    try:
        smoothFactor = float(smoothFactor)
    except:
        msgUseValidSmoothFactor
    
    if smoothFactor < 0: raise Exception, msgUseValidSmoothFactor    

    # Set the location of the temporary file that will be produced. Use the
    # scratch workspace if set to a folder, otherwise use the TEMP folder.
    scratchWS = gp.scratchWorkspace
    currentWS = gp.workspace
    if scratchWS:
        desc = gp.Describe(scratchWS)
        if desc.WorkspaceType <> "FileSystem":
            scratchWS = gp.GetSystemEnvironment("TEMP")
    else:
        scratchWS = gp.GetSystemEnvironment("TEMP")    
# two input feature classes are exported to two binary files called xx....
# in the scratch workspace. Temp grid is called xxg... also in the scratch
# workspace. All temp output is deleted at the end.
    #Message "Reading input features"
    gp.SetProgressorLabel(gp.GetIDMessage(86172))
    
    pntFileName = gp.CreateScratchName("xx", "", "file", scratchWS)
    tmpGrid = gp.CreateScratchName("xxg", "", "grid", scratchWS)
    
    numberPoints = 0
    xleft = (1.0e400)
    xright = -xleft
    ybot = xleft
    ytop = -ybot

    outPntFile = open(pntFileName, "wb")
    inDesc = gp.describe(inputs)
    SRinputPts = inDesc.spatialreference
    # Check inputs to make sure they are points / multipoints
    if str(inDesc.ShapeType).lower() <> "point":
        if str(inDesc.Shapetype).lower() <> "multipoint":  #CR77163
            raise Exception, msgInvalidPointInput          

    # Check barriers to make sure they are lines or polygons
    if barrierExist:
        barDesc = gp.Describe(barriers)
        if str(barDesc.Shapetype).lower() == "point" or str(barDesc.Shapetype).lower() == "multipoint" \
           or str(barDesc.Shapetype).lower() == "multipatch":
            raise Exception, msgInvalidBarriers        
    
    # Write out points

    if not inDesc.HasZ:
           if ZField.lower() == "shape":
              raise Exception, msgInvalidZField        
               
    inPntRows = gp.searchcursor(inputs)
    inRow = inPntRows.Next()
    nullCount = 0
    if inDesc.ShapeType.lower() == "point":        
        while inRow:
            feat = inRow.GetValue(inDesc.ShapeFieldName)
            nullFlag = 0
            pnt = feat.getpart()
            if ZField.lower() <> "shape":
                nullCheck = str(inRow.getvalue(ZField))
                if nullCheck.lower() <> "none":
                    zvalue = inRow.getvalue(ZField)
                else:
                    nullFlag = 1
                    nullCount = nullCount + 1
            else:
                zvalue = pnt.z
#           d = 64 bit float (double precision), f = 32 bit float
            if nullFlag == 0:
                outLine = struct.pack('!ddd',pnt.x,pnt.y,zvalue)
                xleft = min(xleft, pnt.x)
                xright = max(xright, pnt.x)
                ybot = min(ybot, pnt.y)
                ytop = max(ytop, pnt.y)
                outPntFile.write(outLine)
                numberPoints = numberPoints +1
            inRow = inPntRows.Next()
    elif inDesc.ShapeType.lower() == "multipoint":  #CR77163
        while inRow:
            feat = inRow.GetValue(inDesc.ShapeFieldName)
            nullFlag = 0
            pnt = feat.getpart()
            partnum = 0
            partcount = feat.partcount
            while partnum < partcount:
                pnt = feat.getpart(partnum)
                if str(ZField) <> "Shape":
                    zvalue = inRow.getvalue(ZField)
                else:
                    zvalue = pnt.z
                outLine = struct.pack('!ddd',pnt.x,pnt.y,zvalue)
                xleft = min(xleft, pnt.x)
                xright = max(xright, pnt.x)
                ybot = min(ybot, pnt.y)
                ytop = max(ytop, pnt.y)
                outPntFile.write(outLine)
                numberPoints = numberPoints +1
                partnum += 1   
            inRow = inPntRows.Next()
    if nullCount <> 0:
        gp.AddMessage(str(nullCount) + " " + msgNumberOfNullValues)
    outPntFile.flush()
    outPntFile.close()
    xleft_pts = xleft
    xright_pts = xright
    ybot_pts = ybot
    ytop_pts = ytop
    xleft = (1.0e400)
    xright = -xleft
    ybot = xleft
    ytop = -ybot

    
    # Write out barriers
    barFileName = gp.CreateScratchName("xx", "", "file", scratchWS)
    outBarFile = open(barFileName, "wb")
    
    if barrierExist:
        inBarRows = gp.searchcursor(barriers,"",SRinputPts)
        inRow = inBarRows.Next()    
        numberVertices = 0
        lineID = 1
        while inRow:
            partnum = 0
            feat = inRow.GetValue(barDesc.ShapeFieldName) # CR39403 replaced inDesc with barDesc
            partcount = feat.partcount
            while partnum < partcount:
                part = feat.getpart(partnum)
                part.reset()
                pnt = part.next()
                pnt_count = 0
                while pnt:
                    outLine = struct.pack('!ddi',pnt.x,pnt.y,int(lineID))
                    xleft = min(xleft, pnt.x)
                    xright = max(xright, pnt.x)
                    ybot = min(ybot, pnt.y)
                    ytop = max(ytop, pnt.y)
                    outBarFile.write(outLine)
                    numberVertices = numberVertices + 1
                    pnt = part.next()
                    pnt_count += 1
                    if not pnt:
                        lineID = lineID + 1
                        pnt = part.next()
                partnum += 1
                lineID = lineID + 1
            inRow = inBarRows.Next()
        outBarFile.flush()
        outBarFile.close()
        xleft_br = xleft
        xright_br = xright
        ybot_br = ybot
        ytop_br = ytop
    else:
        smallDelta = 0.00000001
        outLine = struct.pack('!ddi',xleft_pts, ybot_pts, 0)
        outBarFile.write(outLine)
        outLine = struct.pack('!ddi',xleft_pts + smallDelta, ybot_pts + smallDelta, 0)
        outBarFile.write(outLine)
        numberVertices = 2
        outBarFile.flush()
        outBarFile.close()
        xleft_br = xleft_pts
        xright_br = xright_pts
        ybot_br = ybot_pts
        ytop_br = ytop_pts

# if no extent is set in the Environment, then use MAXOF
    if str(gp.Extent).lower() == "none":
        xleft = min(xleft_pts, xleft_br)
        xright = max(xright_pts, xright_br)
        ybot = min(ybot_pts, ybot_br)
        ytop = max(ytop_pts, ytop_br)
    elif str(gp.Extent).lower() == "maxof":
        xleft = min(xleft_pts, xleft_br)
        xright = max(xright_pts, xright_br)
        ybot = min(ybot_pts, ybot_br)
        ytop = max(ytop_pts, ytop_br)
    elif str(gp.Extent).lower() == "minof":
        xleft = max(xleft_pts, xleft_br)
        xright = min(xright_pts, xright_br)
        ybot = max(ybot_pts, ybot_br)
        ytop = min(ytop_pts, ytop_br)
    else:
        EnvExt = str(gp.Extent).split(" ")
        xleft = float(EnvExt[0])
        xright = float(EnvExt[2])
        ybot = float(EnvExt[1])
        ytop = float(EnvExt[3])
# - (String) full path and name of points binary file - pntFileName
# - (int) # points in the points binary file - numberPoints
# - (String) full path and name of lines binary file - barFileName
# - (int) # vertices in the lines binary file - numberVertices
# - (String) full path and name of the output grid (must be in a file workspace) - tmpGrid
# - (double) cellsize - cellSize
# - (double) xmin - xleft
# - (double) ymin - xright
# - (double) xmax - ybot
# - (double) ymax - ytop
# - (double or float) smooting factor - smoothFactor
# - (boolean) xsort
    xsort = bool(0) 
# - (int) startPaneling
    startPaneling = 11

    y_extent = (ytop - ybot)
    x_extent = (xright - xleft)
# If a zero cell size is given, then calc a default one
#    if len(str(cellSize)) <= 0: # CR48800 see next line for change
    if cellSizeString == "0":   
        cellSize = min(x_extent, y_extent)/250.0
        #Message "Default cell size = "
        gp.AddMessage(gp.GetIDMessage(86173) + str(cellSize))
     
# This software has been tested to create a raster of size ncols x nrows
# However, these values depend on the amount of memory that the Java VM has available
# It is not recommended to change these values
    ncols = int(((xright - xleft) / cellSize) + 1.0) + 1
    nrows = int(((ytop - ybot) / cellSize) + 1.0) + 1
    if ncols * nrows > largestOutputSize: raise Exception, msgOutputTooBig
# Convert the AOI to double which is required by the java routine
    double_AOI = struct.pack("!dddd", xleft, ybot, xright, ytop)
    double_AOI2 = struct.unpack("!dddd",double_AOI)
    tmpStr = str(double_AOI2)
    strdouble_AOI2 = tmpStr[1:len(tmpStr)-1].split(",")

# Build up the command line that runs the java faulted gridding routine    
    SplineWithBarriersArgs = []
    SplineWithBarriersArgs.append(javaHeapSpace)
    SplineWithBarriersArgs.append(r"-cp")
    SplineWithBarriersArgs.append(quotestr + arcobjectsJar + quotestr + classpathsep + \
                             quotestr + jmcJarfile + quotestr)
    SplineWithBarriersArgs.append(r"com.esri.asmutils.JMCTool")
    SplineWithBarriersArgs.append(pntFileName)
    SplineWithBarriersArgs.append(str(numberPoints))
    SplineWithBarriersArgs.append(barFileName)
    SplineWithBarriersArgs.append(str(numberVertices))
    SplineWithBarriersArgs.append(tmpGrid)
    SplineWithBarriersArgs.append(str(cellSize))
    SplineWithBarriersArgs.append(strdouble_AOI2[0])
    SplineWithBarriersArgs.append(strdouble_AOI2[1])
    SplineWithBarriersArgs.append(strdouble_AOI2[2])
    SplineWithBarriersArgs.append(strdouble_AOI2[3])
    SplineWithBarriersArgs.append(str(smoothFactor))
    SplineWithBarriersArgs.append(str(xsort))
    SplineWithBarriersArgs.append(str(startPaneling))
# This is the main faulted gridding algorithm
#Message "Interpolating ..."
    gp.SetProgressorLabel(gp.GetIDMessage(86192))
    SwBsuccessful = launchWithoutConsole(javaExe, ListToString(SplineWithBarriersArgs))
# A return of zero indicates success in the java routine
# A return = 1 might include, no SA or 3D license available
#Message "Writing output ..."
    gp.SetProgressorLabel(gp.GetIDMessage(86174))
    if SwBsuccessful == 0:
       tmpGridMin = gp.GetRasterProperties_management(tmpGrid, "MINIMUM")
       if tmpGridMin > 1.7E308:
           gp.AddMessage(ListToString(SplineWithBarriersArgs))
           gp.Delete_management(pntFileName)
           gp.Delete_management(barFileName)
           gp.Delete_management(tmpGrid)
           raise Exception, msgNoDataGridFromJava          
    if SwBsuccessful <> 0:
           gp.Delete_management(pntFileName)
           gp.Delete_management(barFileName)
#       test if it failed because of a license issue
           SA_ext = gp.CheckExtension("spatial")
           DDD_ext = gp.CheckExtension("3d")
           if SA_ext.lower() == "available":
                 checkLicense = "spatial"
           elif DDD_ext.lower() == "available":
                 checkLicense = "3d"
           else:
                 msgJMCunsuccessful = msgNoLicenseAvailable
           raise Exception, msgJMCunsuccessful          
        
# The output grid is coulmn major and it has to be row major.
# Rotate, 270 degrees and the pivot point = xmin + half y extent; ymin + half y extent
    PivotPointx = xleft + (x_extent/2.0)
    PivotPointy = ybot + (x_extent/2.0)
    PivotPoint = str(PivotPointx) + r" " + str(PivotPointy)

    if SwBsuccessful == 0:
         gp.outputCoordinateSystem = SRinputPts
         gp.Rotate_management(tmpGrid, outRaster, "270" ,PivotPoint, "NEAREST")
      
# Delete scratch files
    gp.ResetProgressor()
    if SwBsuccessful == 0:
         gp.Delete_management(tmpGrid)
    gp.Delete_management(pntFileName)
    gp.Delete_management(barFileName)
  
except Exception, ErrorDesc:
    gp.AddError(ErrorDesc[0])
##    if outPntFile: outPntFile.close()
##    if outBarFile: outBarFile.close()
    gp.ResetProgressor()
    gp.AddError(gp.getmessages(2))
    
