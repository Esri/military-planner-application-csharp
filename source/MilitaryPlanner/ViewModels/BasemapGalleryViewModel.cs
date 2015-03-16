using Esri.ArcGISRuntime.Portal;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MilitaryPlanner.ViewModels
{
    public class BasemapGalleryViewModel : BaseToolViewModel
    {
        public BasemapGalleryViewModel()
        {

        }

        public IEnumerable<ArcGISPortalItem> Basemaps { get; set; }
    }
}
