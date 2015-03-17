using Esri.ArcGISRuntime.Portal;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Esri.ArcGISRuntime.WebMap;
using MilitaryPlanner.Helpers;

namespace MilitaryPlanner.ViewModels
{
    public class BasemapGalleryViewModel : BaseToolViewModel
    {
        public RelayCommand ChangeBasemapCommand { get; set; }

        public BasemapGalleryViewModel()
        {
            ChangeBasemapCommand = new RelayCommand(OnChangeBasemapCommand);
        }

        private ObservableCollection<ArcGISPortalItem> _basemaps;

        public ObservableCollection<ArcGISPortalItem> Basemaps
        {
            get { return _basemaps;}

            set
            {
                _basemaps = value;
                RaisePropertyChanged(() => Basemaps);
            }
        }

        private void OnChangeBasemapCommand(object obj)
        {
            Mediator.NotifyColleagues(Constants.ACTION_UPDATE_BASEMAP, obj);
        }
    }
}
