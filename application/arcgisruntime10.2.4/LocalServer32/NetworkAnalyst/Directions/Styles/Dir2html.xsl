<?xml version="1.0" ?>

<xsl:stylesheet
  version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:NA="http://www.esri.com/arcgis/directions"
  xmlns:ms="urn:schemas-microsoft-com:xslt">

  <xsl:strip-space elements="NA:DIRECTIONS NA:DIRECTION NA:STRINGS"/> 
  <xsl:output method="html" indent="no" encoding="UTF-8"/>
  <xsl:param name="OUTPUTFILENAME" select="zero"/>
  <xsl:param name="DEFAULTTBTPOS" select="4"/>
  <xsl:param name="DEFAULTSOPOS" select="4"/>
  <xsl:param name="IMAGESPATH" select="zero"/>
  <xsl:param name="HTMLDIR" select="'ltr'"/>

  <xsl:param name="UseCompactMode" select="0"/>
  <xsl:param name="ShowDirNumColumn" select="1"/>
  <xsl:param name="ShowTimeColumn" select="1"/>
  <xsl:param name="ShowDirTimeColumn" select="1"/>
  <xsl:param name="ShowDirLengthColumn" select="1"/>
  <xsl:param name="ShowACCColumn" select="1"/>
  <xsl:param name="ShowMapLinkColumn" select="1"/>

  <xsl:param name="UIROUTESTRING" select="'Route:'"/>
  <xsl:param name="UINULLROUTE" select="'&lt;NULL&gt;'"/>
  <xsl:param name="UISHOWMAP" select="'Map'"/>
  <xsl:param name="UIHIDEMAP" select="'Hide'"/>
  <xsl:param name="UITITLE" select="'Driving Directions'"/>
    
  <xsl:variable name="FirstItemColor" select="'#fdfdf7'"/>
  <xsl:variable name="SecondItemColor" select="'#f7f7ea'"/>
  <!--id of reference used to pass commands to C++ code-->
  <xsl:variable name="CommandHrefId" select="'refCom'"/>


  <xsl:template match="NA:DIRECTIONS">
    <html dir="{$HTMLDIR}">
      <head>
        <title><xsl:value-of select="$UITITLE"/></title>
       
       
       <xsl:if test="$UseCompactMode=0">
        <style type="text/css" media="screen">
         * { FONT-SIZE: 12px; FONT-FAMILY: Verdana, Arial, Helvetica, sans-serif }
         TD { padding: 3px }
         A:link { color: blue }
         A:visited { color: blue }
         table { width:100%; }
         #pagebreakheader { display: none }
         #openroute { width:30px; }
         #maplink { width:40px;vertical-align:top;padding-left:8px }
         #pagebreak { display: none }
         #openevents { width:30px;vertical-align:top }
         #drtext { width:410px;vertical-align:top }
         #drtotaltext { width:410px;vertical-align:top }
         #index { width:35px; vertical-align:top }
         #dirlength { width:75px;vertical-align:top;text-align:right }
         #time { width:75px;vertical-align:top;text-align:right }
         #eta { width:65px;text-align:right;vertical-align:top;padding-right:8px }
         #distance { width:72px;vertical-align:top;text-align:right }
         #time_window { font-size: 10px;text-indent:15px }
         #violation_time { font-size: 10px; color: red; text-indent:15px }
         #wait_time { font-size: 10px; text-indent:15px }
         #service_time { font-size: 10px; text-indent:15px }
        </style>
       </xsl:if>

       <xsl:if test="$UseCompactMode=1">
        <style type="text/css" media="screen">
         * { FONT-SIZE: 10px; FONT-FAMILY: Verdana, Arial, Helvetica, sans-serif }
         TD { padding: 3px }
         A:link { color: blue }
         A:visited { color: blue }
         table { width:100%; }
         #pagebreakheader { display: none }
         #maplink { vertical-align:top;padding-left:9px }
         #pagebreak { display: none }
         #openevents { vertical-align:top }
         #drtext { vertical-align:top }
         #drtotaltext { vertical-align:top }
         #index { vertical-align:top }
         #dirlength { vertical-align:top;text-align:right }
         #time { vertical-align:top;text-align:right }
         #eta { text-align:right;vertical-align:top;padding-right:9px }
         #distance { vertical-align:top;text-align:right }
         #time_window { font-size: 9px;text-indent:15px }
         #violation_time { font-size: 9px; color: red; text-indent:15px }
         #wait_time { font-size: 9px; text-indent:15px }
         #service_time { font-size: 9px; text-indent:15px }
        </style>
       </xsl:if>

      <style type="text/css" media="print">
        * { FONT-SIZE: 14px; FONT-FAMILY: Verdana, Arial, Helvetica, sans-serif }
        TD { padding: 3px }
        A:link { color: black; text-decoration: none }
        A:visited { color: black; text-decoration: none }
        body { background-color:transparent }
        table { width:100% }
        #pagebreakheader { page-break-after: always }
        #zoomcontrol { display: none }
        #openroute { display: none }
        #maplinkdiv { display: none }
        #pagebreak { display: block }
        #drtext { width:3.2in;vertical-align:top }
        #index { width:0.15in;vertical-align:top }
        #dirlength { width:0.88in;vertical-align:top;text-align:right }
        #time { width:0.88in;vertical-align:top;text-align:right }
        #eta { width:0.8in;text-align:right;vertical-align:top;padding-right:7px }
        #distance { width:0.84in;vertical-align:top;text-align:right }
        #time_window { font-size:12px;text-indent:15px }
        #violation_time { font-size:12px;color:red;text-indent:15px }
        #wait_time { font-size: 12px;text-indent:15px }
        #service_time { font-size: 12px;text-indent:15px }
        #openevents { width:1px }
        #eventdiv { display:none }
      </style>

      <script language="javascript" type="text/javascript">
       <xsl:if test="$UseCompactMode=0">
        //<![CDATA[
        var g_bUseCompactMode=0;
        ]]>
       </xsl:if>
       <xsl:if test="$UseCompactMode=1">
        //<![CDATA[
        var g_bUseCompactMode=1;
        ]]>
       </xsl:if>
