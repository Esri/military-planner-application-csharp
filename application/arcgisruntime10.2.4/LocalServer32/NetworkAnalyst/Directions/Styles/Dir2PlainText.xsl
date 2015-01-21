<?xml version="1.0" ?>

<xsl:stylesheet
  version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:NA="http://www.esri.com/arcgis/directions">
  <xsl:param name="OUTPUTFILENAME" select="zero"/>

  <xsl:param name="ShowDirNumColumn" select="1"/>
  <xsl:param name="ShowTimeColumn" select="1"/>
  <xsl:param name="ShowDirTimeColumn" select="1"/>
  <xsl:param name="ShowDirLengthColumn" select="1"/>
  <xsl:param name="ShowACCColumn" select="1"/>
  <xsl:param name="ShowMapLinkColumn" select="1"/>

  <xsl:param name="UIROUTEBEGIN" select="'Begin route'"/>
  <xsl:param name="UIROUTEEND" select="'End of route'"/>
  <xsl:param name="UINULLROUTE" select="'&lt;NULL&gt;'"/>

  <xsl:strip-space elements="NA:DIRECTIONS NA:DIRECTION NA:STRINGS NA:EVENTS NA:EVENT"/> 
  <xsl:output method="text" indent="no" encoding="UTF-8"/>

  <xsl:template match="NA:DIRECTIONS">
    <xsl:for-each select="NA:ROUTE">
      <xsl:value-of select="$UIROUTEBEGIN"/>
      <xsl:text> </xsl:text>
      <xsl:choose>
        <xsl:when test="@name=''">
        <xsl:value-of select="UINULLROUTE"/>
        </xsl:when> 
        <xsl:otherwise>
          <xsl:value-of select="@name"/>         
        </xsl:otherwise>
      </xsl:choose>
      <xsl:text>&#13;&#10;&#13;&#10;</xsl:text>
      
      <xsl:apply-templates select="NA:PATH">
        <xsl:with-param name="RID" select="position()"/>
      </xsl:apply-templates>

      <xsl:call-template name="TOTALITEM"/>

      <xsl:text>&#13;&#10;</xsl:text>

      <xsl:value-of select="$UIROUTEEND"/>
      <xsl:text> </xsl:text>
      <xsl:choose>
        <xsl:when test="@name=''">
        <xsl:value-of select="UINULLROUTE"/>
        </xsl:when> 
        <xsl:otherwise>
          <xsl:value-of select="@name"/>         
        </xsl:otherwise>
      </xsl:choose>
      <xsl:text>&#13;&#10;&#13;&#10;</xsl:text>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="NA:PATH">
    <xsl:param name="RID" select="0"/>
    <xsl:apply-templates>
      <xsl:with-param name="ROUTEID" select="$RID"/>
    </xsl:apply-templates>
  </xsl:template>

  <xsl:template match="NA:DIRECTION">
    <xsl:param name="ROUTEID" select="0"/>
    <xsl:call-template name="DIRECTIONITEM">
      <xsl:with-param name="ROUTEID" select="$ROUTEID"/>
    </xsl:call-template>
  </xsl:template>

  <xsl:template name="TOTALITEM">
    <xsl:for-each select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='normal' or attribute::style='depart' or attribute::style='arrive' or attribute::style='time_window' or attribute::style='violation_time' or attribute::style='wait_time' or attribute::style='service_time']">
      <xsl:value-of select="@text"/>
      <xsl:text>&#13;&#10;</xsl:text>
    </xsl:for-each>
    <xsl:for-each select="NA:DIRECTION/NA:STRINGS/child::NA:STRING[attribute::style='summary']">
      <xsl:value-of select="@text"/>
      <xsl:text>&#13;&#10;</xsl:text>
    </xsl:for-each>
  </xsl:template>
  
  <xsl:template name="DIRECTIONITEM">
    <xsl:param name="ROUTEID" select="0"/>
    <xsl:value-of select="@id"/>
    <xsl:text>: </xsl:text>
    <xsl:apply-templates>
      <xsl:with-param name="ID" select="@id"/>
      <xsl:with-param name="ROUTE_ID" select="$ROUTEID"/>
    </xsl:apply-templates>
  </xsl:template>

  <xsl:template match="NA:STRINGS">
    <xsl:param name="ID" select="0"/>
    <xsl:param name="ROUTE_ID" select="0"/>
    <xsl:variable name="numEvents" select="count(parent::NA:DIRECTION/NA:EVENTS/NA:EVENT)"/>
    <xsl:for-each select="child::NA:STRING[attribute::style='normal' or attribute::style='depart' or attribute::style='arrive' or attribute::style='time_window' or attribute::style='violation_time' or attribute::style='wait_time' or attribute::style='service_time']">
      <xsl:value-of select="@text"/>
      <xsl:text>&#13;&#10;</xsl:text>
    </xsl:for-each>
    <xsl:for-each select="child::NA:STRING[attribute::style='summary']">
      <xsl:value-of select="@text"/>
      <xsl:text>&#13;&#10;</xsl:text>
    </xsl:for-each>
    <xsl:if test="$numEvents = 0">
      <xsl:text>&#13;&#10;</xsl:text>
    </xsl:if>
  </xsl:template>

  <xsl:template match="NA:EVENTS">
    <xsl:param name="ID" select="0"/>
    <xsl:param name="ROUTE_ID" select="0"/>
    <xsl:for-each select="child::NA:EVENT">
      <xsl:value-of select="concat($ID, '.', position(), ': ')"/>
      <xsl:value-of select="NA:STRINGS/child::NA:STRING[attribute::style='normal']/@text"/>     
      <xsl:text>&#13;&#10;</xsl:text>
    </xsl:for-each>
    <xsl:text>&#13;&#10;</xsl:text>
  </xsl:template>

</xsl:stylesheet>

