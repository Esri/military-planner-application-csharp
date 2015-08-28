# arcgis-pro-import-feature-templates

This is an Esri ArcGIS Pro 1.1 SDK Add-in Prototype that can be used for importing order of battle xml files from the military planner application.

## Features

* Add-in for ArcGIS Pro 1.1
* Loads as a context menu option for group/feature layers
* Imports order of battle xml file from military planner application
* Converts MIL-STD-2525C point features to MIL-STD-2525D
	* requires [joint-military-symbology-xml](https://github.com/Esri/joint-military-symbology-xml)

## Sections

* [Requirements](#requirements)
* [Instructions](#instructions)
* [Resources](#resources)
* [Issues](#issues)
* [Contributing](#contributing)
* [Licensing](#licensing)

## Requirements

* Visual Studio 2013
* ArcGIS Pro 1.1 SDK
	* [ArcGIS Pro 1.1 SDK Requirements](https://pro.arcgis.com/en/pro-app/sdk/)
* [joint-military-symbology-xml](https://github.com/Esri/joint-military-symbology-xml)

## Instructions

### General Help

* [New to Github? Get started here.](http://htmlpreview.github.com/?https://github.com/Esri/esri.github.com/blob/master/help/esri-getting-to-know-github.html)

### Getting Started with the Import Feature Templates for ArcGIS Pro 1.1

* Building
	* Install ArcGIS Pro 1.1 SDK
	* Get required dependency github project [joint-military-symbology-xml](https://github.com/Esri/joint-military-symbology-xml)
	* To Build Using Visual Studio
		* Open solution file
		* Add joint-military-symbology-xml project
		* Add reference to newly added project
		* Build solution
	* To use MSBuild to build the solution
		* Open a Visual Studio Command Prompt: Start Menu | Visual Studio 2013 | Visual Studio Tools | Developer Command Prompt for VS2013
		* cd military-planner-application-csharp/source/arcgis-pro-import-feature-templates
		* msbuild arcgis-pro-import-feature-templates.sln /property:Configuration=Release

* Running
	* Run or debug from Visual Studio
		* NOTE : Add-in uses a progressor and this can only be seen in Release mode
	* To run from a stand-alone deployment
        * copy esriAddInX file to here C:/Users/<b>USER</b>/Documents/ArcGIS/AddIns/ArcGISPro
		* Run ArcGIS Pro

## Resources

* [ArcGIS Pro SDK](https://pro.arcgis.com/en/pro-app/sdk/)
* [ArcGIS Blog](http://blogs.esri.com/esri/arcgis/)
* ![Twitter](https://g.twimg.com/twitter-bird-16x16.png)[@EsriDefense](http://twitter.com/EsriDefense)
* [ArcGIS Solutions Website](http://solutions.arcgis.com/military/)

## Issues

Find a bug or want to request a new feature?  Please let us know by submitting an [issue](https://github.com/ArcGIS/military-planner-application-csharp/issues).

## Contributing

Anyone and everyone is welcome to contribute. Please see our [guidelines for contributing](https://github.com/esri/contributing).

## Licensing

Copyright 2015 Esri

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

A copy of the license is available in the repository's [license.txt](license.txt) file.

[](Esri Tags: Military Defense ArcGIS Runtime .NET Planning WPF ArcGISSolutions Pro Import Feature Templates)
[](Esri Language: C#) 
