using Esri.ArcGISRuntime.Controls;
using Esri.ArcGISRuntime.Geometry;
using Esri.ArcGISRuntime.Layers;
using Esri.ArcGISRuntime.Symbology;
using Esri.ArcGISRuntime.Tasks.NetworkAnalyst;
using MilitaryPlanner.ViewModels;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;

namespace MilitaryPlanner.Controllers
{
    public class NetworkingToolController
    {
        private MapView mapView;
        private MapViewModel mapViewModel;
        private Views.NetworkingToolView networkingToolView;

        private const string OnlineRoutingService = "http://sampleserver6.arcgisonline.com/arcgis/rest/services/NetworkAnalysis/SanDiego/NAServer/Route";

        private OnlineRouteTask _routeTask;
        private Symbol _directionPointSymbol;
        private GraphicsOverlay _stopsOverlay;
        private GraphicsOverlay _routesOverlay;
        private GraphicsOverlay _directionsOverlay;

        public NetworkingToolController(MapView mapView, MapViewModel mapViewModel)
        {
            this.mapView = mapView;
            this.mapViewModel = mapViewModel;

            this.networkingToolView = new Views.NetworkingToolView();
            this.networkingToolView.PlacementTarget = mapView;
            this.networkingToolView.ViewModel.mapView = mapView;

            var owner = System.Windows.Window.GetWindow(mapView);

            if (owner != null)
            {
                owner.LocationChanged += (sender, e) =>
                {
                    networkingToolView.HorizontalOffset += 1;
                    networkingToolView.HorizontalOffset -= 1;
                };
            }

            // hook mapview events
            mapView.MapViewTapped += mapView_MapViewTapped;
            mapView.MapViewDoubleTapped += mapView_MapViewDoubleTapped;

            // hook listDirections
            networkingToolView.listDirections.SelectionChanged += listDirections_SelectionChanged;

            // hook view resources
            _directionPointSymbol = networkingToolView.LayoutRoot.Resources["directionPointSymbol"] as Symbol;

            mapView.GraphicsOverlays.Add(new GraphicsOverlay() { ID="RoutesOverlay", Renderer=networkingToolView.LayoutRoot.Resources["routesRenderer"] as Renderer});
            mapView.GraphicsOverlays.Add(new GraphicsOverlay() { ID="StopsOverlay" });
            mapView.GraphicsOverlays.Add(new GraphicsOverlay() { ID = "DirectionsOverlay", Renderer=networkingToolView.LayoutRoot.Resources["directionsRenderer"] as Renderer, SelectionColor=System.Windows.Media.Colors.Red });

            _stopsOverlay = mapView.GraphicsOverlays["StopsOverlay"];
            _routesOverlay = mapView.GraphicsOverlays["RoutesOverlay"];
            _directionsOverlay = mapView.GraphicsOverlays["DirectionsOverlay"];

            _routeTask = new OnlineRouteTask(new Uri(OnlineRoutingService));
        }

        public void Toggle()
        {
            networkingToolView.ViewModel.Toggle();

            if (!networkingToolView.ViewModel.IsToolOpen)
            {
                Reset();
            }
        }

        private void Reset()
        {
            // clean up
            networkingToolView.ViewModel.PanelResultsVisibility = System.Windows.Visibility.Collapsed;

            _stopsOverlay.Graphics.Clear();
            _routesOverlay.Graphics.Clear();
            _directionsOverlay.GraphicsSource = null;
        }

        private void mapView_MapViewTapped(object sender, MapViewInputEventArgs e)
        {
            if (!networkingToolView.ViewModel.IsToolOpen)
                return;

            try
            {
                e.Handled = true;

                if (_directionsOverlay.Graphics.Count() > 0)
                {
                    Reset();
                }

                var graphicIdx = _stopsOverlay.Graphics.Count + 1;
                _stopsOverlay.Graphics.Add(CreateStopGraphic(e.Location, graphicIdx));
            }
            catch (System.Exception ex)
            {
                MessageBox.Show(ex.Message, "Sample Error");
            }
        }

