using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Esri.ArcGISRuntime.Data;
using Esri.ArcGISRuntime.Symbology.Specialized;

namespace MilitaryPlanner.Helpers
{
    public class TimeAwareMessageLayer
    {
        public TimeAwareMessageLayer()
        {
            MessageLayer = new MessageLayer();
            VisibleTimeExtent = new TimeExtent();
        }

        public MessageLayer MessageLayer
        {
            get;
            set;
        }

        public TimeExtent VisibleTimeExtent
        {
            get;
            set;
        }
    }
}
