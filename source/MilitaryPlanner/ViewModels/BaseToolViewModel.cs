using Esri.ArcGISRuntime.Controls;
using MilitaryPlanner.Helpers;

namespace MilitaryPlanner.ViewModels
{
    public class BaseToolViewModel : BaseViewModel
    {
        public MapView mapView { get; set; }

        public RelayCommand OpenToolCommand { get; set; }
        public RelayCommand CloseToolCommand { get; set; }

        public BaseToolViewModel()
        {
            OpenToolCommand = new RelayCommand(OnOpenToolCommand);
            CloseToolCommand = new RelayCommand(OnCloseToolCommand);
        }

        private bool _isToolOpen = false;
        
        public bool IsToolOpen
        {
            get
            {
                return _isToolOpen;
            }

            set
            {
                _isToolOpen = value;
                RaisePropertyChanged(() => IsToolOpen);
            }
        }

        public void Toggle()
        {
            IsToolOpen = !IsToolOpen;
        }

        private void OnCloseToolCommand(object obj)
        {
            IsToolOpen = false;
        }

        private void OnOpenToolCommand(object obj)
        {
            IsToolOpen = true;
        }
    }
}
