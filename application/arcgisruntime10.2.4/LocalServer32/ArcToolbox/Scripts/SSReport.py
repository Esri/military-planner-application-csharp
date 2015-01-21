"""
Source Name:   SSReport.py
Version:       ArcGIS 10.1
Author:        Environmental Systems Research Institute Inc.
Description:   Reporting Functions for ESRI Script Tools as well as users for their own
               scripts.
"""

################### Imports ########################
import os as OS
import arcpy as ARCPY
import ErrorUtils as ERROR
import locale as LOCALE
import SSDataObject as SSDO
import SSUtilities as UTILS
import xml.etree.ElementTree as ET
import pylab as PYLAB
import matplotlib.pyplot as PLT
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_pdf import PdfPages as PDF

#### Set Locale for Matplotlib Axis Labels ####
PYLAB.rcParams['axes.formatter.use_locale'] = True

#################### MatplotLib Constants #########################

#### Text Allignment ####

cAlignment = {'verticalalignment':'center'}
bAlignment = {'verticalalignment':'top'}

################## Set/Create Font Information ####################

def createFont(family = None, style = None, variant = None, weight = None, 
               stretch = None, size = None, fontFilePathName = None):
    """Returns a Font Object for text in Matplotlib."""

    #### Copy Global Font Properties ####
    if fontFilePathName:
        try:
            font0 = FontProperties(fname = fontFilePathName)
        except:
            font0 = FontProperties()
    else:
        font0 = FontProperties()
    font = font0.copy()

    #### Adjust Based on Arguments ####
    if family != None:
        font.set_family(family)
    if style != None:
        font.set_style(style)
    if variant != None:
        font.set_variant(variant)
    if weight != None:
        font.set_weight(weight)
    if stretch != None:
        font.set_stretch(stretch)
    if size != None:
        font.set_size(size)

    return font

############### Examples of Setting Local Fonts #################

#### English, French, German, Italian, Spanish ####
#### Set Default to None, Base Font Should Work ####
fontFilePathName = None
fontFileBoldName = None

################# Chinese/Japanese* #################

#### Windows 7 / Windows Vista (Microsoft YaHei) ####
#### Uncomment the Following Two Lines ####
#fontFilePathName = r'C:\Windows\Fonts\msyh.ttf'
#fontFileBoldName = r'C:\Windows\Fonts\msyhbd.ttf'
#### * Japanese requires a font decrease by two.  See below * ####

#### Linux (UMING) ####
#### Uncomment the Following Two Lines ####
#fontFilePathName = '/usr/share/fonts/chinese/TrueType/uming.ttf'
#fontFileBoldName = '/usr/share/fonts/chinese/TrueType/uming.ttf'

####################################################

################### Russian #######################

#### Windows 7 / Windows Vista (Arial) ####
#### Uncomment the Following Two Lines ####
#fontFilePathName = r'C:\Windows\Fonts\arial.ttf'
#fontFileBoldName = r'C:\Windows\Fonts\arial.ttf'

#### Linux (DejaVu Sans) ####
#### Uncomment the Following Two Lines ####
#fontFilePathName = '/usr/share/fonts/dejavu-lgc/DejaVuLGCSans.ttf'
#fontFileBoldName = '/usr/share/fonts/dejavu-lgc/DejaVuLGCSans.ttf'

####################################################

#### Create Spatial Stats PDF Fonts ####
ssFont = createFont(fontFilePathName = fontFilePathName,
                    size = 10)
ssBoldFont = createFont(fontFilePathName = fontFileBoldName,
                        weight = 'semibold', size = 10)
ssBigFont = createFont(fontFilePathName = fontFilePathName,
                       size = 12)
ssSmallFont = createFont(fontFilePathName = fontFilePathName,
                         size = 8)
ssLabFont = createFont(fontFilePathName = fontFileBoldName,
                       weight = 'semibold', size = 12)
ssTitleFont = createFont(fontFilePathName = fontFileBoldName,
                         weight = 'semibold', size = 14)

#### * Special Font Decrease for Japanese * ####
#ssFont = createFont(fontFilePathName = fontFilePathName,
#                    size = 8)
#ssBoldFont = createFont(fontFilePathName = fontFileBoldName,
#                        weight = 'semibold', size = 8) 
#ssBigFont = createFont(fontFilePathName = fontFilePathName,
#                       size = 10)
#ssSmallFont = createFont(fontFilePathName = fontFilePathName,
#		                  size = 6)
#ssLabFont = createFont(fontFilePathName = fontFileBoldName,
#                       weight = 'semibold', size = 10) 
#ssTitleFont = createFont(fontFilePathName = fontFileBoldName,
#                         weight = 'semibold', size = 12)

