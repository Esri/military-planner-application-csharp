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
    public class GotoXYToolController
    {
        private MapView mapView;
        private MapViewModel mapViewModel;
        private Views.GotoXYToolView gotoXYToolView;

        public GotoXYToolController(MapView mapView, MapViewModel mapViewModel)
        {
            this.mapView = mapView;
            this.mapViewModel = mapViewModel;

            this.gotoXYToolView = new Views.GotoXYToolView();
            this.gotoXYToolView.PlacementTarget = mapView;
            this.gotoXYToolView.ViewModel.mapView = mapView;

            var owner = System.Windows.Window.GetWindow(mapView);

            if (owner != null)
            {
                owner.LocationChanged += (sender, e) =>
                    {
                        gotoXYToolView.HorizontalOffset += 1;
                        gotoXYToolView.HorizontalOffset -= 1;
                    };
            }

            Mediator.Register(Constants.ACTION_GOTO_XY_COORDINATES, OnGotoXYCoordinates);
        }

        public void Toggle()
        {
            gotoXYToolView.ViewModel.Toggle();
        }

        private void OnGotoXYCoordinates(object obj)
        {
            try
            {
                var gitem = obj as GotoItem;

                var sr = SpatialReferences.Wgs84;
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
                        mapView.SetViewAsync(mp, Convert.ToDouble(gitem.Scale));
                    }
                    else
                    {
                        mapView.SetViewAsync(mp);
                    }
                }
                else
                {
                    MessageBox.Show("Failed to convert coordinate.");
                }
            }
            catch
            {
                MessageBox.Show("Failed to convert coordinate.");
            }
        }
    }
}
