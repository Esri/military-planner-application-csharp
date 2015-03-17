using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using Esri.ArcGISRuntime.Layers;
using MilitaryPlanner.ViewModels;
using MilitaryPlanner.Views;
using MapView = Esri.ArcGISRuntime.Controls.MapView;
using Esri.ArcGISRuntime.Portal;
using MilitaryPlanner.Helpers;
using Esri.ArcGISRuntime.WebMap;

namespace MilitaryPlanner.Controllers
{
    class BasemapGalleryController
    {
        private readonly MapView _mapView;
        private readonly BasemapGalleryView _basemapGalleryView;
        private ArcGISPortal _arcGisPortal;

        public BasemapGalleryController(MapView mapView)
        {
            _mapView = mapView;
            
            _basemapGalleryView = new BasemapGalleryView {PlacementTarget = mapView, ViewModel = {mapView = mapView}};

            var owner = Window.GetWindow(mapView);
        
            if (owner != null)
            {
                owner.LocationChanged += (sender, e) =>
                {
                    _basemapGalleryView.HorizontalOffset += 1;
                    _basemapGalleryView.HorizontalOffset -= 1;
                };
            }

            InitializeArcGISPortal();

            Mediator.Register(Constants.ACTION_UPDATE_BASEMAP, DoUpdateBasemap);
        }

        public void Toggle()
        {
            _basemapGalleryView.ViewModel.Toggle();
        }

        private async void InitializeArcGISPortal()
        {
            _arcGisPortal = await ArcGISPortal.CreateAsync();

            // Load portal basemaps
            var result = await _arcGisPortal.ArcGISPortalInfo.SearchBasemapGalleryAsync();
            _basemapGalleryView.ViewModel.Basemaps = new ObservableCollection<ArcGISPortalItem>(result.Results);
        }

        private async void DoUpdateBasemap(object obj)
        {
            try
            {
                var item = obj as ArcGISPortalItem;

                if (item != null)
                {
                    var webmap = await WebMap.FromPortalItemAsync(item);

                    while (_mapView.Map.Layers.Any(l => l.ID == "basemap"))
                    {
                        _mapView.Map.Layers.Remove("basemap");
                    }

                    foreach (var s in webmap.Basemap.Layers.Reverse())
                    {
                        switch (s.LayerType)
                        {
                            case WebMapLayerType.ArcGISTiledMapServiceLayer:
                            case WebMapLayerType.Unknown:
                                _mapView.Map.Layers.Insert(0,new ArcGISTiledMapServiceLayer(new Uri(s.Url)){ID="basemap"});
                                break;
                            case WebMapLayerType.OpenStreetMap:
                                var layer = new OpenStreetMapLayer(){ID="basemap"};
                                _mapView.Map.Layers.Insert(0,layer);
                                break;
                            default:
                                break;
                        }
                    }
                }
            }
            catch (Exception)
            {
                
            }
        }
    }
}
