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

            _gotoXyToolView = new GotoXYToolView {PlacementTarget = mapView, ViewModel = {mapView = mapView}};

            var owner = Window.GetWindow(mapView);

            if (owner != null)
            {
                owner.LocationChanged += (sender, e) =>
                    {
                        _gotoXyToolView.HorizontalOffset += 1;
                        _gotoXyToolView.HorizontalOffset -= 1;
                    };
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