##########################################################

################### Matplotlib Functions ##########################

def openPDF(fileName):
    """Wraps the PDF Output File Pointer with ArcGIS an ArcGIS Error.

    INPUTS:
    fileName (str): path to the output file

    RETURN:
    output PDF file pointer
    """

    try:
        return PDF(fileName)
    except:
        ARCPY.AddIDMessage("ERROR", 210, fileName)
        raise SystemExit()

################### Matplotlib Classes ############################

class ReportPage(object):
    def __init__(self, title = "", landscape = True, titleFontSize = 12,
                 titleFont = None):
        self.title = title
        self.landscape = landscape
        self.titleFontSize = titleFontSize
        self.titleFont = titleFont
        self.construct()

    def construct(self):
        if self.landscape:
            fig = PLT.figure(figsize=(11, 8.5))
            self.numRows = 20
        else:
            fig = PLT.figure(figsize=(8.5, 11))
            self.numRows = 28
        fig.canvas.set_window_title(self.title)
        if self.titleFont:
            PLT.suptitle(self.title, fontproperties = self.titleFont)
        else:
            PLT.suptitle(self.title, fontsize = self.titleFontSize, 
                         fontweight = 'semibold')
        self.fig = fig

    def createReportGrid(self, numCols):
        self.grid = ReportGrid(self.numRows, numCols)

    def write(self, pdfOutput = None):
        if pdfOutput:
            PLT.savefig(pdfOutput, format='pdf')
            PLT.close()

class ReportGrid(object):
    def __init__(self, numRows, numCols):

        #### Set Initial Attributes ####
        self.numRows = numRows
        self.numCols = numCols
        self.gridInfo = (numRows, numCols)
        self.rowCount = 0

    def createEmptyRow(self):
        grid = PLT.subplot2grid(self.gridInfo, (self.rowCount, 0), 
                                colspan = self.numCols)
        PLT.text(0.0, 0.5, "")
        clearGrid(grid)
        self.stepRow()

    def createEmptyCol(self, col):
        grid = PLT.subplot2grid(self.gridInfo, (0, col), 
                                rowspan = self.numRows)
        PLT.text(0.0, 0.5, "")
        clearGrid(grid)

    def createLineRow(self, row, startCol = 1, endCol = 8, color = "black"):
        colspan = endCol - startCol
        grid = PLT.subplot2grid(self.gridInfo, (row, startCol), 
                                colspan = colspan)
        PLT.plot((0.0, 1.0), (-2.0, -2.0), "-", color = color)
        clearGrid(grid)

    def createLineCol(self, col, startRow = 0, endRow = 19, color = "black"):
        rowspan = endRow - startRow
        grid = PLT.subplot2grid(self.gridInfo, (startRow, col), 
                                rowspan = rowspan)
        PLT.plot((0.5, 0.5), (0.0, 1.0), "-", color = color)
        clearGrid(grid)

    def finalizeTable(self):
        while self.rowCount < self.numRows:
            self.createEmptyRow()
            self.stepRow()

        PLT.subplots_adjust(top = .925, bottom = .075, 
                            left = 0.05, right = .95, 
                            wspace = -.0)

    def writeCell(self, cellInfo, text, rowspan = 1, colspan = 1,
                  color = "black", fontObj = ssFont, justify = "center",
                  setX = None):
        if setX:
            x0 = setX
        else:
            if justify in ["left", "center"]:
                x0 = 0.0
            else:
                x0 = 1.0
        grid = PLT.subplot2grid(self.gridInfo, cellInfo, 
                                rowspan = rowspan, colspan = colspan)
        PLT.text(x0, 0.5, text, color = color, 
                 fontproperties = fontObj, 
                 horizontalalignment = justify,
                 **bAlignment)
        clearGrid(grid)

    def writeFootnote(self, text, color = "black", fontObj = ssFont):
        grid = PLT.subplot2grid(self.gridInfo, (self.rowCount, 0), 
                                colspan = self.numCols)
        PLT.text(0.0, 0.5, text, color = color, 
                 fontproperties = fontObj,
                 **bAlignment)
        clearGrid(grid)

    def createColumnLabels(self, colLabs, color = "black", fontObj = ssFont,
                           justify = "center", setX = None):
        for ind, label in enumerate(colLabs):
            self.writeCell((self.rowCount, ind), label, 
                            color = "black", fontObj = fontObj,
                            justify = justify, setX = setX)
        self.stepRow()

    def stepRow(self):
        self.rowCount += 1

