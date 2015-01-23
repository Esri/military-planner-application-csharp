using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Esri.ArcGISRuntime.Data;
using Esri.ArcGISRuntime.Symbology.Specialized;

namespace MilitaryPlanner.Helpers
{
    //public class TimeAwareMessageLayer
    //{
    //    public TimeAwareMessageLayer()
    //    {
    //        MessageLayer = new MessageLayer();
    //        VisibleTimeExtent = new TimeExtent();
    //    }

    //    public MessageLayer MessageLayer
    //    {
    //        get;
    //        set;
    //    }

    //    public TimeExtent VisibleTimeExtent
    //    {
    //        get;
    //        set;
    //    }
    //}

    public class TimeAwareMilitaryMessage : Message
    {
        public TimeAwareMilitaryMessage()
            : base()
        {

        }

        public TimeAwareMilitaryMessage(TimeExtent timeExtent)
            : base()
        {
            VisibleTimeExtent = new TimeExtent(timeExtent.Start,timeExtent.End);
        }

        public TimeExtent VisibleTimeExtent
        {
            get;
            set;
        }

        public Dictionary<string, string> PhaseControlPointsDictionary = new Dictionary<string, string>();

        public void StoreControlPoints(string phaseID, MilitaryMessage msg)
        {
            this[MilitaryMessage.ControlPointsPropertyName] = msg[MilitaryMessage.ControlPointsPropertyName];

            if (PhaseControlPointsDictionary.ContainsKey(phaseID))
            {
                PhaseControlPointsDictionary[phaseID] = msg[MilitaryMessage.ControlPointsPropertyName];
            }
            else
            {
                PhaseControlPointsDictionary.Add(phaseID, msg[MilitaryMessage.ControlPointsPropertyName]);
            }
        }
    }
}
