<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<!-- An XSLT template that displays metadata describing geoprocessing tools in ArcGIS.

     Copyright (c) 2003-2011, Environmental Systems Research Institute, Inc. All rights reserved.
-->

  <xsl:output method="xml" indent="yes" encoding="UTF-8" doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN" doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd" />
	
	<xsl:variable name="hasArcGISmetadata">
		<xsl:choose>
			<xsl:when test="(/metadata/dataIdInfo[1]/idAbs != '') or (/metadata/dataIdInfo[1]/idPurp != '') or (/metadata/dataIdInfo[1]/searchKeys/keyword != '') or (/metadata/dataIdInfo[1]/themeKeys/keyword != '') or (/metadata/dataIdInfo[1]/placeKeys/keyword != '') or (/metadata/dataIdInfo[1]/idCredit != '') or (/metadata/dataIdInfo[1]/resConst/Consts/useLimit[1] != '')">True</xsl:when>
			<xsl:otherwise>False</xsl:otherwise>
		</xsl:choose>
	</xsl:variable>

	<xsl:template match="/">
		<html xmlns="http://www.w3.org/1999/xhtml"><xsl:text xml:space="preserve">&#x0D;&#x0A;</xsl:text>
<xsl:comment>&#x20;saved from url=(0016)http://localhost&#x20;</xsl:comment><xsl:text xml:space="preserve">&#x0D;&#x0A;</xsl:text>
			<head>
				<meta http-equiv="content-type" content="text/html; charset=UTF-8"/>
				<xsl:call-template name="styles" />
			</head>
			<body oncontextmenu="return true">
				<xsl:call-template name="gp"/>
			</body>
		</html>
	</xsl:template>
	
	<xsl:template name="gp">
		<h1 class="gpHeading">
			<xsl:value-of select="//tool/@displayname | //toolbox/@name"/>
		</h1>
		
		<h2 class="gp">Title&#x2003;
		<xsl:choose>
		  <xsl:when test="(/metadata/dataIdInfo[1]/idCitation/resTitle != '')">
			<span class="gpsubtitle"><xsl:value-of select="/metadata/dataIdInfo[1]/idCitation/resTitle[1]" /></span>
		  </xsl:when>
		  <xsl:otherwise>
			<span class="noContent">Title</span>
		  </xsl:otherwise>
		</xsl:choose>
		</h2>

		<xsl:apply-templates select="//tool" />
		<xsl:apply-templates select="//toolbox" />
		<xsl:apply-templates select="//SpatialAnalystFunction"/>
		
	</xsl:template>

	<!--TOOL BOX -->
	<xsl:template match="//toolbox" >
		<!-- AGOL Description/Metadata Abstract/Toolbox Summary -->
		<h2 class="gp">Description</h2>
		<div class="gpItemInfo">
		<xsl:choose>
			<xsl:when test="(//toolbox/summary != '')">
				<p>
					<xsl:call-template name="gpElementSupportingMarkup">
						<xsl:with-param name="ele" select="//toolbox/summary" />
					</xsl:call-template>
				</p><br/>
			</xsl:when>
			<xsl:when test="(/metadata/dataIdInfo[1]/idAbs != '') and ($hasArcGISmetadata = 'True')">
				<p>
					<xsl:call-template name="gpElementSupportingMarkup">
						<xsl:with-param name="ele" select="/metadata/dataIdInfo[1]/idAbs" />
					</xsl:call-template>
				</p><br/>
			</xsl:when>
			<xsl:when test="/metadata/idinfo/descript/abstract[(. != '') and not(contains(text(), 'REQUIRED')) and ($hasArcGISmetadata = 'False')]">
				<xsl:apply-templates select="/metadata/idinfo/descript/abstract" />
			</xsl:when>
			<xsl:otherwise>
				<p><span class="noContent">There is no description for this item.</span></p>
			</xsl:otherwise>
		</xsl:choose>
		</div>

		<!-- can't display embedded images when information is displayed from the Help options in the context menu and the Properties dialog box -->
		<!-- Thumbnail/Toolbox Illustration -->
		<!--
		<xsl:if test="/metadata/Binary/Thumbnail/img[@src != '']">
			<h2 class="gp">Illustration</h2>
			<div>
				<xsl:apply-templates select="/metadata/Binary/Thumbnail" />
			</div>
		</xsl:if>
		-->

		<!-- Toolsets -->
		<xsl:if test="toolsets/*">
			<h2 class="gp">Toolsets</h2>
			<dl>
				<xsl:apply-templates select="toolsets" />
			</dl>
		</xsl:if>
		
		<!-- AGOL Summary/Metadata Purpose -->
        <h2 class="gp">Summary</h2>
        <div class="gpItemInfo">
			<xsl:choose>
				<xsl:when test="(/metadata/dataIdInfo[1]/idPurp != '') and ($hasArcGISmetadata = 'True')">
					<p>
						<xsl:call-template name="gpElementSupportingMarkup">
							<xsl:with-param name="ele" select="/metadata/dataIdInfo[1]/idPurp" />
						</xsl:call-template>
					</p><br/>
				</xsl:when>
				<xsl:when test="/metadata/idinfo/descript/purpose[text() and not(contains(text(), 'REQUIRED')) and ($hasArcGISmetadata = 'False')]">
					<xsl:value-of select="/metadata/idinfo/descript/purpose[text()]"/>
				</xsl:when>
				<xsl:otherwise>
					<span class="noContent">There is no summary for this item.</span>
				</xsl:otherwise>
			</xsl:choose>
		  </div>
		
		<!-- Tags/Metadata Keywords -->
		<h2 class="gp">Tags</h2>
		<div class="gpItemInfo">
		  <p>
			<xsl:choose>
				<xsl:when test="/metadata/dataIdInfo[1]/searchKeys/keyword/text() and ($hasArcGISmetadata = 'True')">
					<xsl:for-each select="/metadata/dataIdInfo[1]/searchKeys/keyword[text()]">
					  <xsl:value-of select="."/>
					  <xsl:if test="not(position()=last())">, </xsl:if>
					</xsl:for-each>
				</xsl:when>
				<xsl:when test="/metadata/dataIdInfo[1]/themeKeys/keyword/text() or /metadata/dataIdInfo/placeKeys/keyword/text() and ($hasArcGISmetadata = 'True')">
					<xsl:for-each select="/metadata/dataIdInfo[1]/themeKeys/keyword[text()] | /metadata/dataIdInfo/placeKeys/keyword[text()]">
						<xsl:value-of select="."/>
						<xsl:if test="not(position()=last())">, </xsl:if>
					</xsl:for-each>
				</xsl:when>
				<xsl:when test="/metadata/dataIdInfo[1]/descKeys/keyword[(. != '001') and (. != '002') and (. != '003') and (. != '004') and (. != '005') and (. != '006') and (. != '007') and (. != '008') and (. != '009') and (. != '010') and ($hasArcGISmetadata = 'False')]">
					<xsl:for-each select="/metadata/dataIdInfo[1]/descKeys/keyword[(. != '001') and (. != '002') and (. != '003') and (. != '004') and (. != '005') and (. != '006') and (. != '007') and (. != '008') and (. != '009') and (. != '010') and text()]">
					  <xsl:value-of select="."/>
					  <xsl:if test="not(position()=last())">, </xsl:if>
					</xsl:for-each>
				</xsl:when>
				<xsl:when test="/metadata/idinfo/keywords/theme/themekey[text() and not(contains(text(), 'REQUIRED')) and ($hasArcGISmetadata = 'False')] or /metadata/idinfo/keywords/place/placekey[text() and ($hasArcGISmetadata = 'False')]">
					<xsl:for-each select="/metadata/idinfo/keywords/theme/themekey[text()] | /metadata/idinfo/keywords/place/placekey[text()]">
					  <xsl:value-of select="."/>
					  <xsl:if test="not(position()=last())">, </xsl:if>
					</xsl:for-each>
				</xsl:when>
				<xsl:otherwise>
					<span class="noContent">There are no tags for this item.</span>
				</xsl:otherwise>
			</xsl:choose>
		  </p>
		</div>
		  
		<!-- Credits -->
        <h2 class="gp">Credits</h2>
        <div class="gpItemInfo">
			<xsl:choose>
				<xsl:when test="(/metadata/dataIdInfo[1]/idCredit != '') and ($hasArcGISmetadata = 'True')">
					<p>
						<xsl:call-template name="gpElementSupportingMarkup">
							<xsl:with-param name="ele" select="/metadata/dataIdInfo[1]/idCredit" />
						</xsl:call-template>
					</p><br/>
				</xsl:when>
				<xsl:when test="/metadata/idinfo/datacred[text() and ($hasArcGISmetadata = 'False')]">
					<xsl:value-of select="/metadata/idinfo/datacred[text()]"/>
				</xsl:when>
				<xsl:otherwise>
					<p><span class="noContent">There are no credits for this item.</span></p>
				</xsl:otherwise>
			</xsl:choose>
		</div>
		
		<!-- Use limitation -->
		<h2 class="gp">Use limitations</h2>
		<div class="gpItemInfo">
			<xsl:choose>
				<xsl:when test="(/metadata/dataIdInfo[1]/resConst/Consts/useLimit[1] != '') and ($hasArcGISmetadata = 'True')">
					<p>
						<xsl:call-template name="gpElementSupportingMarkup">
							<xsl:with-param name="ele" select="/metadata/dataIdInfo[1]/resConst/Consts/useLimit[1]" />
						</xsl:call-template>
					</p><br/>
				</xsl:when>
				<xsl:when test="/metadata/idinfo/useconst[text() and not(contains(text(), 'REQUIRED')) and ($hasArcGISmetadata = 'False')]">
					<xsl:value-of select="/metadata/idinfo/useconst[text()]"/>
				</xsl:when>
				<xsl:otherwise>
					<p><span class="noContent">There are no use limitations for this item.</span></p>
				</xsl:otherwise>
			</xsl:choose>
		</div>
	</xsl:template>

	<!--The TOOLSETS  -->
	<xsl:template match="toolsets" >
		<xsl:choose>
			<xsl:when test="parent::toolset">
				<dl>
					<xsl:apply-templates select="*" />
				</dl>
			</xsl:when>
			<xsl:otherwise>
				<xsl:apply-templates select="toolset"  />
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<!--The TOOLSET  -->
	<xsl:template match="toolset" >
		<dd>
			<b><xsl:value-of select="@name"/></b>
			<br/>
			<div>
				<dl>
				  <dd>
					<xsl:if test="./text()">
					  <xsl:value-of select="."/>
					</xsl:if>
				  </dd>
				</dl>
				<xsl:apply-templates select="*" />
				<br/>
			</div>
			<br/>
		</dd>
	</xsl:template>

	<!--TOOL -->
	<xsl:template match="tool" >
		<!-- AGOL Description/Metadata Abstract/Tool Summary -->
		<h2 class="gp">Summary</h2>
		<div class="gpItemInfo">
			<xsl:choose>
				<xsl:when test="(//tool/summary != '')">
					<p>
						<xsl:call-template name="gpElementSupportingMarkup">
							<xsl:with-param name="ele" select="//tool/summary" />
						</xsl:call-template>
					</p><br/>
				</xsl:when>
				<xsl:when test="(/metadata/dataIdInfo[1]/idAbs != '') and ($hasArcGISmetadata = 'True')">
					<p>
						<xsl:call-template name="gpElementSupportingMarkup">
							<xsl:with-param name="ele" select="/metadata/dataIdInfo[1]/idAbs" />
						</xsl:call-template>
					</p><br/>
				</xsl:when>
				<xsl:when test="/metadata/idinfo/descript/abstract[(. != '') and not(contains(text(), 'REQUIRED')) and ($hasArcGISmetadata = 'False')]">
					<xsl:apply-templates select="/metadata/idinfo/descript/abstract" />
				</xsl:when>
				<xsl:otherwise>
					<p><span class="noContent">There is no summary for this item.</span></p>
				</xsl:otherwise>
			</xsl:choose>
		</div>

		<!-- can't display embedded images when information is displayed from the Help options in the context menu and the Properties dialog box -->
		<!-- Thumbnail/Tool Illustration -->
		<!--
		<xsl:if test="//tool/toolIllust[@src != ''] | /metadata/Binary/Thumbnail/img[@src != '']">
			<h2 class="gp">Illustration</h2>
			<div>
				<xsl:apply-templates select="//tool/toolIllust[@src != '']" />
				<xsl:apply-templates select="/metadata/Binary/Thumbnail[img/@src != '']" />
			</div>
		</xsl:if>
		-->
		<xsl:if test="//tool/toolIllust[@src != '']">
			<h2 class="gp">Illustration</h2>
			<div>
				<xsl:apply-templates select="//tool/toolIllust[@src != '']" />
			</div>
		</xsl:if>

		<!-- Tool Usage -->
		<h2 class="gp">Usage</h2>
		<div class="gpItemInfo">
			<xsl:choose>
				<xsl:when test="(//tool/usage != '')">
					<p>
						<xsl:call-template name="gpElementSupportingMarkup">
							<xsl:with-param name="ele" select="//tool/usage" />
						</xsl:call-template>
					</p><br/>
				</xsl:when>
				<xsl:otherwise>
					<p><span class="noContent">There is no usage for this tool.</span></p>
				</xsl:otherwise>
			</xsl:choose>
		</div>
		
		<!-- Tool Syntax -->
		<h2 class="gp">Syntax</h2>
		<div>
			<!-- not showing Python tool syntax in Server -->
			
			<xsl:choose>
				<xsl:when test="parameters/param">
					<xsl:call-template name="ScriptingTable"/>
				</xsl:when>
				<xsl:otherwise>
					<p><span class="noContent">There are no parameters for this tool.</span></p>
				</xsl:otherwise>
			</xsl:choose>
		</div>
		
		<!-- Code Samples -->
		<h2 class="gp">Code Samples</h2>
		<xsl:choose>
			<xsl:when test="scriptExamples/scriptExample">
				<xsl:apply-templates select="//tool/scriptExamples" />
			</xsl:when>
			<xsl:when test="scriptExample">
				<xsl:apply-templates select="scriptExample" />
			</xsl:when>
			<xsl:otherwise>
				<div class="gpItemInfo">
					<p><span class="noContent">There are no code samples for this tool.</span></p>
				</div>
			</xsl:otherwise>
		</xsl:choose>
		
		<!-- Tool Environments -->
		<!-- not showing tool environments here like in Desktop (carryover from previous releases), should they be shown? -->

		<!-- Tags/Metadata Keywords -->
		<h2 class="gp">Tags</h2>
		<div class="gpItemInfo">
		  <p>
			<xsl:choose>
				<xsl:when test="/metadata/dataIdInfo[1]/searchKeys/keyword/text() and ($hasArcGISmetadata = 'True')">
					<xsl:for-each select="/metadata/dataIdInfo[1]/searchKeys/keyword[text()]">
						<xsl:value-of select="."/>
						<xsl:if test="not(position()=last())">, </xsl:if>
					</xsl:for-each>
				</xsl:when>
				<xsl:when test="/metadata/dataIdInfo[1]/themeKeys/keyword/text() or /metadata/dataIdInfo/placeKeys/keyword/text() and ($hasArcGISmetadata = 'True')">
					<xsl:for-each select="/metadata/dataIdInfo[1]/themeKeys/keyword[text()] | /metadata/dataIdInfo/placeKeys/keyword[text()]">
						<xsl:value-of select="."/>
						<xsl:if test="not(position()=last())">, </xsl:if>
					</xsl:for-each>
				</xsl:when>
				<xsl:when test="/metadata/dataIdInfo[1]/descKeys/keyword[(. != '001') and (. != '002') and (. != '003') and (. != '004') and (. != '005') and (. != '006') and (. != '007') and (. != '008') and (. != '009') and (. != '010') and ($hasArcGISmetadata = 'False')]">
					<xsl:for-each select="/metadata/dataIdInfo[1]/descKeys/keyword[(. != '001') and (. != '002') and (. != '003') and (. != '004') and (. != '005') and (. != '006') and (. != '007') and (. != '008') and (. != '009') and (. != '010') and text()]">
					  <xsl:value-of select="."/>
					  <xsl:if test="not(position()=last())">, </xsl:if>
					</xsl:for-each>
				</xsl:when>
				<xsl:when test="/metadata/idinfo/keywords/theme/themekey[text() and not(contains(text(), 'REQUIRED')) and ($hasArcGISmetadata = 'False')] or /metadata/idinfo/keywords/place/placekey[text() and ($hasArcGISmetadata = 'False')]">
					<xsl:for-each select="/metadata/idinfo/keywords/theme/themekey[text()] | /metadata/idinfo/keywords/place/placekey[text()]">
					  <xsl:value-of select="."/>
					  <xsl:if test="not(position()=last())">, </xsl:if>
					</xsl:for-each>
				</xsl:when>
				<xsl:otherwise>
					<span class="noContent">There are no tags for this item.</span>
				</xsl:otherwise>
			</xsl:choose>
		  </p>
		</div>
		  
		<!-- Credits -->
        <h2 class="gp">Credits</h2>
        <div class="gpItemInfo">
			<xsl:choose>
				<xsl:when test="(/metadata/dataIdInfo[1]/idCredit != '') and ($hasArcGISmetadata = 'True')">
					<p>
						<xsl:call-template name="gpElementSupportingMarkup">
							<xsl:with-param name="ele" select="/metadata/dataIdInfo[1]/idCredit" />
						</xsl:call-template>
					</p><br/>
				</xsl:when>
				<xsl:when test="/metadata/idinfo/datacred[text() and ($hasArcGISmetadata = 'False')]">
					<xsl:value-of select="/metadata/idinfo/datacred[text()]"/>
				</xsl:when>
				<xsl:otherwise>
					<p><span class="noContent">There are no credits for this item.</span></p>
				</xsl:otherwise>
			</xsl:choose>
		</div>
		
		<!-- Use limitation -->
		<h2 class="gp">Use limitations</h2>
		<div class="gpItemInfo">
			<xsl:choose>
				<xsl:when test="(/metadata/dataIdInfo[1]/resConst/Consts/useLimit[1] != '') and ($hasArcGISmetadata = 'True')">
					<p>
						<xsl:call-template name="gpElementSupportingMarkup">
							<xsl:with-param name="ele" select="/metadata/dataIdInfo[1]/resConst/Consts/useLimit[1]" />
						</xsl:call-template>
					</p><br/>
				</xsl:when>
				<xsl:when test="/metadata/idinfo/useconst[text() and not(contains(text(), 'REQUIRED')) and ($hasArcGISmetadata = 'False')]">
					<xsl:value-of select="/metadata/idinfo/useconst[text()]"/>
				</xsl:when>
				<xsl:otherwise>
					<p><span class="noContent">There are no use limitations for this item.</span></p>
				</xsl:otherwise>
			</xsl:choose>
		</div>
		
		<!-- 9.3.1 Server Help used to show additional content from metadata, but not at 10 -->
	</xsl:template>

	<!-- can't display embedded images when information is displayed from the Help options in the context menu and the Properties dialog box -->
	<!-- DISPLAY EMBEDDED THUMBNAIL -->
	<!--
	<xsl:template match="/metadata/Binary/Thumbnail/img[@src]">
		<img class="gp" name="thumbnail" id="thumbnail" alt="Thumbnail" title="Thumbnail">
			<xsl:attribute name="src"><xsl:value-of select="@src"/></xsl:attribute>
		</img>
	</xsl:template>
	-->
	
	<!-- EXTERNAL TOOL ILLUSTRATION-->
	<xsl:template match="tool/toolIllust" >
		<img class="gp">
			<xsl:attribute name="src">
				<xsl:choose>
					<!--The link is a URL that starts with http:// -->
					<xsl:when test="starts-with(@src, 'http://')">
						<xsl:value-of select="@src"/>
					</xsl:when>
					<xsl:otherwise>
						<xsl:text>file://</xsl:text><xsl:value-of select="@src"/>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:attribute>
			<xsl:attribute name="alt">
				<xsl:value-of select="@alt"/>
			</xsl:attribute>
		</img>
		<xsl:if test="text()">
			<b>
				<xsl:value-of select="text()" />		
			</b>
		</xsl:if>
	</xsl:template>
	
	<xsl:template name="ScriptingTable">
		<table width="100%" border="0" cellpadding="5">
			<tbody>
				<tr>
					<th width="30%">
						<b>Parameter</b>
					</th>
					<th width="70%">
						<b>Explanation</b>
					</th>
					<!-- not showing Data Types in the Server context -->
				</tr>
				<xsl:for-each select="parameters/param">
					<tr>
						<td class="info">
							<xsl:call-template name="Script_Expression"/>
						</td>
						<td class="info" align="left">
						  <xsl:if test="(not(dialogReference) or (dialogReference = ''))"><p><span class="noContent">There is no explanation for this parameter.</span></p></xsl:if>
						  <xsl:for-each select="dialogReference[(. != '')]">
							<xsl:choose>
								<xsl:when test="(. = '') or not(node())"><p><span class="noContent">There is no dialog reference for this parameter.</span></p></xsl:when>
								<xsl:when test="para or bulletList or bullet_item or indent or subSection or bold or italics">
									<xsl:choose>
										<xsl:when test="not(name(*) != 'bullet_item')">
											<ul>
												<xsl:apply-templates select="*" />
											</ul>
										</xsl:when>
										<xsl:otherwise>
											<xsl:apply-templates select="*" />
										</xsl:otherwise>
									</xsl:choose>
								</xsl:when>
								<xsl:when test="*">
									<xsl:copy-of select="node()" />
								</xsl:when>
								<xsl:when test="text()[(contains(.,'&lt;/')) or (contains(.,'/&gt;'))]">
									<xsl:variable name="escapedHtmlText">
										<xsl:call-template name="removeMarkup">
											<xsl:with-param name="text" select="." />
										</xsl:call-template>
									</xsl:variable>
									<xsl:choose>
										<xsl:when test="($escapedHtmlText != '')">
											<xsl:value-of select="text()" disable-output-escaping="yes" />
										</xsl:when>
										<xsl:otherwise>
											<p><span class="noContent">There is no dialog reference for this parameter.</span></p>
										</xsl:otherwise>
									</xsl:choose>
								</xsl:when>
								<xsl:when test=".//text()">
									<xsl:apply-templates select="*" />
								</xsl:when>
								<xsl:when test="text()">
									<!-- <xsl:value-of select="." /> -->
									<xsl:variable name="escapedHtmlText">
										<xsl:call-template name="removeMarkup">
											<xsl:with-param name="text" select="." />
										</xsl:call-template>
									</xsl:variable>
									<xsl:call-template name="handleURLs">
										<xsl:with-param name="text" select="normalize-space($escapedHtmlText)" />
									</xsl:call-template>
								</xsl:when>
								<xsl:otherwise><p><span class="noContent">There is no dialog reference for this parameter.</span></p></xsl:otherwise>
							</xsl:choose>
						  </xsl:for-each>
						  <!-- not displaying pythonReference/commandReference in the Server context -->
						</td>
					</tr>
				</xsl:for-each>
			</tbody>
		</table>
	</xsl:template>

	<!--The Script Expression -->
	<xsl:template name="Script_Expression">
		<xsl:choose>
			<xsl:when test="@type='Required'">
				<xsl:value-of select="@name"/>
			</xsl:when>
			<xsl:when test="@type='Optional'">
				<xsl:value-of select="@name"/>
				<xsl:text> (</xsl:text>
				<xsl:value-of select="@type"/>
				<xsl:text>) </xsl:text>
			</xsl:when>
			<xsl:when test="@type='Choice'">
				<xsl:value-of select="@name"/>
			</xsl:when>
		</xsl:choose>
	</xsl:template>

	<!-- SCRIPT EXAMPLES-->
	<xsl:template match="scriptExamples">
		<xsl:for-each select="scriptExample">
			<p>
				<xsl:choose>
					<xsl:when test="(title != '')"><b><xsl:value-of select="title" /></b><br/></xsl:when>
					<xsl:otherwise><span class="noContent">There is no title for this code sample.</span><br/></xsl:otherwise>
				</xsl:choose>
			</p>
			<div class="gpItemInfo">
				<xsl:choose>
					<xsl:when test="(para != '')">
						<p>
							<xsl:call-template name="gpElementSupportingMarkup">
								<xsl:with-param name="ele" select="para" />
							</xsl:call-template>
						</p><br/>
					</xsl:when>
					<xsl:otherwise>
						<p><span class="noContent">There is no description for this code sample.</span></p>
					</xsl:otherwise>
				</xsl:choose>
			</div>
			<div class="gpcode">
				<pre class="gp"><xsl:value-of select="code"/></pre>
			</div>
		</xsl:for-each>
	</xsl:template>

	<xsl:template match="tool/scriptExample">
		<b>Script Example</b><br /><br />
		<div class="gpcode">
			<pre class="gp"><xsl:value-of select="."/></pre>
		</div>
	</xsl:template>

	<!--LINK-->
	<xsl:template match="link" >
		<a target="newWindow" class="gp">
			<xsl:attribute name="href">
				<xsl:choose>
					<!--The link is a URL that starts with http:// -->
					<xsl:when test="starts-with(@src, 'http://')">
						<xsl:value-of select="@src"/>
					</xsl:when>
					<xsl:otherwise>
						<xsl:text>file://</xsl:text>
						<xsl:value-of select="@src"/>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:attribute>
			<xsl:value-of select="." />
		</a>
	</xsl:template>

	<!--ILLUSTRATION-->
	<xsl:template match="illust" >
		<br/>
		<img class="gp">
			<xsl:attribute name="src">
				<xsl:choose>
					<!--The link is a URL that starts with http:// -->
					<xsl:when test="starts-with(@src, 'http://')">
						<xsl:value-of select="@src"/>
					</xsl:when>
					<xsl:otherwise>
						<xsl:text>file://</xsl:text>
						<xsl:value-of select="@src"/>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:attribute>
			<xsl:attribute name="alt">
				<xsl:value-of select="@alt"/>
			</xsl:attribute>
		</img>
		<p/>
	</xsl:template>
	
	<!-- BOLD-->
	<xsl:template match="bold" >
		<b>
			<xsl:apply-templates select="*|text()"  />
		</b>
	</xsl:template>

	<!-- ITALICS-->
	<xsl:template match="italics" >
		<i>
			<xsl:apply-templates select="*|text()"  />
		</i>
	</xsl:template>
	
	<!-- PARAGRAPH-->
	<xsl:template match="para[(. != '')]" >
		<p class="gp">
			<xsl:apply-templates select="*|text()"  />
		</p>
	</xsl:template>

	<!--BULLETS -->
	<xsl:template match="bulletList[(. != '')]" >
		<ul>
			<xsl:apply-templates select="*|text()" />
		</ul>
	</xsl:template>

	<xsl:template match="bullet_item[(. != '')]" >
		<li>
			<xsl:apply-templates select="*|text()"  />
		</li>
	</xsl:template>

	<!--SUBSECTION-->
	<xsl:template match="subSection" >
		<xsl:if test="*">
			<xsl:if test="(@title != '')">
				<h2 class="gp"><xsl:value-of select="@title"/></h2>
			</xsl:if>
			<dl class="gp">
				<dd>
					<xsl:apply-templates select="*|text()" />
				</dd>
			</dl>
		</xsl:if>
	</xsl:template>

	<!--INDENT-->
	<xsl:template match="indent" >
		<dl class="gp">
			<dd>
				<xsl:apply-templates select="*"  />			
			</dd>
		</dl>
	</xsl:template>

	<!-- templates for adding portions of the header to the HTML page -->

	<xsl:template name="styles">
		<style type="text/css" id="internalStyle">
		body {
		  font-family: Verdana, Gill, Helvetica, Sans-serif ;
		  font-size: 0.8em;
		  font-weight: 500;
		  color: #000020;
		  background-color: #FFFFFF;
		}
		div.itemDescription {
		  margin-right: 2em;
		  margin-bottom: 2em;
		}
		h1 {
		  font-size: 1.5em;
		  margin-top: 0;
		  margin-bottom: 5px;
		}
		h1.idHeading {
		  color: #008FAF;
		  text-align: center;
		}
		h1.gpHeading {
		  color: black;
		}
		span.idHeading {
		  color: #007799;
		  font-weight: bold;
		}
		.center {
		  text-align: center;
		  margin-top: 5px;
		  margin-bottom: 5px;
		}
		img {
		  width: 210px;
		  border-width: 1px;
		  border-style: outset;
		}
		img.center {
		  text-align: center;
		  display: block;
		  border-color: #666666;
		}
		img.enclosed {
		  width: 60%;
		}
		img.gp {
		  width: auto;
		  border-style: none;
		  margin-top: -1.2em;
		}
		.noThumbnail {
		  color: #888888;
		  font-size: 1.2em;
		  border-width: 1px;
		  border-style: solid;
		  border-color: black;
		  padding: 3em 3em;
		  position: relative;
		  text-align: center;
		  width: 210px;
		  height: 140px;
		}
		.noContent {
		  color: #888888;
		}
		.itemInfo p {
		  margin-top: -0.1em;
		}
		.itemInfo img {
		  width: auto;
		  border: none;
		}
		.gpItemInfo p {
		  margin-top: -1.2em;
		}
		div.box {
		  margin-left: 1em;
		}
		div.hide {
		  display: none;
		}
		div.show {
		  display: block;
		}
		span.hide {
		  display: none;
		}
		span.show {
		  display: inline-block;
		}
		.backToTop a {
		  color: #DDDDDD;
		  font-style: italic;
		  font-size: 0.85em;
		}
		h2 {
		  font-size: 1.2em;
		}
		h2.gp {
		  color: #00709C;
		}
		.gpsubtitle {
		  color: black;
		  font-size: 1.2em;
		  font-weight: normal;
		}
		.gptags {
		  color: black;
		  font-size: 0.8em;
		  font-weight: normal;
		}
		.head {
		  font-size: 1.3em;
		}
		a:link {
		  color: #098EA6;
		  font-weight: normal;
		  text-decoration: none;
		}
		a:visited {
		  color: #098EA6;
		  text-decoration: none;
		}
		a:link:hover, a:visited:hover {
		  color: #007799;
		  background-color: #C6E6EF;
		}
		h2.iso a {
		  color: #007799;
		  font-weight: bold;
		}
		.iso a:link {
		  color: #007799;
		  text-decoration: none;
		}
		.iso a:visited {
		  color: #007799;
		  text-decoration: none;
		}
		.iso a:link:hover, .iso a:visited:hover {
		  color: #006688;
		  background-color: #C6E6EF;
		}
		h2.fgdc a {
		  color: #888888;
		  font-weight: bold;
		}
		.fgdc a:link {
		  color: #888888;
		  text-decoration: none;
		}
		.fgdc a:visited {
		  color: #888888;
		  text-decoration: none;
		}
		.fgdc a:link:hover, .fgdc a:visited:hover {
		  color: #777777;
		  background-color: #C6E6EF;
		}
		h3 {
			font-size: 1em; 
			color: #00709C;
		}
		.backToTop {
		  color: #AAAAAA;
		  margin-left: 1em;
		}
		p.gp {
		  margin-top: .6em;
		  margin-bottom: .6em;
		}
		ul ul {
		  list-style-type: square;
		}
		ul li.iso19139heading {
		  margin-left: -3em;
		  list-style: none;
		  font-weight: bold;
		  color: #666666;
		}
		dl {
		  margin: 0;
		  padding: 0;
		}
		dl.iso {
		  background-color: #F2F9FF;
		}
		dl.esri {
		  background-color: #F2FFF9;
		}
		dl.subtype {
		  width: 40em;
		  margin-top: 0.5em;
		  margin-bottom: 0.5em;
		  padding: 0;
		}
		dt {
		  margin-left: 0.6em;
		  padding-left: 0.6em;
		  clear: left;
		}
		.subtype dt {
		  width: 60%;
		  float: left;
		  margin: 0;
		  padding: 0.5em 0.5em 0 0.75em;
		  border-top: 1px solid #006400;
		  clear: none;
		}
		.subtype dt.header {
		  padding: 0.5em 0.5em 0.5em 0;
		  border-top: none;
		}
		dd {
		  margin-left: 0.6em;
		  padding-left: 0.6em;
		  clear: left;
		}
		.subtype dd {
		  float: left;
		  width: 25%;
		  margin: 0;
		  padding: 0.5em 0.5em 0 0.75em;
		  border-top: 1px solid #006400;
		  clear: none;
		}
		.subtype dd.header {
		  padding: 0.5em 0.5em 0.5em 0;
		  border-top: none;
		}
		.isoElement {
		  font-variant: small-caps;
		  font-size: 0.9em;
		  font-weight: normal;
		  color: #006688;
		}
		.esriElement {
		  font-variant: small-caps;
		  font-size: 0.9em;
		  font-weight: normal;
		  color: #006688;
		}
		.element {
		  font-variant: small-caps;
		  font-size: 0.9em;
		  font-weight: normal;
		  color: #666666;
		}
		unknownElement {
		  font-variant: small-caps;
		  font-size: 0.9em;
		  font-weight: normal;
		  color: #333333;
		}
		.sync {
		  color: #006400;
		  font-weight: bold;
		  font-size: 0.9em;
		}
		.syncOld {
		  color: #888888;
		  font-weight: bold;
		  font-size: 0.9em;
		}
		.textOld {
		  color: #999999;
		}
		.code {
		  font-family: monospace;
		}
		pre.wrap {
		  width: 96%;
		  font-family: Verdana, Gill, Helvetica, Sans-serif ;
		  font-size: 1em;
		  margin: 0 0 1em 0.6em;
		  white-space: pre-wrap;       /* css-3 */
		  white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
		  white-space: -pre-wrap;      /* Opera 4-6 */
		  white-space: -o-pre-wrap;    /* Opera 7 */
		  word-wrap: break-word;       /* Internet Explorer 5.5+ */
		}
		pre.gp {
		  font-family: Courier New, Courier, monospace;
		  line-height: 1.2em;
		}
		.gpcode {
		  margin-left:15px;
		  border: 1px dashed #ACC6D8;
		  padding: 10px;
		  background-color:#EEEEEE;
		  height: auto;
		  overflow: scroll; 
		  width: 96%;
		}
		tr {
		  vertical-align: top;
		}
		th {
		  text-align: left;
		  background: #dddddd;
		  vertical-align: bottom;
		  font-size: 0.8em;
		}
		td {
		  background: #EEEEEE;
		  color: black;
		  vertical-align: top;
		  font-size: 0.8em;
		}
		td.description {
		  background: white;
		}
	  </style>
	</xsl:template>

	<xsl:template name="removeMarkup">
		<xsl:param name="text" />
		<xsl:variable name="lessThan">&lt;</xsl:variable>
		<xsl:variable name="greaterThan">&gt;</xsl:variable>
		
		<xsl:choose>
			<xsl:when test="contains($text, $lessThan)">
				<xsl:variable name="before" select="substring-before($text, $lessThan)" />
				<xsl:variable name="middle" select="substring-after($text, $lessThan)" />
				<xsl:variable name="after" select="substring-after($middle, $greaterThan)" />
			
				<xsl:choose>
					<xsl:when test='$middle'>
						<xsl:value-of select='$before'/>
						<xsl:call-template name="removeMarkup">
							<xsl:with-param name="text" select="$after" />
						</xsl:call-template>
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="$text" />
					</xsl:otherwise>
				</xsl:choose>
			</xsl:when>
			<xsl:otherwise>
				<xsl:value-of select="$text" />
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<xsl:template name="handleURLs">
		<xsl:param name="text" />
		<xsl:variable name="replaceURL">http://</xsl:variable>
		
		<xsl:choose>
			<xsl:when test="contains($text, $replaceURL)">
				<xsl:variable name="before" select="substring-before($text, $replaceURL)" />
				<xsl:variable name="middle" select="substring-after($text, $replaceURL)" />
				
				<xsl:variable name="url" select="substring-before($middle, ' ')" />
				<xsl:variable name="after" select="substring-after($middle, $url)" />
			
				<xsl:choose>
					<xsl:when test='$after'>
						<xsl:value-of select='$before'/><a target="viewer">
							<xsl:attribute name="href"><xsl:value-of select='$replaceURL' /><xsl:value-of select='$url' /></xsl:attribute>
							<xsl:value-of select='$replaceURL' /><xsl:value-of select='$url' />
						</a>
						
						<xsl:call-template name="handleURLs">
							<xsl:with-param name="text" select="$after" />
						</xsl:call-template>
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="$text" />
					</xsl:otherwise>
				</xsl:choose>
			</xsl:when>
			<xsl:otherwise>
				<xsl:value-of select="$text" />
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>

	<xsl:template name="gpElementSupportingMarkup">
		<xsl:param name="ele" />
		<xsl:choose>
			<xsl:when test="$ele[para or bulletList or bullet_item or indent or subSection or bold or italics]">
				<xsl:choose>
					<xsl:when test="not(name($ele/*) != 'bullet_item')">
						<ul>
							<xsl:apply-templates select="$ele/*" />
						</ul>
					</xsl:when>
					<xsl:otherwise>
						<xsl:apply-templates select="$ele/*" />
					</xsl:otherwise>
				</xsl:choose>
			</xsl:when>
			<xsl:when test="$ele/*">
				<xsl:copy-of select="$ele/node()" />
			</xsl:when>
			<xsl:when test="$ele[(contains(.,'&lt;/')) or (contains(.,'/&gt;'))]">
				<xsl:variable name="escapedHtmlText">
				    <xsl:call-template name="removeMarkup">
						<xsl:with-param name="text" select="$ele" />
					</xsl:call-template>
				</xsl:variable>
				<xsl:choose>
					<xsl:when test="($escapedHtmlText != '')">
						<xsl:value-of select="$ele" disable-output-escaping="yes" />
					</xsl:when>
					<xsl:otherwise>
						<p><span class="noContent">
							<xsl:choose>
								<xsl:when test="(name($ele) = 'summary') and ((../tool) or (../../tool))">There is no summary for this item.</xsl:when>
								<xsl:when test="(name($ele) = 'summary') and ((../toolbox) or (../../toolbox))">There is no description for this tool.</xsl:when>
								<xsl:when test="(name($ele) = 'idAbs') and ((../tool) or (../../tool))">There is no summary for this item.</xsl:when>
								<xsl:when test="(name($ele) = 'idAbs') and ((../toolbox) or (../../toolbox))">There is no description for this tool.</xsl:when>
								<xsl:when test="(name($ele) = 'idPurp')">There is no summary for this item.</xsl:when>
								<xsl:when test="(name($ele) = 'idCredit')">There are no credits for this item.</xsl:when>
								<xsl:when test="(name($ele) = 'useLimit')">There are no use limitations for this item.</xsl:when>
								<xsl:when test="(name($ele) = 'usage')">There is no usage for this tool.</xsl:when>
								<xsl:when test="(name($ele) = 'para')">There are no code samples for this tool.</xsl:when>
							</xsl:choose>
						</span></p>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:when>
			<xsl:when test="$ele[(contains(.,'&amp;')) or (contains(.,'&lt;')) or (contains(.,'&gt;'))]">
				<xsl:call-template name="handleURLs">
					<xsl:with-param name="text" select="$ele" />
				</xsl:call-template>
			</xsl:when>
			<xsl:when test="$ele/text()">
				<xsl:variable name="escapedHtmlText">
					<xsl:call-template name="removeMarkup">
						<xsl:with-param name="text" select="$ele" />
					</xsl:call-template>
				</xsl:variable>
				<p><xsl:call-template name="handleURLs">
					<xsl:with-param name="text" select="normalize-space($escapedHtmlText)" />
				</xsl:call-template></p>
				<!--
					<pre class="wrap">
						<xsl:call-template name="handleURLs">
							<xsl:with-param name="text" select="." />
						</xsl:call-template>
					</pre>
				-->
			</xsl:when>
		</xsl:choose>
	</xsl:template>
	
</xsl:stylesheet>