#################### MatplotLib Functions #########################

def startNewReport(numCols, title = None, landscape = True, 
                   titleFontSize = 12, numRows = None, 
                   titleFont = None):
    if titleFont:
        report = ReportPage(title = title, landscape = landscape, 
                            titleFont = titleFont)
    else:
        report = ReportPage(title = title, landscape = landscape, 
                            titleFontSize = titleFontSize)
    if numRows:
        report.numRows = numRows
    report.createReportGrid(numCols)
    return report

def setTickFontSize(plot, size = 10):
    allTicks = plot.get_xticklabels() + plot.get_yticklabels()
    for label in allTicks:
        label.set_fontsize(size) 

def clearGrid(grid):
    """Clears the given grid of axes and bounding box."""

    grid.xaxis.set_visible(False)
    grid.yaxis.set_visible(False)
    PLT.box(False)

def createParameterPage(paramLabels, paramValues, 
                        title = "Parameter Information",
                        pdfOutput = None,
                        titleFont = None):

    #### Make Main Figure ####
    report = startNewReport(8, title = title, landscape = True,
                            titleFont = titleFont)

    #### Get Grid Info ####
    grid = report.grid

    #### Add Labels ####
    paramLab = ARCPY.GetIDMessage(84400)
    inputLab = ARCPY.GetIDMessage(84401)
    grid.writeCell((0, 0), paramLab, colspan = 3, 
                   fontObj = ssBoldFont, justify = "left")
    grid.writeCell((0, 3), inputLab, colspan = 5, 
                   fontObj = ssBoldFont, justify = "left")
    grid.stepRow()
    grid.createLineRow(grid.rowCount, startCol = 0)

    #### Make Table ####
    for ind, label in enumerate(paramLabels):
        if grid.rowCount >= 20:
            grid.finalizeTable()
            if pdfOutput:
                report.write(pdfOutput)

            #### Make Main Figure ####
            titleCont = title + " " + ARCPY.GetIDMessage(84377)
            report = startNewReport(8, title = title, landscape = True,
                                    titleFont = titleFont)

            #### Get Grid Info ####
            grid = report.grid

            #### Add Labels ####
            grid.writeCell((0, 0), paramLab, colspan = 3, 
                           fontObj = ssBoldFont, justify = "left")
            grid.writeCell((0, 3), inputLab, colspan = 5, 
                           fontObj = ssBoldFont, justify = "left")
            grid.stepRow()
            grid.createLineRow(grid.rowCount, startCol = 0)


        value = paramValues[ind]
        grid.writeCell((grid.rowCount, 0), label, colspan = 3, 
                        justify = "left")
        grid.writeCell((grid.rowCount, 3), value, colspan = 5, 
                        justify = "left")
        grid.stepRow()
    grid.finalizeTable()

    if pdfOutput:
        report.write(pdfOutput)

def splitFootnote(footnote, index):
    outStr = []
    splitStr = []
    linelen = 0
    words = footnote.split()
    shortWords = []
    for word in words:
        lenWord = len(word)
        if lenWord > index:
            start = 0
            while start < lenWord:
                shortWords.append(word[start:start+index])
                start += index
        else:
            shortWords.append(word)

    for word in shortWords:
        linelen = linelen + len(word) + 1
        if linelen > index:
            if len(splitStr):
                outStr.append(" ".join(splitStr))
            splitStr = [word]
            linelen = len(word)
        else:
            splitStr.append(word)
    outStr.append(" ".join(splitStr))

    return outStr

######################### XML Functions ###########################

def xmlReport(title = None):
    """Creates Base Report Element.

    INPUTS:
    title {str, None}: Title for the report.

    OUTPUT:
    reportElement (obj): Base Report Element
    reportTree (obj): Report Element Tree
    """

    #### Root Element ####
    reportElement = ET.Element("Report")
    reportTree = ET.ElementTree(reportElement)

    #### Title Element ####
    if title != None:
        titleElement = ET.SubElement(reportElement, tag = "ssTitle")
        titleElement.text = title

    return reportElement, reportTree

def xmlFooter(parentElement, footerText):
    """Adds a footnote to a given Element.

    INPUTS:
    parentElement (obj): Parent Element
    footerText (str): Footnote text.

    OUTPUT:
    footerElement (obj): Footer Element.
    """

    footerElement = ET.SubElement(parentElement, tag = "ssFooter")
    footerElement.text = footerText

    return footerElement