//<![CDATA[
var g_dTBTMapScale = 1;
var g_dSVMapScale = 7;

var g_bColItemNum=true;
var g_bColETA=true;
var g_bColTime=true;
var g_bColDistance=true;
var g_bColCumulDist=true;
var g_bColMap=true;
var g_bColEvents=false;

var barHeight = 103;
var zoompoints = 9;

function SetTBTMapScale(scale) {g_dTBTMapScale=scale;}
function SetSVMapScale(scale) {g_dSVMapScale=scale;}

function SetColItemNum(visible) {g_bColItemNum=visible;}
function SetColETA(visible) {g_bColETA=visible;}
function SetColTime(visible) {g_bColTime=visible;}
function SetColDistance(visible) {g_bColDistance=visible;}
function SetColCumulDist(visible) {g_bColCumulDist=visible;}
function SetColMap(visible) {g_bColMap=visible;}
function SetColEvents(visible) {g_bColEvents=visible;}

var g_bPBEnabled=true;

function SetPageBreaks(bEnabled)
{
  if (g_bPBEnabled == bEnabled)
    return;

  var collCol=document.all.item("pagebreakheader");

  if(collCol)
  {
    if (collCol.length)
    {
      if(bEnabled)
        for(i=0;i<collCol.length;i++)
          collCol.item(i).style.display="block";
      else
        for(i=0;i<collCol.length;i++)
          collCol.item(i).style.display="none";
    }
    else
    {
      if(bEnabled)
        collCol.style.display="block";
      else
        collCol.style.display="none";
    }
  }

  g_bPBEnabled = bEnabled;
}


function SetImageSrc(oOldImage, strImageSRC)
{
  var oImage = new Image(); 
  oImage = oOldImage;
  oImage.src = "";
  oImage.src = strImageSRC; 
}

function SetImageSrcStr(strImage, strImageSRC)
{
  document.images[strImage].src = null;
  document.images[strImage].src = strImageSRC;
}

function UpdateSlider(key)
{
  strSl="Slider"+(Math.floor(key/0x1000000000000))+"_"+(Math.floor(( Math.floor(key%0x1000000000000) / 0x100000000 )));
  var oSld=document.all.item(strSl);
  oSld.style.top=-1;
}

function ShowColumn(sColumn,bShow)
{
  var collCol=document.all.item(sColumn);
  if(collCol)
  {
    if(bShow)
      for(i=0;i<collCol.length;i++)
        collCol.item(i).style.display="block";
    else
      for(i=0;i<collCol.length;i++)
        collCol.item(i).style.display="none";
  }
}

function SetColSpan(oColl, value)
{
  if(!oColl)
    return;

  if(oColl.length)
    for(i=0;i<oColl.length;i++)
      oColl.item(i).colSpan=value;
  else
    oColl.colSpan=value;
}

function ChangeColspan()
{
  SetColSpan(document.all.item("routename"),1+(g_bColEvents?1:0)+(g_bColItemNum?1:0)+(g_bColETA?1:0)+(g_bColCumulDist?1:0));
  SetColSpan(document.all.item("mapimage"),3+(g_bColEvents?1:0)+(g_bColItemNum?1:0)+(g_bColTime?1:0)+(g_bColDistance?1:0)+(g_bColMap?1:0)+(g_bColETA?1:0)+(g_bColCumulDist?1:0));
  SetColSpan(document.all.item("drtotaltext"),1+(g_bColEvents?1:0)+(g_bColItemNum?1:0)+(g_bColTime?1:0)+(g_bColDistance?1:0)+(g_bColMap?1:0)+(g_bColETA?1:0)+(g_bColCumulDist?1:0));
  SetColSpan(document.all.item("routenamecompact"), 1+(g_bColEvents?1:0)+(g_bColItemNum?1:0)+(g_bColETA?1:0)+(g_bColCumulDist?1:0)+(g_bColTime?1:0)+(g_bColDistance?1:0)+(g_bColMap?1:0));
}

function Update()
{
  ShowColumn("index",g_bColItemNum); 
  ShowColumn("eta",g_bColETA);
  ShowColumn("time",g_bColTime);
  ShowColumn("dirlength",g_bColDistance);
  ShowColumn("distance",g_bColCumulDist);
  ShowColumn("maplink",g_bColMap);
  ShowColumn("openevents",g_bColEvents);
  ChangeColspan();
}

/*
  Makes column with button to open events list visible
*/
function ShowEvents()
{
  if (g_bColEvents)
  {
    ShowColumn("openevents",g_bColEvents);
    ChangeColspan();
  }
}

