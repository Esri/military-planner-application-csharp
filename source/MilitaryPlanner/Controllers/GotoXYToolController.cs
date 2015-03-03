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
                var gitem = obj as GotoItem;

                var x = Convert.ToDouble(gitem.X);
                var y = Convert.ToDouble(gitem.Y);
                var mp = new MapPoint(x, y, SpatialReferences.Wgs84);

                if (!String.IsNullOrWhiteSpace(gitem.Scale))
                {
                    mapView.SetViewAsync(mp, Convert.ToDouble(gitem.Scale));
                }
                else
                {
                    mapView.SetViewAsync(mp);
                }
            }
            catch
            {

            }
        }
    }
}
