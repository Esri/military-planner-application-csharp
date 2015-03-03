using Esri.ArcGISRuntime.Controls;
using Esri.ArcGISRuntime.Geometry;
using MilitaryPlanner.Helpers;
using MilitaryPlanner.ViewModels;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

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
            this.gotoXYToolView.ViewModel.mapView = mapView;

            Mediator.Register(Constants.ACTION_GOTO_XY_COORDINATES, OnGotoXYCoordinates);
        }

        public void Toggle()
        {
            //gotoXYToolView.ViewModel.IsToolOpen = !gotoXYToolView.ViewModel.IsToolOpen;
            gotoXYToolView.ViewModel.Toggle();
        }

        private void OnGotoXYCoordinates(object obj)
        {
            try
            {
                string coordinates = obj as string;

                if (!String.IsNullOrWhiteSpace(coordinates))
                {
                    var xy = coordinates.Split(new char[] { ';' });

                    if (xy.Count() == 2)
                    {
                        var x = Convert.ToDouble(xy[0]);
                        var y = Convert.ToDouble(xy[1]);
                        var mp = new MapPoint(x, y, SpatialReferences.Wgs84);
                        mapView.SetViewAsync(mp, 50000);
                    }
                }
            }
            catch
            {

            }
        }
    }
}
