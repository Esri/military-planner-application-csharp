using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Esri.ArcGISRuntime.Data;
using Esri.ArcGISRuntime.Symbology.Specialized;
using System.Xml.Serialization;

namespace MilitaryPlanner.Helpers
{
    public class TimeAwareMilitaryMessage : Message, IXmlSerializable
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

        public System.Xml.Schema.XmlSchema GetSchema()
        {
            return null;
        }

        public void ReadXml(System.Xml.XmlReader reader)
        {

            reader.Read(); // move to inner element, PersistenMessage

            XmlSerializer serializer = new XmlSerializer(typeof(PersistentMessage));

            var temp = serializer.Deserialize(reader) as PersistentMessage;

            this.VisibleTimeExtent = temp.VisibleTimeExtent;

            foreach (var pi in temp.PropertyItems)
            {
                if (this.ContainsKey(pi.Key))
                {
                    this[pi.Key] = pi.Value;
                }
                else
                {
                    this.Add(pi.Key, pi.Value);
                }
            }

            foreach (var pc in temp.PhaseControlPoints)
            {
                this.PhaseControlPointsDictionary.Add(pc.Key, pc.Value);
            }

            reader.Read();
        }

        public void WriteXml(System.Xml.XmlWriter writer)
        {
            var pm = new PersistentMessage();
            pm.ID = this.Id;
            pm.VisibleTimeExtent = this.VisibleTimeExtent;

            // get properties in property list
            pm.PropertyItems = this.Select(kvp => new PropertyItem() { Key = kvp.Key, Value = kvp.Value }).ToList();

            pm.PhaseControlPoints = this.PhaseControlPointsDictionary.Select(kvp => new PropertyItem() { Key = kvp.Key, Value = kvp.Value }).ToList();

            XmlSerializer serializer = new XmlSerializer(typeof(PersistentMessage));
            serializer.Serialize(writer, pm);
        }
    }

    public class CustomItem
    {
        public CustomItem() { }

        public string Key { get; set; }
        public string Value { get; set; }
    }

    public class PropertyItem
    {
        public PropertyItem() { }

        public string Key { get; set; }
        public string Value { get; set; }
    }

    public class PersistentMessage
    {
        public PersistentMessage()
        {

        }

        public string ID
        {
            get;
            set;
        }

        public TimeExtent VisibleTimeExtent
        {
            get;
            set;
        }

        public List<PropertyItem> PropertyItems
        {
            get;
            set;
        }

        public List<PropertyItem> PhaseControlPoints
        {
            get;
            set;
        }

    }

}
