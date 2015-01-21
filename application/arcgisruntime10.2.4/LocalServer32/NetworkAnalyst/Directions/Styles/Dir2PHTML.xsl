<?xml version="1.0" ?>

<xsl:stylesheet
  version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:NA="http://www.esri.com/arcgis/directions"
  xmlns:ms="urn:schemas-microsoft-com:xslt">

  <xsl:strip-space elements="NA:DIRECTIONS NA:DIRECTION NA:STRINGS NA:EVENT NA:EVENTS"/> 
  <xsl:output method="html" indent="no" encoding="UTF-8"/>
  <xsl:param name="OUTPUTFILENAME" select="zero"/>
  <xsl:param name="IncludeTBTMaps" select="'false'"/>
  <xsl:param name="IncludeSVMaps" select="'false'"/>
  <xsl:param name="IncludeOMap" select="'false'"/>

  <xsl:param name="ShowDirNumColumn" select="1"/>
  <xsl:param name="ShowTimeColumn" select="1"/>
  <xsl:param name="ShowDirTimeColumn" select="1"/>
  <xsl:param name="ShowDirLengthColumn" select="1"/>
  <xsl:param name="ShowACCColumn" select="1"/>
  <xsl:param name="ShowMapLinkColumn" select="1"/>

  <xsl:param name="PageBreakStyle" select="0"/>

  <xsl:param name="UIROUTESTRING" select="'Route:'"/>
  <xsl:param name="UINULLROUTE" select="'&lt;NULL&gt;'"/>
  <xsl:param name="HTMLDIR" select="'ltr'"/>

  <xsl:variable name="FirstItemColor" select="'#fdfdf7'"/>
  <xsl:variable name="SecondItemColor" select="'#f7f7ea'"/>

  <xsl:template match="NA:DIRECTIONS">
    <xsl:variable name="DirNumColspan" select="1 + $ShowDirNumColumn + $ShowTimeColumn + $ShowACCColumn"/>
    <xsl:variable name="OMapColspan" select="1 + $ShowDirNumColumn + $ShowDirTimeColumn + $ShowDirLengthColumn + $ShowTimeColumn + $ShowACCColumn"/>
  
    <html dir="{$HTMLDIR}">
      <head>

      <style type="text/css">
         * { FONT-SIZE: 14px; FONT-FAMILY: Verdana, Arial, Helvetica, sans-serif }
        TD { padding: 3px }
        body { background-color:transparent }
        h2 { page-break-after: always }
        table { width:100% }
        #pagebreak { display: block }
        #drtext { width:3.2in;vertical-align:top }
        #index { width:0.15in;vertical-align:top }
        #length { width:0.88in;vertical-align:top;text-align:right }
        #time { width:0.88in;vertical-align:top;text-align:right }
        #eta { width:0.8in;text-align:right;vertical-align:top;padding-right:7px }
        #distance { width:0.84in;vertical-align:top;text-align:right }
        #time_window { font-size:12px;text-indent:15px }
        #violation_time { font-size:12px;color:red;text-indent:15px }
        #wait_time { font-size: 12px;text-indent:15px }
        #service_time { font-size: 12px;text-indent:15px }
      </style>

      </head>
      
      <body topmargin="0" leftmargin="0">
        <xsl:for-each select="NA:ROUTE">
          <table cellspacing="0">  
              <tr bgcolor="#e3e5c7">
                <td colspan="{$DirNumColspan}" id="route">
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
               </tr>

            <tbody>
              <xsl:if test="$IncludeOMap='true'">
                <xsl:variable name="MAPID" select="concat('PMap_',position())"/>
                <tr bgcolor="#e3e5c7">
                  <td colspan="{$OMapColspan}">
                    <img src="{$OUTPUTFILENAME}{$MAPID}.jpg" style="margin:10px;border:1px solid black;"/>
                  </td>
                  <xsl:if test="$PageBreakStyle=1">
                    <tr><td><h2/></td></tr>
                  </xsl:if>
                </tr>
              </xsl:if>
            </tbody>

            <tbody>
                       
              <xsl:apply-templates select="NA:PATH">
                <xsl:with-param name="RID" select="position()"/>
              </xsl:apply-templates>

              <xsl:call-template name="TOTALITEM">
              </xsl:call-template>

              <xsl:if test="position()&lt;last() and $PageBreakStyle=1">
                <tr><td><h2/></td></tr>
              </xsl:if>
  
            </tbody>
          </table>

        </xsl:for-each>
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
    <xsl:variable name="MAPID" select="concat('PMap_', $ROUTEID,'_',@id)"/>
    <xsl:variable name="DEPARTCOUNT" select="count(NA:STRINGS/child::NA:STRING[attribute::style='depart'])"/>
    <xsl:variable name="ARRIVECOUNT" select="count(NA:STRINGS/child::NA:STRING[attribute::style='arrive'])"/>
    <xsl:variable name="ISTBT" select="$DEPARTCOUNT=0 and $ARRIVECOUNT=0 or $ARRIVECOUNT>0 and $IncludeSVMaps='false'"/>
    <xsl:variable name="MapColspan" select="2 + $ShowDirNumColumn + $ShowDirTimeColumn + $ShowDirLengthColumn + $ShowTimeColumn + $ShowACCColumn"/>

    <tr id="tr1" bgcolor="{$BACKGROUNDCOLOR}">
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

    <xsl:if test="($IncludeTBTMaps='true' and $ISTBT) or ($IncludeSVMaps='true' and $ISTBT=false and ($DEPARTCOUNT=0 or $PATHID=1))">
      <tr bgcolor="{$BACKGROUNDCOLOR}">
        <td colspan="{$MapColspan}"><img src="{$OUTPUTFILENAME}{$MAPID}.jpg" style="margin-left:20px;margin-top:10px;margin-bottom:10px;border:1px solid black;"/></td>
      </tr>
    </xsl:if>

    <xsl:apply-templates select="NA:EVENTS">
      <xsl:with-param name="ID" select="@id"/>
      <xsl:with-param name="ROUTE_ID" select="$ROUTEID"/>
      <xsl:with-param name="BACKGROUNDCOLOR" select="$BACKGROUNDCOLOR"/>
      <xsl:with-param name="ISTBT" select="$ISTBT"/>
    </xsl:apply-templates>
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
    <xsl:param name="ISTBT" select="0"/>

      <xsl:for-each select="child::NA:EVENT">
        <xsl:variable name="MapColspan" select="2 + $ShowDirNumColumn + $ShowDirTimeColumn + $ShowDirLengthColumn + $ShowTimeColumn + $ShowACCColumn"/>
        <xsl:variable name="MAPID" select="concat('PMap_', $ROUTE_ID,'_',$ID, '_', @index + 1)"/>
        
        <tr id="tr1" bgcolor="{$BACKGROUNDCOLOR}">
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
          <xsl:if test="$ShowTimeColumn=1">
            <td id="eta">
              <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='eta']/@text"/>
            </td>
          </xsl:if>
          <td id="drtext">
            <div style="FONT-FAMILY:Courier;display:inline">&#xa0;&#xa0;&#xa0;&#xa0;</div>
            <div id="@index" style="display:inline">
              <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='normal']/@text"/>
              <!--<xsl:value-of select="$MAPID"/>-->
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

        <xsl:if test="($IncludeTBTMaps='true' and $ISTBT)">
          <tr bgcolor="{$BACKGROUNDCOLOR}">
            <td colspan="{$MapColspan}">
              <img src="{$OUTPUTFILENAME}{$MAPID}.jpg" style="margin-left:20px;margin-top:10px;margin-bottom:10px;border:1px solid black;"/>
            </td>
          </tr>
        </xsl:if>
      </xsl:for-each>
  </xsl:template>

</xsl:stylesheet>
