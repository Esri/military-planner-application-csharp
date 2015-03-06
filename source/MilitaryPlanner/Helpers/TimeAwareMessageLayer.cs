using System.Collections.Generic;
using System.Linq;
using System.Xml;
using System.Xml.Schema;
using System.Xml.Serialization;
using Esri.ArcGISRuntime.Data;
using Esri.ArcGISRuntime.Symbology.Specialized;

namespace MilitaryPlanner.Helpers
{
    public class TimeAwareMilitaryMessage : Message, IXmlSerializable
    {
        public TimeAwareMilitaryMessage()
        {

        }

        public TimeAwareMilitaryMessage(TimeExtent timeExtent)
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

        public XmlSchema GetSchema()
        {
            return null;
        }

        public void ReadXml(XmlReader reader)
        {

            reader.Read(); // move to inner element, PersistenMessage

            XmlSerializer serializer = new XmlSerializer(typeof(PersistentMessage));

            var temp = serializer.Deserialize(reader) as PersistentMessage;

            if (temp != null)
            {
                VisibleTimeExtent = temp.VisibleTimeExtent;

                foreach (var pi in temp.PropertyItems)
                {
                    if (ContainsKey(pi.Key))
                    {
                        this[pi.Key] = pi.Value;
                    }
                    else
                    {
                        Add(pi.Key, pi.Value);
                    }
                }

                foreach (var pc in temp.PhaseControlPoints)
                {
                    PhaseControlPointsDictionary.Add(pc.Key, pc.Value);
                }
            }

            reader.Read();
        }

        public void WriteXml(XmlWriter writer)
        {
            var pm = new PersistentMessage
            {
                ID = Id,
                VisibleTimeExtent = VisibleTimeExtent,
                PropertyItems = this.Select(kvp => new PropertyItem {Key = kvp.Key, Value = kvp.Value}).ToList(),
                PhaseControlPoints =
                    PhaseControlPointsDictionary.Select(kvp => new PropertyItem {Key = kvp.Key, Value = kvp.Value})
                        .ToList()
            };

            // get properties in property list


            XmlSerializer serializer = new XmlSerializer(typeof(PersistentMessage));
            serializer.Serialize(writer, pm);
        }
    }

    public class CustomItem
    {
        public string Key { get; set; }
        public string Value { get; set; }
    }

    public class PropertyItem
    {
        public string Key { get; set; }
        public string Value { get; set; }
    }

    public class PersistentMessage
    {
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
