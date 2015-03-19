// Copyright 2015 Esri 
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Windows;
using Esri.ArcGISRuntime.Layers;
using Esri.ArcGISRuntime.Portal;
using Esri.ArcGISRuntime.WebMap;
using MilitaryPlanner.Helpers;
using MilitaryPlanner.Views;
using MapView = Esri.ArcGISRuntime.Controls.MapView;

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

            _basemapGalleryView = new BasemapGalleryView { PlacementTarget = mapView, ViewModel = { mapView = mapView } };

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
