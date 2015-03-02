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
    public class GotoXYController
    {
        private MapView mapView;
        private MapViewModel mapViewModel;

        public GotoXYController(MapView mapView, MapViewModel mapViewModel)
        {
            this.mapView = mapView;
            this.mapViewModel = mapViewModel;

            Mediator.Register(Constants.ACTION_GOTO_XY_COORDINATES, OnGotoXYCoordinates);
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
