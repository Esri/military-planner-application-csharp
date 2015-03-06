using System;
using System.Windows;
using Esri.ArcGISRuntime.Layers;

namespace MilitaryPlanner.ViewModels
{
    public class NetworkingToolViewModel : BaseToolViewModel
    {
        public NetworkingToolViewModel()
        {

        }

        private string _routeTotals = String.Empty;
        public string RouteTotals
        {
            get
            {
                return _routeTotals;
            }

            set
            {
                _routeTotals = value;
                RaisePropertyChanged(() => RouteTotals);
            }
        }

        private GraphicCollection _graphics = null;
        public GraphicCollection Graphics
        {
            get
            {
                return _graphics;
            }

            set
            {
                _graphics = value;
                RaisePropertyChanged(() => Graphics);
            }
        }

        private Visibility _panelResultsVisibility = Visibility.Collapsed;
        public Visibility PanelResultsVisibility
        {
            get
            {
                return _panelResultsVisibility;
            }

            set
            {
                _panelResultsVisibility = value;
                RaisePropertyChanged(() => PanelResultsVisibility);
            }
        }

        private Visibility _progressVisibility = Visibility.Collapsed;
        public Visibility ProgressVisibility
        {
            get
            {
                return _progressVisibility;
            }

            set
            {
                _progressVisibility = value;
                RaisePropertyChanged(() => ProgressVisibility);
            }
        }
    }
}
