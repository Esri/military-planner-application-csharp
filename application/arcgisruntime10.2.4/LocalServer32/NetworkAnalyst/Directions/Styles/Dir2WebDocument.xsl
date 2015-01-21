<?xml version="1.0" ?>

<xsl:stylesheet
  version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:NA="http://www.esri.com/arcgis/directions"
  xmlns:ms="urn:schemas-microsoft-com:xslt">
  <xsl:param name="OUTPUTFILENAME" select="zero"/>
  <xsl:param name="IMAGESFOLDERNAME" select="zero"/>

  <xsl:param name="ShowDirNumColumn" select="1"/>
  <xsl:param name="UseCompactMode" select="0"/>
  <xsl:param name="ShowTimeColumn" select="1"/>
  <xsl:param name="ShowDirTimeColumn" select="1"/>
  <xsl:param name="ShowDirLengthColumn" select="1"/>
  <xsl:param name="ShowACCColumn" select="1"/>
  <xsl:param name="ShowMapLinkColumn" select="1"/>

  <xsl:param name="UIROUTESTRING" select="'Route:'"/>
  <xsl:param name="UINULLROUTE" select="'&lt;NULL&gt;'"/>
  <xsl:param name="UITITLE" select="'Driving Directions'"/>
  <xsl:param name="HTMLDIR" select="'ltr'"/>
  
  <xsl:variable name="ColumnWidth" select="40 div ($ShowDirTimeColumn + $ShowDirLengthColumn + $ShowACCColumn)"/>
  <xsl:variable name="FirstItemColor" select="'#fdfdf7'"/>
  <xsl:variable name="SecondItemColor" select="'#f7f7ea'"/>

  <xsl:strip-space elements="NA:DIRECTIONS NA:DIRECTION NA:STRINGS NA:EVENTS NA:EVENT"/> 
  <xsl:output method="html" indent="no" encoding="UTF-8"/>

  <xsl:template match="NA:DIRECTIONS">
    <html dir="{$HTMLDIR}">
      <head>
        <title><xsl:value-of select="$UITITLE"/></title>

       <xsl:if test="$UseCompactMode=0">
        <style type="text/css">
         * { FONT-SIZE: 12px; FONT-FAMILY: Verdana, Arial, Helvetica, sans-serif }
         TD { padding: 3px }
         A:link { color: blue }
         A:visited { color: blue }
         h2 { display: none }
         table { width:100% }
         #openroute { width:30px; }
         #maplink { width:40px;vertical-align:top;padding-left:8px }
         #pagebreak { display: none }
         #openevents { width:30px;vertical-align:top }
         #drtext { width:410px;vertical-align:top }
         #index { width:20px; vertical-align:top }
         #length { width:75px;vertical-align:top;text-align:right }
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
        <style type="text/css">
         * { FONT-SIZE: 10px; FONT-FAMILY: Verdana, Arial, Helvetica, sans-serif }
         TD { padding: 3px }
         A:link { color: blue }
         A:visited { color: blue }
         h2 { display: none }
         table { width:100% }
         #openroute { }
         #maplink { vertical-align:top;padding-left:8px }
         #pagebreak { display: none }
         #openevents { vertical-align:top }
         #drtext { vertical-align:top }
         #index { vertical-align:top }
         #length { vertical-align:top;text-align:right }
         #time { vertical-align:top;text-align:right }
         #eta { text-align:right;vertical-align:top;padding-right:8px }
         #distance { vertical-align:top;text-align:right }
         #time_window { font-size: 9px;text-indent:15px }
         #violation_time { font-size: 9px; color: red; text-indent:15px }
         #wait_time { font-size: 9px; text-indent:15px }
         #service_time { font-size: 9px; text-indent:15px }
        </style>
       </xsl:if>
      
      <script language="javascript" type="text/javascript">
