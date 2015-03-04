using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Esri.ArcGISRuntime.Layers;
using System.Windows;

namespace MilitaryPlanner.ViewModels
{
    public class NetworkingToolViewModel : BaseToolViewModel
    {
        public NetworkingToolViewModel()
        {

        }

        private string routeTotals = String.Empty;
        public string RouteTotals
        {
            get
            {
                return routeTotals;
            }

            set
            {
                routeTotals = value;
                RaisePropertyChanged(() => RouteTotals);
            }
        }

        private GraphicCollection graphics = null;
        public GraphicCollection Graphics
        {
            get
            {
                return graphics;
            }

            set
            {
                graphics = value;
                RaisePropertyChanged(() => Graphics);
            }
        }

        private Visibility panelResultsVisibility = Visibility.Collapsed;
        public Visibility PanelResultsVisibility
        {
            get
            {
                return panelResultsVisibility;
            }

            set
            {
                panelResultsVisibility = value;
                RaisePropertyChanged(() => PanelResultsVisibility);
            }
        }

        private Visibility progressVisibility = Visibility.Collapsed;
        public Visibility ProgressVisibility
        {
            get
            {
                return progressVisibility;
            }

            set
            {
                progressVisibility = value;
                RaisePropertyChanged(() => ProgressVisibility);
            }
        }
    }
}
