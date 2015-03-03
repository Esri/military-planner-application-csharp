using MilitaryPlanner.Helpers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MilitaryPlanner.ViewModels
{
    public class BaseToolViewModel : BaseViewModel
    {
        public Esri.ArcGISRuntime.Controls.MapView mapView { get; set; }

        public RelayCommand OpenToolCommand { get; set; }
        public RelayCommand CloseToolCommand { get; set; }

        public BaseToolViewModel()
        {
            OpenToolCommand = new RelayCommand(OnOpenToolCommand);
            CloseToolCommand = new RelayCommand(OnCloseToolCommand);
        }

        private bool _IsToolOpen = false;
        
        public bool IsToolOpen
        {
            get
            {
                return _IsToolOpen;
            }

            set
            {
                _IsToolOpen = value;
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