        private async void mapView_MapViewDoubleTapped(object sender, MapViewInputEventArgs e)
        {
            if (!networkingToolView.ViewModel.IsToolOpen)
                return;

            if (_stopsOverlay.Graphics.Count() < 2)
                return;

            try
            {
                e.Handled = true;

                //panelResults.Visibility = Visibility.Collapsed;
                networkingToolView.ViewModel.PanelResultsVisibility = Visibility.Collapsed;
                //progress.Visibility = Visibility.Visible;
                networkingToolView.ViewModel.ProgressVisibility = Visibility.Visible;

                RouteParameters routeParams = await _routeTask.GetDefaultParametersAsync();
                routeParams.OutSpatialReference = mapView.SpatialReference;
                routeParams.ReturnDirections = true;
                routeParams.DirectionsLengthUnit = LinearUnits.Miles;
                routeParams.DirectionsLanguage = new CultureInfo("en-Us"); // CultureInfo.CurrentCulture;
                routeParams.SetStops(_stopsOverlay.Graphics);

                var routeResult = await _routeTask.SolveAsync(routeParams);
                if (routeResult == null || routeResult.Routes == null || routeResult.Routes.Count() == 0)
                    throw new Exception("No route could be calculated");

                var route = routeResult.Routes.First();
                _routesOverlay.Graphics.Add(new Graphic(route.RouteFeature.Geometry));

                _directionsOverlay.GraphicsSource = route.RouteDirections.Select(rd => GraphicFromRouteDirection(rd));
                //listDirections.ItemsSource = _directionsOverlay.Graphics;
                networkingToolView.ViewModel.Graphics = _directionsOverlay.Graphics;

                var totalTime = route.RouteDirections.Select(rd => rd.Time).Aggregate(TimeSpan.Zero, (p, v) => p.Add(v));
                var totalLength = route.RouteDirections.Select(rd => rd.GetLength(LinearUnits.Miles)).Sum();
                //txtRouteTotals.Text = string.Format("Time: {0:h':'mm':'ss} / Length: {1:0.00} mi", totalTime, totalLength);
                networkingToolView.ViewModel.RouteTotals = string.Format("Time: {0:h':'mm':'ss} / Length: {1:0.00} mi", totalTime, totalLength);

                if (!route.RouteFeature.Geometry.IsEmpty)
                    await mapView.SetViewAsync(route.RouteFeature.Geometry.Extent.Expand(1.25));
            }
            catch (AggregateException ex)
            {
                var innermostExceptions = ex.Flatten().InnerExceptions;
                if (innermostExceptions != null && innermostExceptions.Count > 0)
                {
                    MessageBox.Show(innermostExceptions[0].Message, "Sample Error");
                }
                else
                {
                    MessageBox.Show(ex.Message, "Sample Error");
                }
                Reset();
            }
            catch (System.Exception ex)
            {
                MessageBox.Show(ex.Message, "Sample Error");
                Reset();
            }
            finally
            {
                //progress.Visibility = Visibility.Collapsed;
                networkingToolView.ViewModel.ProgressVisibility = Visibility.Collapsed;
                if (_directionsOverlay.Graphics.Count() > 0)
                {
                    //panelResults.Visibility = Visibility.Visible;
                    networkingToolView.ViewModel.PanelResultsVisibility = Visibility.Visible;
                }
            }
        }

        void listDirections_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
        {
            _directionsOverlay.ClearSelection();

            if (e.AddedItems != null && e.AddedItems.Count == 1)
            {
                var graphic = e.AddedItems[0] as Graphic;
                graphic.IsSelected = true;
            }
        }

        private Graphic CreateStopGraphic(MapPoint location, int id)
        {
            var symbol = new CompositeSymbol();
            symbol.Symbols.Add(new SimpleMarkerSymbol() { Style = SimpleMarkerStyle.Circle, Color = Colors.Blue, Size = 16 });
            symbol.Symbols.Add(new TextSymbol()
            {
                Text = id.ToString(),
                Color = Colors.White,
                VerticalTextAlignment = VerticalTextAlignment.Middle,
                HorizontalTextAlignment = HorizontalTextAlignment.Center,
                YOffset = -1
            });

            var graphic = new Graphic()
            {
                Geometry = location,
                Symbol = symbol
            };

            return graphic;
        }

        private Graphic GraphicFromRouteDirection(RouteDirection rd)
        {
            var graphic = new Graphic(rd.Geometry);
            graphic.Attributes.Add("Direction", rd.Text);
            graphic.Attributes.Add("Time", string.Format("{0:h\\:mm\\:ss}", rd.Time));
            graphic.Attributes.Add("Length", string.Format("{0:0.00}", rd.GetLength(LinearUnits.Miles)));
            if (rd.Geometry is MapPoint)
                graphic.Symbol = _directionPointSymbol;

            return graphic;
        }

    }
}
