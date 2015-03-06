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
using System.Windows.Input;
using Esri.ArcGISRuntime.Controls;
using Esri.ArcGISRuntime.Geometry;
using MilitaryPlanner.Helpers;
using MilitaryPlanner.ViewModels;

namespace MilitaryPlanner.Controllers
{
    public class CoordinateReadoutController
    {
        private readonly MapView _mapView;
        private readonly MapViewModel _mapViewModel;

        private enum CoordinateReadoutFormat
        {
            DD,
            DMS,
            GARS,
            GEOREF,
            MGRS,
            USNG,
            UTM
        };

        private CoordinateReadoutFormat _coordinateReadoutFormat = CoordinateReadoutFormat.DD;

        public CoordinateReadoutController(MapView mapView, MapViewModel mapViewModel)
        {
            _mapView = mapView;
            _mapViewModel = mapViewModel;

            _mapView.MouseMove += mapView_MouseMove;

            Mediator.Register(Constants.ACTION_COORDINATE_READOUT_FORMAT_CHANGED, OnCoordinateReadoutFormatChanged);
        }

        private void OnCoordinateReadoutFormatChanged(object obj)
        {
            string format = obj as string;

            if (!String.IsNullOrWhiteSpace(format))
            {
                switch (format)
                {
                    case "DD":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.DD;
                        break;
                    case "DMS":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.DMS;
                        break;
                    case "GARS":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.GARS;
                        break;
                    case "GEOREF":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.GEOREF;
                        break;
                    case "MGRS":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.MGRS;
                        break;
                    case "USNG":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.USNG;
                        break;
                    case "UTM":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.UTM;
                        break;
                    default:
                        _coordinateReadoutFormat = CoordinateReadoutFormat.MGRS;
                        break;
                }
            }
        }

        void mapView_MouseMove(object sender, MouseEventArgs e)
        {
            UpdateCoordinateReadout(e.GetPosition(_mapView));
        }

        private void UpdateCoordinateReadout(Point point)
        {
            var mp = _mapView.ScreenToLocation(point);

            if (mp == null)
                return;

            string coordinateReadout;

            // we can do DD, DMS, GARS, GEOREF, MGRS, USNG, UTM
            switch (_coordinateReadoutFormat)
            {
                case CoordinateReadoutFormat.DD:
                    coordinateReadout = ConvertCoordinate.ToDecimalDegrees(mp, 3);
                    break;
                case CoordinateReadoutFormat.DMS:
                    coordinateReadout = ConvertCoordinate.ToDegreesMinutesSeconds(mp, 1);
                    break;
                case CoordinateReadoutFormat.GARS:
                    coordinateReadout = ConvertCoordinate.ToGars(mp);
                    break;
                case CoordinateReadoutFormat.GEOREF:
                    coordinateReadout = ConvertCoordinate.ToGeoref(mp, 4, true);
                    break;
                case CoordinateReadoutFormat.MGRS:
                    coordinateReadout = ConvertCoordinate.ToMgrs(mp, MgrsConversionMode.Automatic, 5, true, true);
                    break;
                case CoordinateReadoutFormat.USNG:
                    coordinateReadout = ConvertCoordinate.ToUsng(mp, 5, true, true);
                    break;
                case CoordinateReadoutFormat.UTM:
                    coordinateReadout = ConvertCoordinate.ToUtm(mp, UtmConversionMode.None, true);
                    break;
                default:
                    coordinateReadout = ConvertCoordinate.ToMgrs(mp, MgrsConversionMode.Automatic, 5, true, true);
                    break;
            }

            _mapViewModel.CoordinateReadout = coordinateReadout;
        }

    }
}
