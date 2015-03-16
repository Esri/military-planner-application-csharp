using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using MilitaryPlanner.ViewModels;
using MilitaryPlanner.Views;
using MapView = Esri.ArcGISRuntime.Controls.MapView;
using Esri.ArcGISRuntime.Portal;

namespace MilitaryPlanner.Controllers
{
    class BasemapGalleryController
    {
        private readonly MapView _mapView;
        private readonly BasemapGalleryView _basemapGalleryView;

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
        }

        public void Toggle()
        {
            _basemapGalleryView.ViewModel.Toggle();
        }

        private async void InitializeArcGISPortal()
        {
            var portal = await ArcGISPortal.CreateAsync();

            // Load portal basemaps
            var result = await portal.ArcGISPortalInfo.SearchBasemapGalleryAsync();
            _basemapGalleryView.ViewModel.Basemaps = new ObservableCollection<ArcGISPortalItem>(result.Results);
        }
    }
}
