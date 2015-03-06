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
