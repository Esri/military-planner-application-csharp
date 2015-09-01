// Copyright 2015 Esri 
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using ArcGIS.Desktop.Framework;
using ArcGIS.Desktop.Framework.Contracts;
using ArcGIS.Core.CIM;
using ArcGIS.Desktop.Framework.Threading.Tasks;
using Microsoft.Win32;
using System.Xml.Linq;
using ArcGIS.Desktop.Mapping;
using ArcGIS.Core.Data;

namespace arcgis_pro_import_feature_templates
{
    internal class ImportFeaturesTemplateButton : Button
    {
        private JointMilitarySymbologyLibrary.Librarian _librarian = null;

        protected async override void OnClick()
        {
            CIMFeatureTemplate cimFT;
            List<CIMFeatureTemplate> list = new List<CIMFeatureTemplate>();

            var ps = new ArcGIS.Desktop.Framework.Threading.Tasks.CancelableProgressorSource("Importing feature templates", "Canceled");

            await QueuedTask.Run(() =>
            {
                InitializeLibrarian();

                // browse file dialog

                var ofd = new OpenFileDialog
                {
                    Filter = "xml files (*.xml)|*.xml",
                    RestoreDirectory = true,
                    Multiselect = false
                };

                if (ofd.ShowDialog() == true)
                {
                    var doc = XDocument.Load(ofd.FileName);

                    var elements = from el in doc.Descendants("Children").Descendants("Children").Where(node => node.Elements("Name").Any())
                                   select new
                                   {
                                       eName = el.Element("Name").Value,
                                       eSIC = el.Element("SIC").Value
                                   };

                    foreach (var item in elements)
                    {
                        var s = _librarian.MakeSymbol("2525C", item.eSIC);

                        cimFT = new CIMFeatureTemplate();
                        switch(s.GeometryType)
                        {
                            case JointMilitarySymbologyLibrary.GeometryType.POINT:
                                cimFT.Tags = "Point";
                                cimFT.ToolProgID = "2a8b3331-5238-4025-972e-452a69535b06";
                                break;
                            case JointMilitarySymbologyLibrary.GeometryType.LINE:
                                // JointMilitarySymbologyLibrary only works with points
                                cimFT.Tags = "Line";
                                break;
                            case JointMilitarySymbologyLibrary.GeometryType.AREA:
                                // JointMilitarySymbologyLibrary only work with points
                                cimFT.Tags = "Polygon";
                                break;
                            default:
                                break;
                        }
                        cimFT.Name = item.eName;
                        cimFT.DefaultValues = new Dictionary<string, object>
                            {
                                {"identity",s.SIDC.PartAString.Substring(2,2)},
                                {"context", s.SIDC.PartAString.Substring(6,1)},
                                {"symbolset", s.SIDC.PartAString.Substring(4,2)},
                                {"entity", s.SIDC.PartBString.Substring(0,6)}
                            };

                        list.Add(cimFT);
                    }
                }
            });

            if (MapView.Active != null && list.Any())
            {
                // get toc highlighted layers
                var selLayers = MapView.Active.GetSelectedLayers();
                // retrieve the first one
                Layer layer = selLayers.FirstOrDefault();
                if (layer != null)
                {
                    // find the CIM and serialize it                    
                    await QueuedTask.Run(() =>
                    {
                        if (layer is FeatureLayer)
                        {
                            AddMatchingSymbolSetsToLayer(layer, list);
                        }
                        else if (layer is GroupLayer)
                        {
                            var gl = layer as GroupLayer;
                            var layerList = gl.GetLayersAsFlattenedList();

                            foreach (var layerItem in layerList)
                            {
                                if (layerItem is FeatureLayer)
                                {
                                    AddMatchingSymbolSetsToLayer(layerItem, list);
                                }
                            }
                        }
                    }, ps.Progressor);
                }
            }
        }

        private void AddMatchingSymbolSetsToLayer(Layer layer, List<CIMFeatureTemplate> list)
        {
            // get layer symbol codes, "symbolset"
            var symbolCodeList = new List<string>();
            var fl = layer as FeatureLayer;

            if (fl.GetTable().GetDatastore() is UnknownDatastore)
                return;
            using (var table = fl.GetTable())
            {
                IReadOnlyList<ArcGIS.Core.Data.Subtype> readOnlyList;
                try
                {
                    var tableDef = table.GetDefinition();
                    readOnlyList = tableDef.GetSubtypes();
                    var fieldIndex = tableDef.FindField("symbolset");
                    if (fieldIndex >= 0)
                    {
                        var fieldValue = tableDef.GetFields().ElementAt(fieldIndex).GetDefaultValue();
                        if (fieldValue != null)
                        {
                            symbolCodeList.Add(fieldValue.ToString());
                        }
                    }
                }
                catch (Exception e)
                {
                    return;
                }
                foreach (var subtype in readOnlyList)
                {
                    //var name = subtype.GetName();
                    var code = subtype.GetCode().ToString();
                    if (!symbolCodeList.Contains(code))
                    {
                        symbolCodeList.Add(code);
                    }
                }
            }

            var filteredList = list.Where(t => symbolCodeList.Contains(t.DefaultValues["symbolset"].ToString()));

            if (filteredList != null && filteredList.Any())
            {
                CIMBaseLayer cim = layer.GetDefinition();

                var cimFL = ((CIMFeatureLayer)cim);

                if (cimFL != null)
                {
                    if (cimFL.FeatureTemplates != null && cimFL.FeatureTemplates.Any())
                    {
                        var tempList = cimFL.FeatureTemplates.ToList();
                        tempList.AddRange(filteredList);
                        cimFL.FeatureTemplates = tempList.ToArray();
                    }
                    else
                    {
                        cimFL.FeatureTemplates = filteredList.ToArray();
                    }

                    layer.SetDefinition(cim);
                }
            }

        }


        private void InitializeLibrarian()
        {
            if (_librarian == null)
            {
                _librarian = new JointMilitarySymbologyLibrary.Librarian();
                //_librarian.IsLogging = true;
            }
        }
    }
}
