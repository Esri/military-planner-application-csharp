using Esri.ArcGISRuntime.Controls;
using Esri.ArcGISRuntime.Geometry;
using Esri.ArcGISRuntime.Layers;
using Esri.ArcGISRuntime.Tasks.Geoprocessing;
using MilitaryPlanner.Helpers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;

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
        private Geoprocessor _gpTask;

        private bool _ViewShedEnabled = true;
        public bool ViewShedEnabled
        {
            get
            {
                return _ViewShedEnabled;
            }
            set
            {
                _ViewShedEnabled = value;
                RaisePropertyChanged(() => ViewShedEnabled);
            }
        }

        private Visibility _ViewShedProgressVisible = Visibility.Collapsed;
        public Visibility ViewShedProgressVisible
        {
            get
            {
                return _ViewShedProgressVisible;
            }
            set
            {
                _ViewShedProgressVisible = value;
                RaisePropertyChanged(() => ViewShedProgressVisible);
            }
        }

        private string _ToolStatus = "";
        public string ToolStatus
        {
            get
            {
                return _ToolStatus;
            }
            set
            {
                _ToolStatus = value;
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
                var viewshedLayer = result.OutParameters[0] as GPFeatureRecordSetLayer;
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
