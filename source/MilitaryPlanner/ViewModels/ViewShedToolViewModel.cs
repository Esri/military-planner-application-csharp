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
using System.Linq;
using System.Windows;
using Esri.ArcGISRuntime.Controls;
using Esri.ArcGISRuntime.Geometry;
using Esri.ArcGISRuntime.Layers;
using Esri.ArcGISRuntime.Tasks.Geoprocessing;
using MilitaryPlanner.Helpers;

namespace MilitaryPlanner.ViewModels
{
    public class ViewShedToolViewModel : BaseToolViewModel
    {
        public RelayCommand StartViewShedCommand { get; set; }
        public RelayCommand CloseViewShedCommand { get; set; }

        public ViewShedToolViewModel()
        {
            StartViewShedCommand = new RelayCommand(OnStartViewShedCommand);
            CloseViewShedCommand = new RelayCommand(OnCloseViewShedCommand);

            _gpTask = new Geoprocessor(new Uri(ViewshedServiceUrl));
        }

        private void OnCloseViewShedCommand(object obj)
        {
            IsToolOpen = false;

            if (_inputOverlay != null)
            {
                _inputOverlay.Graphics.Clear();
            }

            if (_viewshedOverlay != null)
            {
                _viewshedOverlay.Graphics.Clear();
            }
        }

        //viewshed
        private const string ViewshedServiceUrl = "http://sampleserver6.arcgisonline.com/arcgis/rest/services/Elevation/ESRI_Elevation_World/GPServer/Viewshed";

        private GraphicsOverlay _inputOverlay;
        private GraphicsOverlay _viewshedOverlay;
        private readonly Geoprocessor _gpTask;

        private bool _viewShedEnabled = true;
        public bool ViewShedEnabled
        {
            get
            {
                return _viewShedEnabled;
            }
            set
            {
                _viewShedEnabled = value;
                RaisePropertyChanged(() => ViewShedEnabled);
            }
        }

        private Visibility _viewShedProgressVisible = Visibility.Collapsed;
        public Visibility ViewShedProgressVisible
        {
            get
            {
                return _viewShedProgressVisible;
            }
            set
            {
                _viewShedProgressVisible = value;
                RaisePropertyChanged(() => ViewShedProgressVisible);
            }
        }

        private string _toolStatus = "";
        public string ToolStatus
        {
            get
            {
                return _toolStatus;
            }
            set
            {
                _toolStatus = value;
                RaisePropertyChanged(() => ToolStatus);
            }
        }

        private async void OnStartViewShedCommand(object obj)
        {
            try
            {
                _inputOverlay = mapView.GraphicsOverlays["inputOverlay"];
                _viewshedOverlay = mapView.GraphicsOverlays["ViewshedOverlay"];

                string txtMiles = obj as string;

                ViewShedEnabled = false;
                _inputOverlay.Graphics.Clear();
                _viewshedOverlay.Graphics.Clear();

                //get the user's input point
                var inputPoint = await mapView.Editor.RequestPointAsync();

                ViewShedProgressVisible = Visibility.Visible;
                _inputOverlay.Graphics.Add(new Graphic() { Geometry = inputPoint });

                var parameter = new GPInputParameter() { OutSpatialReference = SpatialReferences.WebMercator };
                parameter.GPParameters.Add(new GPFeatureRecordSetLayer("Input_Observation_Point", inputPoint));
                parameter.GPParameters.Add(new GPLinearUnit("Viewshed_Distance ", LinearUnits.Miles, Convert.ToDouble(txtMiles)));

                ToolStatus = "Processing on server...";
                var result = await _gpTask.ExecuteAsync(parameter);
                if (result == null || result.OutParameters == null || !(result.OutParameters[0] is GPFeatureRecordSetLayer))
                    throw new ApplicationException("No viewshed graphics returned for this start point.");

                ToolStatus = "Finished processing. Retrieving results...";
                var viewshedLayer = (GPFeatureRecordSetLayer) result.OutParameters[0];
                _viewshedOverlay.Graphics.AddRange(viewshedLayer.FeatureSet.Features.OfType<Graphic>());
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "Sample Error");
            }
            finally
            {
                ViewShedEnabled = true;
                ViewShedProgressVisible = Visibility.Collapsed;
            }
        }
    }
}