/*
  Refreshes map image and corresponding controls
    sMapName - table row where map is stored (<tr> tag)
    oAShow - map show reference (<href> tag)
    oAHide - map hide reference
    oImage - image containter object (<img> tag)
    oSlider - slider object (<div> tag), null of image has no slider
    iIsStop - non 0 if current image is for stop point, 0 otherwise
*/
function RefreshMap(sMapName,oAShow,oAHide,oImage,oSlider,iIsStop)
{
  SetImageSrc(oImage, oImage.src);  // refresh image
  sMapName.style.display = "block"; // make image tr visible
  oAShow.style.display = "none";    // hide show button
  oAHide.style.display = "block";   // show hide button
  // calculate slider position if necessary
  if (oSlider != null)
    if ( parseInt(oSlider.style.top) < 0 )
    {
      if ( iIsStop == 0 )
        oSlider.style.top = Math.floor(g_dTBTMapScale*barHeight/zoompoints+1);
      else
        oSlider.style.top = Math.floor(g_dSVMapScale*barHeight/zoompoints+1);
    }
}

/*
  Toggles visibility of table rows containing events
    strTR - string identifier of TRs containing route and direction ids
    strShow - string identifier of show map reference containing route and direction ids
    strHide - string identifier of hide map reference containing route and direction ids
    strMap - string identifier template of row containing events (with route and direction)
    strImag - string identifier template for event map images
    oA - href object of hide/show button for events
    numEvents - number of events for given direction
*/

  var g_varClosed = "<NOBR>[+]</NOBR>";
  var g_varOpened = "<NOBR>[-]</NOBR>";
  
function ToggleTR(strTR,strShow,strHide,strMap,strImage,strSlider,oA,strOh2,numEvents)
{
  // loop through all rows with events and set their parameters
  for (i = 0; i < numEvents; i++)
  {
    // obtain html objects for current event row from given string templates
    oTR = document.all.item(strTR + "_" + i);
    oShow = document.all.item(strShow + "_" + i);
    oHide = document.all.item(strHide + "_" + i);
    oMap = document.all.item(strMap + "_" + i);
    oImage = document.all.item(strImage + "_" + i);
    oSlider = document.all.item(strSlider + "_" + i);
    // toggle row visibility
    if(oTR.style.display != "none")
    {
      oTR.style.display = "none";
      if( oMap != null )
        oMap.style.display = "none";
    }
    else
    {
      if( oHide != null )
        if (oHide.style.display != "none")
        {
          // if map is visible when showing row this map needs to be refreshed
          if( oMap != null )
            RefreshMap(oMap,oShow,oHide,oImage,oSlider,0);
        }
       oTR.style.display = "block";
    }
  }
  
  // toggle drop down list text
  oh2 = document.all.item(strOh2);
  if (oA.innerText == "[+]")
  {
    if( oh2 != null )
      oh2.style.display = "none";
      
    oA.innerHTML = g_varOpened;
  }
  else
  {
    if( oh2 != null )
      oh2.style.display = "block";
      
    oA.innerHTML = g_varClosed;
  }
}

        function ToggleBody(oTBody,oA,oh2)
        {
         if( oTBody == null )
          return;
          
          if(oTBody.style.display != "none")
          {
            oTBody.style.display = "none";
            oh2.style.display = "block";
            oA.innerHTML = g_varClosed;
          }
          else
          {
            oTBody.style.display = "block";
            oh2.style.display = "none";
            oA.innerHTML = g_varOpened;
          }
        }

        function ToggleMap(sMapName,oAShow,oAHide,oImage,oSlider,iIsStop)
        {
          if( sMapName == null )
            return;
            
          if ( sMapName.style.display != "block" )
          {
            RefreshMap(sMapName,oAShow,oAHide,oImage,oSlider,iIsStop);
          }
          else
          {
            sMapName.style.display = "none";
            oAHide.style.display = "none";
            oAShow.style.display = "block";
          }
        }
 
        function GetPos(y)
        {
          return parseInt(y)/barHeight*zoompoints;
        }

        function GetSliderPos(oSld)
        {
          return GetPos(oSld.style.top + oSld.style.height/2);
        }

        function SetSliderPos(oSld, pos)
        {
          oSld.style.top = pos*barHeight/zoompoints + 1;  
        }

        function ZoomTo(value, oA, dirID, routeID, oImg, sMapFile, iEventId)
        {
          oA.href="ZOOMMAP!ID=" + dirID +"&RouteID=" + routeID + "&Value=" + value + "&File=" + sMapFile + "&Event=" + iEventId;
          oA.click();
          SetImageSrc(oImg, sMapFile);
        }
        
        function OnSliderClick(oA, dirID, routeID, oImg, sMapFile, oSld, iEventId)
        {
          var newPos = Math.floor(GetPos(event.y));
          SetSliderPos(oSld, newPos);
          ZoomTo(newPos, oA, dirID, routeID, oImg, sMapFile, iEventId);
        }

