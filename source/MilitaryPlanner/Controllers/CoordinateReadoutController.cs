using Esri.ArcGISRuntime.Controls;
using Esri.ArcGISRuntime.Geometry;
using MilitaryPlanner.Helpers;
using MilitaryPlanner.ViewModels;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;

namespace MilitaryPlanner.Controllers
{
    public class CoordinateReadoutController
    {
        private MapView mapView;
        private MapViewModel mapViewModel;

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

        private CoordinateReadoutFormat coordinateReadoutFormat = CoordinateReadoutFormat.DD;

        public CoordinateReadoutController(MapView mapView, MapViewModel mapViewModel)
        {
            this.mapView = mapView;
            this.mapViewModel = mapViewModel;

            this.mapView.MouseMove += mapView_MouseMove;

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
                        coordinateReadoutFormat = CoordinateReadoutFormat.DD;
                        break;
                    case "DMS":
                        coordinateReadoutFormat = CoordinateReadoutFormat.DMS;
                        break;
                    case "GARS":
                        coordinateReadoutFormat = CoordinateReadoutFormat.GARS;
                        break;
                    case "GEOREF":
                        coordinateReadoutFormat = CoordinateReadoutFormat.GEOREF;
                        break;
                    case "MGRS":
                        coordinateReadoutFormat = CoordinateReadoutFormat.MGRS;
                        break;
                    case "USNG":
                        coordinateReadoutFormat = CoordinateReadoutFormat.USNG;
                        break;
                    case "UTM":
                        coordinateReadoutFormat = CoordinateReadoutFormat.UTM;
                        break;
                    default:
                        coordinateReadoutFormat = CoordinateReadoutFormat.MGRS;
                        break;
                }
            }
        }

        void mapView_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
        {
            UpdateCoordinateReadout(e.GetPosition(mapView));
        }

        private void UpdateCoordinateReadout(Point point)
        {
            var mp = mapView.ScreenToLocation(point);

            if (mp == null)
                return;

            string CoordinateReadout = "";

            // we can do DD, DMS, GARS, GEOREF, MGRS, USNG, UTM
            switch (coordinateReadoutFormat)
            {
                case CoordinateReadoutFormat.DD:
                    CoordinateReadout = ConvertCoordinate.ToDecimalDegrees(mp, 3);
                    break;
                case CoordinateReadoutFormat.DMS:
                    CoordinateReadout = ConvertCoordinate.ToDegreesMinutesSeconds(mp, 1);
                    break;
                case CoordinateReadoutFormat.GARS:
                    CoordinateReadout = ConvertCoordinate.ToGars(mp);
                    break;
                case CoordinateReadoutFormat.GEOREF:
                    CoordinateReadout = ConvertCoordinate.ToGeoref(mp, 4, true);
                    break;
                case CoordinateReadoutFormat.MGRS:
                    CoordinateReadout = ConvertCoordinate.ToMgrs(mp, MgrsConversionMode.Automatic, 5, true, true);
                    break;
                case CoordinateReadoutFormat.USNG:
                    CoordinateReadout = ConvertCoordinate.ToUsng(mp, 5, true, true);
                    break;
                case CoordinateReadoutFormat.UTM:
                    CoordinateReadout = ConvertCoordinate.ToUtm(mp, UtmConversionMode.None, true);
                    break;
                default:
                    CoordinateReadout = ConvertCoordinate.ToMgrs(mp, MgrsConversionMode.Automatic, 5, true, true);
                    break;
            }

            mapViewModel.CoordinateReadout = CoordinateReadout;
        }

    }
}
