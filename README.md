# military-planner-application-csharp

This is an Esri ArcGIS Runtime for .NET application that can be used for planning military operations.  It uses ArcGIS Runtime SDK for .NET 10.2.4. Learn more about it [here](https://developers.arcgis.com/net/).

![Image of Military Planner Application](ScreenShot.PNG) 

## Features
* Time enabled layers, grouped by Courses of Action and Phases of the Operation
* Order of Battle Widget customizable for individual units
* What You See Is What You Get (WYSIWYG) editing of military symbols and control measures
* MIL-STD-2525C compliant symbology

## Sections

* [Requirements](#requirements)
* [Instructions](#instructions)
* [Resources](#resources)
* [Issues](#issues)
* [Contributing](#contributing)
* [Licensing](#licensing)

## Requirements

* Visual Studio 2012
* ArcGIS Runtime SDK for .NET 10.2.4
	* [ArcGIS Runtime for .NET Requirements](https://developers.arcgis.com/net/desktop/guide/system-requirements.htm)

## Instructions

### General Help

* [New to Github? Get started here.](http://htmlpreview.github.com/?https://github.com/Esri/esri.github.com/blob/master/help/esri-getting-to-know-github.html)

### Getting Started with the Military Planner Application (.NET)

* Building
	* To Build Using Visual Studio
		* Open and build solution file
		* Optional: Change references to use the installed SDK instead of NuGet package
			* 1. Remove / Unintstall Esri.ArcGISRuntime NuGet-package reference from the solution.
				* Click "Manage NuGet Packages for solution..." from Tools \ NuGet Package Manager
				* See Installed Packages tab and remove "Esri.ArcGISRuntime" package
			* 2. Add references to projects
			* 3. Prepare deployment
				* Windows Desktop - Delete deployment folder (arcgisruntime10.2.4) from output folder if it exists. This step makes sure that centralized developer deployment is used and no deployment is needed
* Running
	* Download and unzip the .zip file(s).  \\disldb\Shared\MilitaryPlanner\application or (https://esri.box.com/s/g6nes1k4xqjwtmgs1kanvr1ayx4m9yfg)
	* Unzip military planner application zip file
	* Unzip arcgisruntime10.2.4 folder so that you end up with ./application/arcgisruntime10.2.4  (same level as MilitaryPlanner.exe file)
		* Only need to do this once
	* Run MilitaryPlanner.exe

## Resources

* [ArcGIS Runtime for .NET Resource Center](https://developers.arcgis.com/net/)
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

A copy of the license is available in the repository's [license.txt](https://github.com/ArcGIS/military-planner-application-csharp/blob/master/license.txt) file.

[](Esri Tags: Military Defense ArcGIS Runtime .NET)
[](Esri Language: C-Sharp) 
