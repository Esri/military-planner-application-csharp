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
using System.Collections.Generic;
using System.Linq;
using System.Xml;
using System.Xml.Schema;
using System.Xml.Serialization;
using Esri.ArcGISRuntime.Data;
using Esri.ArcGISRuntime.Geometry;
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

        public Geometry SymbolGeometry { get; set; }

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