def xmlGraphic(reportElement, graphicFile, footerText = None):
    """Generates XML Graphic Elements for Reporting.

    INPUTS:
    reportElement (obj): Root Element in XML report.
    graphicFile (file): Image file to embed.
    footer {str, None}: Footer for the image.

    OUTPUT:
    graphElement (obj): Graph Element
    """

    graphicElement = ET.SubElement(reportElement, tag = "ssGraphic")
    imageElement = ET.SubElement(graphicElement, tag = "ssImage")
    imageElement.text = graphicFile
    if footerText != None:
        footerElement = xmlFooter(graphicElement, 
                        footerText = footerText)

    return graphicElement

def xmlRow(tableElement, cellValues, rType = "ssRow"):
    """Returns a Row Element for a given Table Element.

    INPUTS:
    tableElement (obj): Table Element
    cellValues (list): values in the row.
    rType {str, ssRow}: type of row {ssRow, ssFloatRow}

    OUTPUT:
    rowElement (obj): Row Element
    """
    
    rowElement = ET.SubElement(tableElement, tag = rType)
    rowInd0 = ET.SubElement(rowElement, tag = "Label")
    rowInd1 = ET.SubElement(rowElement, tag = "Value")
    if rType == "ssRow":
        label, value = cellValues
        rowInd0.text = label
        rowInd1.text = value
    else:
        rowInd2 = ET.SubElement(rowElement, tag = "SignBox")
        label, value, img = cellValues
        rowInd0.text = label
        rowInd1.text = value
        rowInd2.text = img
    
    return rowElement

def xmlTable(reportElement, rowValues, title = None, tType = "ssTable"):
    """Generates XML Table Elements for Reporting.

    INPUTS:
    reportElement (obj): Root Element in XML report.
    rowValues (list): Each row in the table is a list.
    title {str, None}: Title of the table.
    tType {str, ssTable}: type of table {ssTable, ssFloat}

    OUTPUT:
    tableElement (obj): Table Element in XML report.
    """

    tableElement = ET.SubElement(reportElement, tag = tType)
    if title != None:
        tableTitle = ET.SubElement(tableElement, "ssTableTitle")
        tableTitle.text = title

    if tType == "ssTable":
        rType = "ssRow"
    else:
        rType = "ssFloatRow"
    for row in rowValues:
        xmlRow(tableElement, row, rType = rType)

    return tableElement

######################### HTML Functions ###########################

