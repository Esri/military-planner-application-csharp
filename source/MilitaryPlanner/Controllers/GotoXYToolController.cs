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
using System.Windows;
using Esri.ArcGISRuntime.Geometry;
using MilitaryPlanner.Helpers;
using MilitaryPlanner.ViewModels;
using MilitaryPlanner.Views;
using MapView = Esri.ArcGISRuntime.Controls.MapView;

namespace MilitaryPlanner.Controllers
{
    public class GotoXYToolController
    {
        private readonly MapView _mapView;
        private readonly GotoXYToolView _gotoXyToolView;

        public GotoXYToolController(MapView mapView, MapViewModel mapViewModel)
        {
            _mapView = mapView;

            _gotoXyToolView = new GotoXYToolView { ViewModel = { mapView = mapView } };

            var owner = Window.GetWindow(mapView);

            if (owner != null)
            {
                _gotoXyToolView.Owner = owner;
            }

            Mediator.Register(Constants.ACTION_GOTO_XY_COORDINATES, OnGotoXYCoordinates);
        }

        public void Toggle()
        {
            _gotoXyToolView.ViewModel.Toggle();
        }

        private void OnGotoXYCoordinates(object obj)
        {
            try
            {
                var gitem = obj as GotoItem;

                var sr = SpatialReferences.Wgs84;

                if (gitem != null)
                {
                    MapPoint mp;

                    switch (gitem.Format)
                    {
                        case "DD":
                            mp = ConvertCoordinate.FromDecimalDegrees(gitem.Coordinate, sr);
                            break;
                        case "DDM":
                            mp = ConvertCoordinate.FromDegreesDecimalMinutes(gitem.Coordinate, sr);
                            break;
                        case "DMS":
                            mp = ConvertCoordinate.FromDegreesMinutesSeconds(gitem.Coordinate, sr);
                            break;
                        case "GARS":
                            mp = ConvertCoordinate.FromGars(gitem.Coordinate, sr, GarsConversionMode.Center);
                            break;
                        case "GEOREF":
                            mp = ConvertCoordinate.FromGeoref(gitem.Coordinate, sr);
                            break;
                        case "MGRS":
                            mp = ConvertCoordinate.FromMgrs(gitem.Coordinate, sr, MgrsConversionMode.Automatic);
                            break;
                        case "USNG":
                            mp = ConvertCoordinate.FromUsng(gitem.Coordinate, sr);
                            break;
                        case "UTM":
                            mp = ConvertCoordinate.FromUtm(gitem.Coordinate, sr, UtmConversionMode.None);
                            break;
                        default:
                            mp = ConvertCoordinate.FromDecimalDegrees(gitem.Coordinate, SpatialReferences.Wgs84);
                            break;
                    }

                    if (mp != null)
                    {
                        if (!String.IsNullOrWhiteSpace(gitem.Scale))
                        {
                            _mapView.SetViewAsync(mp, Convert.ToDouble(gitem.Scale));
                        }
                        else
                        {
                            _mapView.SetViewAsync(mp);
                        }
                    }
                    else
                    {
                        MessageBox.Show("Failed to convert coordinate.");
                    }
                }
            }
            catch
            {
                MessageBox.Show("Failed to convert coordinate.");
            }
        }
    }
}