var exp = 0.1;

        function OnPlus(oA, dirID, routeID, oImg, sMapFile, oSld, iEventId)
        {
          var pos = GetSliderPos(oSld);
          var floorpos = Math.floor(pos);
          if (floorpos+exp>=pos && floorpos > 0)
            floorpos--;
          SetSliderPos(oSld, floorpos);
          ZoomTo(floorpos, oA, dirID, routeID, oImg, sMapFile, iEventId);
        }

        function OnMinus(oA, dirID, routeID, oImg, sMapFile, oSld, iEventId)
        {
          var pos = Math.floor(GetSliderPos(oSld));
          if (pos < zoompoints-1)
            pos++;
          pos=Math.floor(pos);
          SetSliderPos(oSld, pos);
          ZoomTo(pos, oA, dirID, routeID, oImg, sMapFile, iEventId);
        }

        var g_oldSelection = null
        var g_curSelectedItem = null;
        var g_sSelectionColor = "#e5e7b9";

        function HighlightItem(item, dirItemIndex, dirEventIndex)
        {
          if( item == null || !g_bUseCompactMode )
            return;

          if( g_curSelectedItem != null )
          {
            if( g_curSelectedItem.directionNativeColor != null )
              g_curSelectedItem.style.backgroundColor = g_curSelectedItem.directionNativeColor;
            g_curSelectedItem = null;
          }

          // update item info
          g_curSelectedItem = item;
          g_curSelectedItem.directionIndex = dirItemIndex;
          g_curSelectedItem.directionEventIndex = dirEventIndex;

          if( g_oldSelection == null )
           g_curSelectedItem.directionNativeColor = item.style.backgroundColor;

          g_curSelectedItem.style.backgroundColor = g_sSelectionColor;
        }
        
        function GetSelectedDirectionIndex()
        {
          if( g_curSelectedItem )
            return g_curSelectedItem.directionIndex - 1;
          else
           return -1;
        }
        
        function GetSelectedDirectionEventIndex()
        {
          if( g_curSelectedItem )
            return g_curSelectedItem.directionEventIndex;
          else
           return -1;
        }
        
        function RemoveCurrentSelection()
        {
          if( g_curSelectedItem )
          {
            if( g_curSelectedItem.directionNativeColor != null )
              g_curSelectedItem.style.backgroundColor = g_curSelectedItem.directionNativeColor;

            g_oldSelection = g_curSelectedItem;
          }
        }
        
        function RestoreCurrentSelection()
        { 
          if( g_oldSelection )
          {
            g_oldSelection.style.backgroundColor = g_sSelectionColor;
            g_oldSelection = null;
          }
        }
]]>       
      </script>
      </head>

      <body style="overflow:auto" topmargin="0" leftmargin="0">
        <!--reference to pass commands to C++ code-->
        <a id="{$CommandHrefId}" style="display:none"/>
        <table cellspacing="0" id="Directions">
                  
          <xsl:for-each select="NA:ROUTE">
            <xsl:variable name="TBODYID" select="concat('RouteTable',position())"/>
            <xsl:variable name="BUTTONID" select="concat('Sign',position())"/>
            <xsl:variable name="TID" select="concat('Table',@id)"/>
            <xsl:variable name="H2ID" select="concat('h2',position())"/>
            <!--id of show/hide overview map references-->
            <xsl:variable name="HREFMAPSHOW" select="concat('RouteMapShow_',position())"/>
            <xsl:variable name="HREFMAPHIDE" select="concat('RouteMapHide_',position())"/>
            <xsl:variable name="OMAPROWID" select="concat('RouteMap_',position())"/>
            <xsl:variable name="OMAPIMGID" select="concat('RouteMapImg_',position())"/>
            <xsl:variable name="OMAPFILENAME" select="concat($OUTPUTFILENAME,$OMAPROWID,'.jpg')"/>

              <tr bgcolor="#e3e5c7">
               <xsl:if test="$UseCompactMode=0">
                <td id="openroute"/>
               </xsl:if>
                <td id="index"/>
                <td id="distance"/>
                <td id="eta"/>
                <td id="openevents"/>
                <td id="drtext"/>
                <td id="dirlength"/>
                <td id="time"/>
                <td id="maplink"/>
                <td/>
              </tr>

              <tr id="head" bgcolor="#e3e5c7">
               <xsl:if test="$UseCompactMode=0">
                <xsl:choose>
                 <xsl:when test="position()=1">
                  <td id="openroute">
                   <a name="{$TID}"/>
                   <div id="{$BUTTONID}" onclick="javascript:ToggleBody({$TBODYID},{$BUTTONID},{$H2ID})" style="FONT-FAMILY:Courier;cursor:hand">[-]</div>
                  </td>
                 </xsl:when>
                 <xsl:otherwise>
                  <td id="openroute">
                   <a name="{$TID}"/>
                   <div id="{$BUTTONID}" onclick="javascript:ToggleBody({$TBODYID},{$BUTTONID},{$H2ID})" style="FONT-FAMILY:Courier;cursor:hand">[+]</div>
                  </td>
                 </xsl:otherwise>
                </xsl:choose>
                <td id="routename">
                  <b>
                   <a href="ZOOMTOALL!RouteID={position()}">
                    <xsl:value-of select="$UIROUTESTRING"/>
                    <xsl:text> </xsl:text>
                    <xsl:choose>
                     <xsl:when test="@name=''">
                      <xsl:value-of select="$UINULLROUTE"/>
                     </xsl:when>
                     <xsl:otherwise>
                      <xsl:value-of select="@name"/>
                     </xsl:otherwise>
                    </xsl:choose>
                   </a>
                  </b>
                </td>
                <td id="dirlength">
                 <xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='length']/@text"/>
                </td>
                <td id="time">
                 <xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='time']/@text"/>
                </td>
                <td id="maplink" style="vertical-align:middle">
                  <xsl:if test="$UseCompactMode=0">
                  <div id="maplinkdiv">
                  <!--ToggleMap(sMapName,oAShow,oAHide,oImage,oSlider,iIsStop)-->
                  <a id="{$HREFMAPSHOW}" href="javascript:ToggleMap({$OMAPROWID},{$HREFMAPSHOW},{$HREFMAPHIDE},{$OMAPIMGID},null,0);">
                   <xsl:value-of select="$UISHOWMAP"/>
                  </a>
                  <a id="{$HREFMAPHIDE}" href="javascript:ToggleMap({$OMAPROWID},{$HREFMAPSHOW},{$HREFMAPHIDE},{$OMAPIMGID},null,0);" style="display:none">
                   <xsl:value-of select="$UIHIDEMAP"/>
                  </a>
                 </div>
                    </xsl:if>
                </td>
                <td/>
                 </xsl:if>

               <xsl:if test="$UseCompactMode=1">
                <td id="routenamecompact">
                 <div>
                  <b>
                   <a href="ZOOMTOALL!RouteID={position()}">
                    <xsl:value-of select="$UIROUTESTRING"/>
                    <xsl:text> </xsl:text>
                    <xsl:choose>
                     <xsl:when test="@name=''">
                      <xsl:value-of select="$UINULLROUTE"/>
                     </xsl:when>
                     <xsl:otherwise>
                      <xsl:value-of select="@name"/>
                     </xsl:otherwise>
                    </xsl:choose>
                   </a>
                  </b>
                 </div>
                 <xsl:for-each select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='normal' or  attribute::style='time_window' or attribute::style='violation_time' or attribute::style='wait_time' or attribute::style='service_time' or attribute::style='summary']">
                  <div id="{@style}">
                   <xsl:value-of select="@text"/>
                  </div>
                 </xsl:for-each>
                </td>
                <td/>
               </xsl:if>
              </tr>

            <xsl:call-template name="MAPROW">
              <xsl:with-param name="MAPID" select="$OMAPROWID"/>
              <xsl:with-param name="BACKGROUNDCOLOR" select="$SecondItemColor"/>
              <xsl:with-param name="MAPFILENAME" select="$OMAPFILENAME"/>
              <xsl:with-param name="MAPIMAGEID" select="$OMAPIMGID"/>
            </xsl:call-template>

            <xsl:choose>
              <xsl:when test="position()=1">
   
                <tr id="pagebreak">
                  <td id="{$H2ID}" style="display:none">
                    <xsl:if test="position()&lt;last()"><h2 id="pagebreakheader"/></xsl:if>
                  </td>
                </tr>
                <tbody id="{$TBODYID}" style="display:block">
                                                                                
                  <xsl:apply-templates select="NA:PATH">
                    <xsl:with-param name="RID" select="position()"/>
                  </xsl:apply-templates>

                 <xsl:if test="$UseCompactMode=0">
                  <xsl:call-template name="TOTALITEM">
                  </xsl:call-template>
                 </xsl:if>

                  <xsl:if test="position()&lt;last()">
                    <tr id="pagebreak"><td><h2 id="pagebreakheader"/></td></tr>
                  </xsl:if>

                </tbody>
              </xsl:when>
              <xsl:otherwise>

                <tr id="pagebreak">
                  <td id="{$H2ID}" style="display:block">
                    <xsl:if test="position()&lt;last()"><h2 id="pagebreakheader"/></xsl:if>
                  </td>
                </tr>

                <tbody id="{$TBODYID}" style="display:none">
                      
                  <xsl:apply-templates select="NA:PATH">
                    <xsl:with-param name="RID" select="position()"/>
                  </xsl:apply-templates>

                  <xsl:call-template name="TOTALITEM">
                  </xsl:call-template>

                  <xsl:if test="position()&lt;last()">
                    <tr id="pagebreak"><td><h2 id="pagebreakheader"/></td></tr>
                  </xsl:if>
          
                </tbody>
              </xsl:otherwise>
            </xsl:choose>
        

          </xsl:for-each>
        </table>
        <script language="javascript" type="text/javascript">ShowEvents();</script>
      </body>
    </html>
  </xsl:template>

  <xsl:template match="NA:PATH">
    <xsl:param name="RID" select="0"/>

    <xsl:apply-templates>
      <xsl:with-param name="ROUTEID" select="$RID"/>
      <xsl:with-param name="PATHID" select="@id"/>
    </xsl:apply-templates>

    <xsl:if test="position()&lt;last()">
      <tr id="pagebreak"><td><h2 /></td></tr>
    </xsl:if>
  </xsl:template>

  <xsl:template match="NA:DIRECTION">
    <xsl:param name="ROUTEID" select="0"/>
    <xsl:param name="PATHID" select="0"/>
    <xsl:choose>
      <xsl:when test="(@id mod 2) = 1">
        <xsl:call-template name="DIRECTIONITEM">
          <xsl:with-param name="ROUTEID" select="$ROUTEID"/>
          <xsl:with-param name="PATHID" select="$PATHID"/>
          <xsl:with-param name="BACKGROUNDCOLOR" select="$FirstItemColor"/>
        </xsl:call-template>
      </xsl:when>
      <xsl:otherwise>
        <xsl:call-template name="DIRECTIONITEM">
          <xsl:with-param name="ROUTEID" select="$ROUTEID"/>
          <xsl:with-param name="PATHID" select="$PATHID"/>
          <xsl:with-param name="BACKGROUNDCOLOR" select="$SecondItemColor"/>
        </xsl:call-template>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

 <xsl:template name="TOTALITEM">
  <xsl:if test="$UseCompactMode=0">
   <tr id="tr1" bgcolor="ivory">
     <td id="openroute">&#xa0;</td>
    <td id="index">&#xa0;</td>
    <td id="distance">
     <xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='Cumul_length']/@text"/>
    </td>
    <td id="eta">
     <xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='eta']/@text"/>
    </td>
    <td id="openevents">&#xa0;</td>
    <td id="drtext">
     <xsl:for-each select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='normal' or  attribute::style='time_window' or attribute::style='violation_time' or attribute::style='wait_time' or attribute::style='service_time' or attribute::style='summary']">
      <div id="{@style}">
       <xsl:value-of select="@text"/>
      </div>
     </xsl:for-each>
    </td>
     <td id="dirlength">
      &#xa0;<!--xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='length']/@text"/-->
     </td>
     <td id="time">
      &#xa0;<!--xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='time']/@text"/-->
     </td>
    <td id="maplink">&#xa0;</td>
    <td/>
   </tr>
  </xsl:if>
 </xsl:template>

  <xsl:template name="DIRECTIONITEM">
    <xsl:param name="ROUTEID" select="0"/>
    <xsl:param name="PATHID" select="0"/>
    <xsl:param name="BACKGROUNDCOLOR" select="'white'"/>
    <xsl:variable name="MAPID" select="concat('Map_', $ROUTEID,'_',@id)"/>
    <xsl:variable name="HREFMAPIDSHOW" select="concat('HRefMapShow', $ROUTEID,'_', @id)"/>
    <xsl:variable name="HREFMAPIDHIDE" select="concat('HRefMapHide', $ROUTEID,'_', @id)"/>
    <xsl:variable name="MAPIMAGEID" select="concat('MapImage', $ROUTEID,'_',@id)"/>
    <xsl:variable name="ZOOMSLIDERID" select="concat('Slider', $ROUTEID,'_',@id)"/>
    <xsl:variable name="MAPFILENAME" select="concat($OUTPUTFILENAME, $MAPID, '.jpg')"/>
    <xsl:variable name="aid" select="concat('ref', $ROUTEID,'_',@id)"/>
    <xsl:variable name="MAPSCALETBT" select="floor($DEFAULTTBTPOS * 103 div 9 + 1)"/>
    <xsl:variable name="MAPSCALESO" select="floor($DEFAULTSOPOS * 103 div 9 + 1)"/>
    <xsl:variable name="NumIsStop" select="count(NA:STRINGS/child::NA:STRING[attribute::style='arrive']) + count(NA:STRINGS/child::NA:STRING[attribute::style='depart'])"/>
    <!--objects for events display-->
    <xsl:variable name="EBUTTONID" select="concat('EventButton_', @id, '_', $ROUTEID)"/>
    <xsl:variable name="EH2ID" select="concat('EventH2_', @id, '_', $ROUTEID)"/>
    <xsl:variable name="NUMEVENTS" select="count(NA:EVENTS/child::NA:EVENT)"/>
    <xsl:variable name="TRID" select="concat('EventTR_', @id, '_', $ROUTEID)"/>
    <xsl:variable name="EVENTMAPID" select="concat('EventMap_', $ROUTEID, '_', @id)"/>
    <xsl:variable name="EVENTMAPIMAGEID" select="concat('EventMapImage', $ROUTEID,'_', @id)"/>
    <xsl:variable name="EVENTZOOMSLIDERID" select="concat('Slider', $ROUTEID,'_', @id)"/>
    <tr id="tr1" bgcolor="{$BACKGROUNDCOLOR}" onclick="HighlightItem(this, {@id}, -1)">
     <xsl:if test="$UseCompactMode=0">
      <td id="openroute">&#xa0;</td>
     </xsl:if>
        <td id="index">
          <a href="ZOOMTO!ID={@id}&amp;RouteID={$ROUTEID}">
            <xsl:value-of select="@id"/>
          </a>
          <xsl:text>: </xsl:text>
        </td>
        <td id="distance">
          <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='Cumul_length']/@text"/>
        </td>  
        <td id="eta">
          <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='eta']/@text"/>
        </td>
      <!--show events drop down list if necessary-->
      <xsl:choose>
        <xsl:when test="$NUMEVENTS>0">
          <script language="javascript" type="text/javascript">SetColEvents(true);</script>
          <td id="openevents">
            <div id="eventdiv">
              <div id="{$EBUTTONID}" onclick="javascript:ToggleTR('{$TRID}','{$HREFMAPIDSHOW}','{$HREFMAPIDHIDE}','{$EVENTMAPID}','{$EVENTMAPIMAGEID}','{$EVENTZOOMSLIDERID}',{$EBUTTONID},'{$EH2ID}',{$NUMEVENTS})" style="FONT-FAMILY:Courier;cursor:hand">
               <NOBR>[+]</NOBR>
              </div>
            </div>
          </td>
        </xsl:when>
        <xsl:otherwise>
          <td id="openevents">&#xa0;</td>
        </xsl:otherwise>
      </xsl:choose>
      <td id="drtext">
        <xsl:apply-templates select="NA:STRINGS">
          <xsl:with-param name="ID" select="@id"/>
          <xsl:with-param name="ROUTE_ID" select="$ROUTEID"/>
        </xsl:apply-templates>
      </td>
        <td id="dirlength">
          <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='length']/@text"/>
        </td>
        <td id="time">
          <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='time']/@text"/>
        </td>
        <td id="maplink">
          <xsl:if test="$UseCompactMode=0">
          <div id="maplinkdiv">
          <xsl:if test="count(NA:STRINGS/child::NA:STRING[attribute::style='depart'])=0 or $PATHID=1">
            <a id="{$HREFMAPIDSHOW}" href="javascript:ToggleMap({$MAPID},{$HREFMAPIDSHOW},{$HREFMAPIDHIDE},{$MAPIMAGEID},{$ZOOMSLIDERID},{$NumIsStop});">
              <xsl:value-of select="$UISHOWMAP"/>
            </a>
            <a id="{$HREFMAPIDHIDE}" href="javascript:ToggleMap({$MAPID},{$HREFMAPIDSHOW},{$HREFMAPIDHIDE},{$MAPIMAGEID},{$ZOOMSLIDERID},{$NumIsStop});" style="display:none">
              <xsl:value-of select="$UIHIDEMAP"/>
            </a>
          </xsl:if>
          </div>
          </xsl:if>
        </td>
      <td/>
    </tr>

    <!--insert row with map image-->
    <xsl:if test="$UseCompactMode=0">
      <xsl:call-template name="MAPROW">
        <xsl:with-param name="MAPID" select="$MAPID"/>
        <xsl:with-param name="BACKGROUNDCOLOR" select="$BACKGROUNDCOLOR"/>
        <xsl:with-param name="MAPFILENAME" select="$MAPFILENAME"/>
        <xsl:with-param name="MAPIMAGEID" select="$MAPIMAGEID"/>
        <xsl:with-param name="ShowSlider" select="1"/>
        <xsl:with-param name="ZOOMSLIDERID" select="$ZOOMSLIDERID"/>
        <xsl:with-param name="ID" select="@id"/>
        <xsl:with-param name="ROUTE_ID" select="$ROUTEID"/>
        <!--<xsl:with-param name="aid" select="$CommandHrefId"/>-->
      </xsl:call-template>
    </xsl:if>
    
    <xsl:if test="$NUMEVENTS>0">
      <xsl:apply-templates select="NA:EVENTS">
        <xsl:with-param name="ID" select="@id"/>
        <xsl:with-param name="ROUTE_ID" select="$ROUTEID"/>
        <xsl:with-param name="BACKGROUNDCOLOR" select="$BACKGROUNDCOLOR"/>
        <xsl:with-param name="TR_ID" select="$TRID"/>
      </xsl:apply-templates>
    </xsl:if>

  </xsl:template>

  <xsl:template match="NA:STRINGS">
    <xsl:param name="ID" select="0"/>
    <xsl:param name="ROUTE_ID" select="0"/>
    <xsl:for-each select="child::NA:STRING[attribute::style='normal' or attribute::style='depart' or attribute::style='arrive' or attribute::style='time_window' or attribute::style='violation_time' or attribute::style='wait_time' or attribute::style='service_time']">
      <div id="{@style}">
        <xsl:value-of select="@text"/>
      </div>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="NA:EVENTS">
    <xsl:param name="ID" select="0"/>
    <xsl:param name="ROUTE_ID" select="0"/>
    <xsl:param name="BACKGROUNDCOLOR" select="white"/>
    <xsl:param name="TR_ID" select="0"/>

    <xsl:for-each select="child::NA:EVENT">
      <xsl:variable name="MAPID" select="concat('EventMap_', $ROUTE_ID, '_', $ID, '_', @index)"/>
      <xsl:variable name="HREFMAPIDSHOW" select="concat('HRefMapShow', $ROUTE_ID, '_', $ID,'_', @index)"/>
      <xsl:variable name="HREFMAPIDHIDE" select="concat('HRefMapHide', $ROUTE_ID,'_', $ID,'_', @index)"/>
      <xsl:variable name="MAPIMAGEID" select="concat('EventMapImage', $ROUTE_ID,'_', $ID,'_', @index)"/>
      <xsl:variable name="ZOOMSLIDERID" select="concat('Slider', $ROUTE_ID,'_', $ID,'_', @index)"/>
      <xsl:variable name="MAPFILENAME" select="concat($OUTPUTFILENAME, $MAPID, '.jpg')"/>
      <xsl:variable name="aid" select="concat('ref', $ROUTE_ID,'_',$ID,'_',@index)"/>

      <tr id="{concat($TR_ID,'_',@index)}" bgcolor="{$BACKGROUNDCOLOR}" style="display:none" onclick="HighlightItem(this, {$ID},{@index})">
       <xsl:if test="$UseCompactMode=0">
        <td id="openroute"/>
       </xsl:if>
        <td id="index">
          <a href="ZOOMTO!ID={$ID}&amp;RouteID={$ROUTE_ID}&amp;Event={@index}">
            <xsl:value-of select="concat($ID, '.', string(position()))"/>
          </a>
          <xsl:text>:</xsl:text>
        </td>
        <td id="distance"/>
        <td id="eta">
          <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='eta']/@text"/>
        </td>
        <td id="openevents">&#xa0;</td>
        <td id="drtext">
          <div style="FONT-FAMILY:Courier;display:inline">&#xa0;&#xa0;&#xa0;&#xa0;</div>
          <div id="@index" style="display:inline">
            <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='normal']/@text"/>
          </div>
        </td>
        <td id="dirlength"/>
        <td id="time"/>
        <td id="maplink">
        <xsl:if test="$UseCompactMode=0">
          <div id="maplinkdiv">
            <a id="{$HREFMAPIDSHOW}" href="javascript:ToggleMap({$MAPID},{$HREFMAPIDSHOW},{$HREFMAPIDHIDE},{$MAPIMAGEID},{$ZOOMSLIDERID},0);">
              <xsl:value-of select="$UISHOWMAP"/>
            </a>
            <a id="{$HREFMAPIDHIDE}" href="javascript:ToggleMap({$MAPID},{$HREFMAPIDSHOW},{$HREFMAPIDHIDE},{$MAPIMAGEID},{$ZOOMSLIDERID},0);" style="display:none">
              <xsl:value-of select="$UIHIDEMAP"/>
            </a>
          </div>
        </xsl:if>
 
        </td>
        <td/>
      </tr>

      <!--insert row with map image-->
      <xsl:if test="$UseCompactMode=0">
        <xsl:call-template name="MAPROW">
          <xsl:with-param name="MAPID" select="$MAPID"/>
          <xsl:with-param name="BACKGROUNDCOLOR" select="$BACKGROUNDCOLOR"/>
          <xsl:with-param name="MAPFILENAME" select="$MAPFILENAME"/>
          <xsl:with-param name="MAPIMAGEID" select="$MAPIMAGEID"/>
          <xsl:with-param name="ShowSlider" select="1"/>
          <xsl:with-param name="ZOOMSLIDERID" select="$ZOOMSLIDERID"/>
          <xsl:with-param name="ID" select="$ID"/>
          <xsl:with-param name="ROUTE_ID" select="$ROUTE_ID"/>
          <!--<xsl:with-param name="aid" select="$CommandHrefId"/>-->
          <xsl:with-param name="EventIndex" select="@index"/>
        </xsl:call-template>
      </xsl:if>
    </xsl:for-each>
  </xsl:template>

  <xsl:template name="MAPROW">
    <!--mandatory parameters-->
    <xsl:param name="MAPID" select="0"/> <!--id of map row-->
    <xsl:param name="BACKGROUNDCOLOR" select="0"/>
    <xsl:param name="MAPFILENAME" select="0"/> <!--full file name of map image file-->
    <xsl:param name="MAPIMAGEID" select="0"/>
    <!--optional parameters, used when ShowSlider=1-->
    <xsl:param name="ShowSlider" select="0"/>
    <xsl:param name="ZOOMSLIDERID" select="0"/>
    <xsl:param name="ID" select="0"/>
    <xsl:param name="ROUTE_ID" select="0"/>
    <!--<xsl:param name="aid" select="0"/>-->
    <!--optional, used when event map needs to be shown-->
    <xsl:param name="EventIndex" select="-1"/> <!-- -1 when direction is shown, otherwise event index -->
    
    <tr style="display:none" id="{$MAPID}" bgcolor="{$BACKGROUNDCOLOR}">
      <td id="openroute">&#xa0;</td>
      <td id="mapimage" colspan="8">
        <img src="{$MAPFILENAME}" id="{$MAPIMAGEID}" style="margin-left:20px;margin-right:10px;margin-top:10px;margin-bottom:10px;border:1px solid black;"/>
        
        <!--show slider if necessary-->
        <xsl:if test="$ShowSlider=1">
          <div id="zoomcontrol" style="position: absolute; width: 30">
            <div style="position:relative;top:30;left:0">
              <img src="{$IMAGESPATH}plus.bmp" style="zindex:0;cursor:hand" onclick="OnPlus({$CommandHrefId},{$ID},{$ROUTE_ID},{$MAPIMAGEID},'{$MAPFILENAME}',{$ZOOMSLIDERID},{$EventIndex});"/>
            </div>
            <div style="position:relative;top:30;left:0;height:103">
              <img src="{$IMAGESPATH}bar.bmp" style="zindex:0;cursor:hand" onclick="OnSliderClick({$CommandHrefId},{$ID},{$ROUTE_ID},{$MAPIMAGEID},'{$MAPFILENAME}',{$ZOOMSLIDERID},{$EventIndex});"/>
              <div id="{$ZOOMSLIDERID}" style="position:absolute;top:-1">
                <img src="{$IMAGESPATH}slider.bmp" style="zindex: 1"/>
              </div>
            </div>
            <div style="position:relative;top:30;left:0">
              <img src="{$IMAGESPATH}minus.bmp" style="zindex:0;cursor:hand" onclick="OnMinus({$CommandHrefId},{$ID},{$ROUTE_ID},{$MAPIMAGEID},'{$MAPFILENAME}',{$ZOOMSLIDERID},{$EventIndex});"/>
            </div>
            <!--<a id="{$aid}" style="display: none"/>-->
          </div>
        </xsl:if>
        
      </td>
    </tr>
  </xsl:template>

</xsl:stylesheet>
