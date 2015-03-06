using System.Windows;
using Esri.ArcGISRuntime.Controls;
using Esri.ArcGISRuntime.Symbology;
using MilitaryPlanner.ViewModels;
using MilitaryPlanner.Views;
using MapView = Esri.ArcGISRuntime.Controls.MapView;

namespace MilitaryPlanner.Controllers
{
    public class ViewShedToolController
    {
        private readonly ViewShedToolView _viewShedToolView;

        public ViewShedToolController(MapView mapView, MapViewModel mapViewModel)
        {
            _viewShedToolView = new ViewShedToolView {PlacementTarget = mapView, ViewModel = {mapView = mapView}};

            var owner = Window.GetWindow(mapView);

            if (owner != null)
            {
                owner.LocationChanged += (sender, e) =>
                {
                    _viewShedToolView.HorizontalOffset += 1;
                    _viewShedToolView.HorizontalOffset -= 1;
                };
            }

            mapView.GraphicsOverlays.Add(new GraphicsOverlay() { ID = "inputOverlay", Renderer = _viewShedToolView.LayoutRoot.Resources["PointRenderer"] as Renderer });
            mapView.GraphicsOverlays.Add(new GraphicsOverlay() { ID = "ViewshedOverlay", Renderer = _viewShedToolView.LayoutRoot.Resources["ViewshedRenderer"] as Renderer });
        }

        public void Toggle()
        {
            _viewShedToolView.ViewModel.Toggle();
        }
    }
}
