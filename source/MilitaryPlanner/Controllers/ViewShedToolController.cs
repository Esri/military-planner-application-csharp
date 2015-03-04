using Esri.ArcGISRuntime.Controls;
using Esri.ArcGISRuntime.Symbology;
using MilitaryPlanner.ViewModels;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MilitaryPlanner.Controllers
{
    public class ViewShedToolController
    {
        private Views.ViewShedToolView viewShedToolView;

        public ViewShedToolController(MapView mapView, MapViewModel mapViewModel)
        {
            viewShedToolView = new Views.ViewShedToolView();
            viewShedToolView.PlacementTarget = mapView;
            viewShedToolView.ViewModel.mapView = mapView;

            var owner = System.Windows.Window.GetWindow(mapView);

            if (owner != null)
            {
                owner.LocationChanged += (sender, e) =>
                {
                    viewShedToolView.HorizontalOffset += 1;
                    viewShedToolView.HorizontalOffset -= 1;
                };
            }

            mapView.GraphicsOverlays.Add(new GraphicsOverlay() { ID = "inputOverlay", Renderer = viewShedToolView.LayoutRoot.Resources["PointRenderer"] as Renderer });
            mapView.GraphicsOverlays.Add(new GraphicsOverlay() { ID = "ViewshedOverlay", Renderer = viewShedToolView.LayoutRoot.Resources["ViewshedRenderer"] as Renderer });
        }

        public void Toggle()
        {
            viewShedToolView.ViewModel.Toggle();
        }
    }
}