//<![CDATA[
        function ToggleBody(oTBody, oA)
        {
          if(oTBody.style.display != "none")
          {
            oTBody.style.display = "none";
            oA.innerText = "[+]";
          }
          else
          {
            oTBody.style.display = "block";
            oA.innerText = "[-]";
          }
        }

        function ToggleTR(strTR,strMapTR,oA,oh2,numEvents)
        {
          for (i = 0; i < numEvents; i++)
          {
            oTR = document.all.item(strTR + "_" + i);
            oMapTR = document.all.item(strMapTR + "_" + i);
            if(oTR.style.display != "none")
          {
            oTR.style.display = "none";
            if( oMapTR != null )
              oMapTR.style.display = "none";
          }
          else
          {
            oTR.style.display = "block";
            if( oMapTR != null )
              oMapTR.style.display = "block";
          }
          }
          if (oA.innerText == "[+]")
          {
            oh2.style.display = "none";
            oA.innerText = "[-]";
          }
          else
          {
            oh2.style.display = "block";
            oA.innerText = "[+]";
          }
        }
]]>
      </script>
      </head>

      <body topmargin="0" leftmargin="0">
        <table width="100%" cellspacing="0">
                  
          <xsl:for-each select="NA:ROUTE">
            <xsl:variable name="TBODYID" select="concat('RouteTable',position())"/>
            <xsl:variable name="BUTTONID" select="concat('Sign',position())"/>
            <xsl:variable name="TID" select="concat('Table',@id)"/>
            <xsl:variable name="MAPID" select="concat('Route_', position())"/>
            <xsl:variable name="MapColspan" select="3 + $ShowDirNumColumn + $ShowDirTimeColumn + $ShowDirLengthColumn + $ShowTimeColumn + $ShowACCColumn - $UseCompactMode"/>

            <xsl:variable name="DirNumColspan" select="2 + $ShowDirNumColumn + $ShowTimeColumn + $ShowACCColumn"/>

              <tr bgcolor="#e3e5c7">
                <xsl:if test="$UseCompactMode=0"><td id="openroute"/></xsl:if>
                <xsl:if test="$ShowDirNumColumn=1"><td id="index"/></xsl:if>
                <xsl:if test="$ShowACCColumn=1"><td id="distance"/></xsl:if>
                <xsl:if test="$ShowTimeColumn=1"><td id="eta"/></xsl:if>
                <td id="openevents"/>
                <td id="drtext"/>
                <xsl:if test="$ShowDirLengthColumn=1"><td id="length"/></xsl:if>
                <xsl:if test="$ShowDirTimeColumn=1"><td id="time"/></xsl:if>
                <td/>
              </tr>
 
            <tr id="head" bgcolor="#e3e5c7">
             <xsl:if test="$UseCompactMode=0">
              <td width="30px">
               <a name="{$TID}"/>
               <div id="{$BUTTONID}" onclick="javascript:ToggleBody({$TBODYID}, {$BUTTONID})" style="FONT-FAMILY: Courier;cursor:hand">[-]</div>
              </td>
              <td colspan="{$DirNumColspan}">
               <b>
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
               </b>
              </td>
              <xsl:if test="$ShowDirLengthColumn=1">
               <td id="length">
                <xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='length']/@text"/>
               </td>
              </xsl:if>
              <xsl:if test="$ShowDirTimeColumn=1">
               <td id="time">
                <xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='time']/@text"/>
               </td>
              </xsl:if>
              <td/>
             </xsl:if>
             <xsl:if test="$UseCompactMode=1">
              <td colspan="{$DirNumColspan + $ShowDirTimeColumn + $ShowDirLengthColumn}">
               <div>
                <b>
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
                </b>
               </div>
               <!-- add totals info -->
               <xsl:for-each select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='normal' or  attribute::style='time_window' or attribute::style='violation_time' or attribute::style='wait_time' or attribute::style='service_time' or attribute::style='summary']">
                <div id="{@style}">
                 <xsl:value-of select="@text"/>
                </div>
               </xsl:for-each>
              </td>
              <td/>
             </xsl:if>
            </tr>

            <tbody id="{$TBODYID}" style="display:block">
              
              <xsl:if test="$ShowMapLinkColumn=1">
                <tr id="{$MAPID}" bgcolor="{$SecondItemColor}">
                  <td width="30px">&#xa0;</td>
                  <td colspan="{$MapColspan}">
                    <img src="{$IMAGESFOLDERNAME}\{$MAPID}.jpg" style="margin-left:20px;margin-top:10px;margin-bottom:10px;border:1px solid black;"/>
                  </td>
                </tr>
              </xsl:if>
              
              <xsl:apply-templates select="NA:PATH">
                <xsl:with-param name="RID" select="position()"/>
              </xsl:apply-templates>

             <xsl:if test="$UseCompactMode=0">
              <xsl:call-template name="TOTALITEM">
              </xsl:call-template>
             </xsl:if>

            </tbody>
        
          </xsl:for-each>
        </table>
      </body>
    </html>
  </xsl:template>

  <xsl:template match="NA:PATH">
    <xsl:param name="RID" select="0"/>
    <xsl:apply-templates>
      <xsl:with-param name="ROUTEID" select="$RID"/>
      <xsl:with-param name="PATHID" select="@id"/>
    </xsl:apply-templates>
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
    <tr id="tr1" bgcolor="ivory">
      <td id="openroute">&#xa0;</td>
      <xsl:if test="$ShowDirNumColumn=1">
        <td id="index">&#xa0;</td>
      </xsl:if>
      <xsl:if test="$ShowACCColumn=1">
        <td id="distance">
         <xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='Cumul_length']/@text"/>
        </td>  
      </xsl:if>
      <xsl:if test="$ShowTimeColumn=1">
        <td id="eta">
          <xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='eta']/@text"/>
        </td>  
      </xsl:if>
      <td id="openevents"/>
      <td id="drtext">
        <xsl:for-each select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='normal' or  attribute::style='time_window' or attribute::style='violation_time' or attribute::style='wait_time' or attribute::style='service_time' or attribute::style='summary']">
          <div id="{@style}">
            <xsl:value-of select="@text"/>
          </div>
        </xsl:for-each>
      </td>
      <xsl:if test="$ShowDirLengthColumn=1">
        <td id="length">
          &#xa0;<!--xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='length']/@text"/-->
        </td>
      </xsl:if>
      <xsl:if test="$ShowDirTimeColumn=1">
        <td id="time">
          &#xa0;<!--xsl:value-of select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='time']/@text"/-->
        </td>
      </xsl:if>
      <td/>
    </tr>
  </xsl:template>

  <xsl:template name="DIRECTIONITEM">
    <xsl:param name="ROUTEID" select="0"/>
    <xsl:param name="PATHID" select="0"/>
    <xsl:param name="BACKGROUNDCOLOR" select="'white'"/>
    <xsl:variable name="MAPID" select="concat('Map_', $ROUTEID,'_',@id)"/>
    <xsl:variable name="MapColspan" select="3 + $ShowDirNumColumn + $ShowDirTimeColumn + $ShowDirLengthColumn + $ShowTimeColumn + $ShowACCColumn - $UseCompactMode"/>

    <xsl:variable name="EBUTTONID" select="concat('EventButton_', @id, '_', $ROUTEID)"/>
    <xsl:variable name="EH2ID" select="concat('EventH2_', @id, '_', $ROUTEID)"/>
    <xsl:variable name="NUMEVENTS" select="count(NA:EVENTS/child::NA:EVENT)"/>
    <xsl:variable name="TRID" select="concat('EventTR_', @id, '_', $ROUTEID)"/>
    <xsl:variable name="EMAPID" select="concat('EventMap_', $ROUTEID, '_', @id)"/>
    
    <tr id="tr1" bgcolor="{$BACKGROUNDCOLOR}">
     <xsl:if test="$UseCompactMode=0">
      <td id="openroute">&#xa0;</td>
     </xsl:if>
      <xsl:if test="$ShowDirNumColumn=1">
        <td id="index">
          <xsl:value-of select="@id"/>
          <xsl:text>: </xsl:text>
        </td>
      </xsl:if>
      <xsl:if test="$ShowACCColumn=1">
        <td id="distance">
          <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='Cumul_length']/@text"/>
        </td>  
      </xsl:if>
      <xsl:if test="$ShowTimeColumn=1">
        <td id="eta">
          <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='eta']/@text"/>
        </td>  
      </xsl:if>
      <xsl:choose>
        <xsl:when test="$NUMEVENTS>0">
          <td id="openevents">
            <div id="{$EBUTTONID}" onclick="javascript:ToggleTR('{$TRID}','{$EMAPID}',{$EBUTTONID},{$EH2ID},{$NUMEVENTS})" style="FONT-FAMILY:Courier;cursor:hand">[+]</div>
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
      <xsl:if test="$ShowDirLengthColumn=1">
        <td id="length">
          <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='length']/@text"/>
        </td>
      </xsl:if>
      <xsl:if test="$ShowDirTimeColumn=1">
        <td id="time">
          <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='time']/@text"/>
        </td>
      </xsl:if>
      <td/>
    </tr>

    <xsl:if test="$ShowMapLinkColumn=1 and (count(NA:STRINGS/child::NA:STRING[attribute::style='depart'])=0 or $PATHID=1)">      
      <tr bgcolor="{$BACKGROUNDCOLOR}">
        <td width="30px">&#xa0;</td>
        <td colspan="{$MapColspan}"><img src="{$IMAGESFOLDERNAME}\{$MAPID}.jpg" style="margin-left:20px;margin-top:10px;margin-bottom:10px;border:1px solid black;"/></td>
      </tr>
    </xsl:if>

    <tr id="pagebreak">
      <td id="{$EH2ID}" style="display:block">
        <xsl:if test="position()&lt;last()">
          <h2 id="pagebreakheader"/>
        </xsl:if>
      </td>
    </tr>

    <xsl:if test="$NUMEVENTS>0">
      <xsl:apply-templates select="NA:EVENTS">
        <xsl:with-param name="ID" select="@id"/>
        <xsl:with-param name="ROUTE_ID" select="$ROUTEID"/>
        <xsl:with-param name="BACKGROUNDCOLOR" select="$BACKGROUNDCOLOR"/>
        <xsl:with-param name="SHOW_ETA" select="$ShowTimeColumn"/>
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
    <xsl:param name="BACKGROUNDCOLOR" select="'white'"/>
    <xsl:param name="SHOW_ETA" select="1"/>
    <xsl:param name="TR_ID" select="0"/>

    <xsl:for-each select="child::NA:EVENT">
      <xsl:variable name="MAPID" select="concat('EventMap_', $ROUTE_ID, '_', $ID, '_', @index)"/>
      <xsl:variable name="MapColspan" select="3 + $ShowDirNumColumn + $ShowDirTimeColumn + $ShowDirLengthColumn + $ShowTimeColumn + $ShowACCColumn"/>

      <tr id="{concat($TR_ID,'_',@index)}" bgcolor="{$BACKGROUNDCOLOR}" style="display:none">
       <xsl:if test="$UseCompactMode=0">
        <td id="openroute">&#xa0;</td>
       </xsl:if>
        <xsl:if test="$ShowDirNumColumn=1">
          <td id="index">
            <xsl:value-of select="concat($ID, '.', string(position()))"/>
            <xsl:text>: </xsl:text>
          </td>
        </xsl:if>
        <xsl:if test="$ShowACCColumn=1">
          <td id="distance">
          </td>
        </xsl:if>
        <xsl:if test="$SHOW_ETA=1">
          <td id="eta">
            <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='eta']/@text"/>
          </td>
        </xsl:if>
        <td id="openevents"/>
        <td id="drtext">
          <div style="FONT-FAMILY:Courier;display:inline">&#xa0;&#xa0;&#xa0;&#xa0;</div>
          <div id="@index" style="display:inline">
            <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='normal']/@text"/>
          </div>
        </td>
        <xsl:if test="$ShowDirLengthColumn=1">
          <td id="length">
          </td>
        </xsl:if>
        <xsl:if test="$ShowDirTimeColumn=1">
          <td id="time">
          </td>
        </xsl:if>
        <td/>
      </tr>

      <xsl:if test="$ShowMapLinkColumn=1">
        <tr id="{$MAPID}" bgcolor="{$BACKGROUNDCOLOR}" style="display:none">
          <td width="30px">&#xa0;</td>
          <td colspan="{$MapColspan}">
            <img src="{$IMAGESFOLDERNAME}\{$MAPID}.jpg" style="margin-left:20px;margin-top:10px;margin-bottom:10px;border:1px solid black;"/>
          </td>
        </tr>
      </xsl:if>
    </xsl:for-each>
  </xsl:template>

</xsl:stylesheet>