def report2html(reportTree, htmlFile):
    """Converts an Report Element Tree to a HTML File.

    INPUTS:
    reportTree (obj): Report Element Tree
    htmlFile (str): path to the output html file
    """

    root = ET.Element('html')

    #### <head> ####
    head = ET.Element('head')

    #### <style> ####
    style = ET.Element('style')
    style.attrib['type'] = "text/css"
    style.text = """
        html, body, div, span, applet, object, iframe,
        h1, h2, h3, h4, h5, h6, p, blockquote, pre,
        a, abbr, acronym, address, big, cite, code,
        del, dfn, em, font, img, ins, kbd, q, s, samp,
        small, strike, strong, sub, sup, tt, var,
        b, u, i, center,
        dl, dt, dd, ol, ul, li,
        fieldset, form, label, legend,
        table, caption, tbody, tfoot, thead, tr, th, td {
            margin: 0;
            padding: 0;
            border: 0;
            outline: 0;
            font-size: 100%;
            vertical-align: baseline;
            background: transparent;
        }
        body {
            line-height: 1.2em;
        }
        ol, ul {
            list-style: none;
        }
        blockquote, q {
            quotes: none;
        }
        blockquote:before, blockquote:after,
        q:before, q:after {
            content: '';
            content: none;
        }

        :focus {
            outline: 0;
        }

        table {
            border-collapse: collapse;
            border-spacing: 0;
        }



        body {
            font-family: tahoma, verdana, sans-serif;
            background-color: #e5f0f5;
            text-align: center;

        }
        h1 {
            text-align: center;
            color:#00709C;
            font-size:1.2em;
            margin: 12px;
        }

        caption {
            text-align: center;
            color:#00709C;
            font-size:1em;
            margin: 0 0 10px 0;
            font-weight: bold;
        }
        th {
            text-align: left;
            padding-right: 4px;
        }

        #mainImg {
            border: 1px solid #c6c6c6;
            padding: 20px 30px 10px 30px;
            text-align: center;
            background-color: #ffffff;
            margin:0 auto 15px auto;
            width: 540px;
        }

        #mainImg p {
            text-align: left;
            font-size:.8em;
            border-top: 1px solid #c6c6c6;
            padding: 10px 0 0 0;
        }

        #key {
            float: center;
            width: 540px;
            margin:0 auto;
            text-align: left;
        }

        #keytable {
            float: left;
            font-size:.75em;
            position: absolute;
            margin: 30px 0 0 0;
        }

        #keytable img {
            margin-left: 4px;
        }
        .infotable {
            border: 1px solid #c6c6c6;
            background-color: #ffffff;
            font-size:1.2em;
            width: 600px;
            margin: 0 auto 15px auto;
        }
        .infotable th, .infotable td  {
            width: 50%;
            font-size:.75em;
            padding: 5px;
            border-top: 1px solid #c6c6c6;
        }

        .infotable th{
            border-right: 1px solid #c6c6c6;
        }

        th {
            text-align: right;
        }
        td {
            text-align: left;
        }
    """
    head.append(style)
    # </style>

    #### <title>...</title> ####
    title_element = reportTree.find('ssTitle')
    title = ET.Element('title')
    title_text = ("" if title_element is None else title_element.text)
    title.text = title_text

    #### </head> ####
    head.append(title)

    #### <body> ####
    body = ET.Element('body')

    #### <h1>Title</h1> ####
    title_header = ET.Element('h1')
    title_header.text = title_text
    body.append(title_header)

    #### <table>Moran's... ####
    key_div = ET.Element('div')
    key_div.attrib['id'] = "key"
    key_table = ET.SubElement(key_div, 'table')
    key_table.attrib['id'] = "keytable"
    table_element = reportTree.find('ssGraphic/ssFloat')
    for row in (table_element.findall('ssFloatRow') if table_element is not None else []):
        #### <tr> ####
        row_elt = ET.Element('tr')
        label = ET.Element('th')
        label_elt = row.find('Label')
        label.text = (label_elt.text if label_elt is not None else "")
        value = ET.Element('td')
        value_elt = row.find('Value')
        value.text = (value_elt.text if value_elt is not None else "")
        signbox = ET.Element('td')
        signbox_elt = row.find('SignBox')
        if signbox_elt is not None and signbox_elt.text:
            img = ET.Element('img')
            img.attrib['src'] = "file://%s" % signbox_elt.text
            signbox.append(img)
        row_elt.append(label)
        row_elt.append(value)
        row_elt.append(signbox)
        key_table.append(row_elt)
        #### </tr> ####
    #### </table> ####
    body.append(key_div)

    #### <img src="..."> #### 
    img_div = ET.Element('div')
    img_div.attrib['id'] = "mainImg"
    image = ET.SubElement(img_div, 'img')
    image_src = reportTree.find('ssGraphic/ssImage')
    image.attrib['src'] = ("" if image_src is None else "file://%s" % image_src.text)
    image.attrib['alt'] = title_text
    body.append(img_div)

    #### <p>given ...</p> ####
    explanation_element = reportTree.find('ssGraphic/ssFooter')
    expanatory_text = ("" if explanation_element is None else explanation_element.text)
    explanatory_par = ET.SubElement(img_div, 'p')
    explanatory_par.text = expanatory_text
    tables = reportTree.findall('ssTable')
    if tables is not None:
        for table_elt in tables:
            table = ET.Element('table')
            table.attrib["class"] = "infotable"
            caption = ET.Element('caption')
            caption_elt = table_elt.find('ssTableTitle')
            caption.text = (caption_elt.text if caption_elt is not None else "")
            if caption.text:
                table.append(caption)
            for row_elt in table_elt.findall('ssRow'):
                row = ET.Element('tr')
                label = row_elt.find('Label')
                value = row_elt.find('Value')
                label_elt = ET.Element('th')
                label_elt.text = (label.text if label is not None else "")
                value_elt = ET.Element('td')
                value_elt.text = (value.text if value is not None else "")
                row.append(label_elt)
                row.append(value_elt)
                table.append(row)
            body.append(table)
    #### </body> ####
    root.append(head)
    root.append(body)
    htmlStr = ET.tostring(root)
    outHTML = UTILS.openFile(htmlFile, 'w')
    strictDocStr = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
"http://www.w3.org/TR/html4/strict.dtd">"""
    outHTML.write("%s\n" % strictDocStr)
    outHTML.write(htmlStr)
    outHTML.close()

