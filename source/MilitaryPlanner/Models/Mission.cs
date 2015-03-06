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
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows;
using System.Xml;
using System.Xml.Serialization;
using Esri.ArcGISRuntime.Data;
using MilitaryPlanner.Helpers;

namespace MilitaryPlanner.Models
{
    public class Mission : NotificationObject
    {

        public Mission()
        {

        }

        public Mission(string name)
        {
            Name = name;
        }

        private string _name;

        public string Name
        {
            get { return _name; }
            set
            {
                if (_name != value)
                {
                    _name = value;
                    RaisePropertyChanged(() => Name);
                }
            }
        }

        private List<MissionPhase> _phaseList = new List<MissionPhase>();

        public List<MissionPhase> PhaseList
        {
            get { return _phaseList; }
            set
            {
                if (_phaseList != value)
                {
                    _phaseList = value;
                    RaisePropertyChanged(() => PhaseList);
                }
            }
        }

        private List<TimeAwareMilitaryMessage> _timeAwareMilitaryMessages = new List<TimeAwareMilitaryMessage>();

        public List<TimeAwareMilitaryMessage> MilitaryMessages
        {
            get
            {
                return _timeAwareMilitaryMessages;
            }

            set
            {
                if (value != _timeAwareMilitaryMessages)
                {
                    _timeAwareMilitaryMessages = value;
                    RaisePropertyChanged(() => MilitaryMessages);
                }
            }
        }

        public bool Save(string filename)
        {
            return Save(filename, Constants.SAVE_AS_MISSION);
        }

        public bool Save(string filename, int saveAsType)
        {
            switch (saveAsType)
            {
                case Constants.SAVE_AS_GEOMESSAGES:
                    return SaveGeomessages(filename);

                case Constants.SAVE_AS_MISSION:
                default:
                    return SaveMission(filename);
            }
        }

        private bool SaveMission(string filename)
        {
            if (String.IsNullOrWhiteSpace(filename))
            {
                return false;
            }

            XmlSerializer x = new XmlSerializer(GetType());
            XmlWriter writer = new XmlTextWriter(filename, Encoding.UTF8);

            x.Serialize(writer, this);

            return true;
        }

        private bool SaveGeomessages(string filename)
        {
            if (String.IsNullOrWhiteSpace(filename))
            {
                return false;
            }

            using (XmlWriter writer = XmlWriter.Create(filename))
            {
                writer.WriteStartDocument();
                writer.WriteStartElement("geomessages");

                foreach (TimeAwareMilitaryMessage message in MilitaryMessages)
                {
                    writer.WriteStartElement("geomessage");
                    foreach (KeyValuePair<string, string> kvp in message)
                    {
                        string key = kvp.Key.ToLower();
                        string value = kvp.Value;
                        if ("sic" == key)
                        {
                            while (15 > value.Length)
                            {
                                value += "-";
                            }
                        }

                        writer.WriteElementString(key, value);
                    }
                    writer.WriteEndElement();
                }

                writer.WriteEndElement();
                writer.WriteEndDocument();
            }
            return true;
        }

        public bool Load(string filename)
        {
            if (!String.IsNullOrWhiteSpace(filename) && File.Exists(filename))
            {
                try
                {
                    XmlSerializer x = new XmlSerializer(GetType());
                    TextReader tr = new StreamReader(filename);
                    var temp = x.Deserialize(tr) as Mission;

                    if(temp != null)
                    {
                        Name = temp.Name;
                        PhaseList = temp.PhaseList;
                        MilitaryMessages = temp.MilitaryMessages;

                        return true;
                    }
                }
                catch
                {
                    MessageBox.Show("Error in loading mission file.");
                }
                
            }

            return false;
        }

        public bool AddPhase(string name)
        {
            try
            {
                var phase = new MissionPhase(name) {ID = Guid.NewGuid().ToString("D")};

                if (PhaseList.Count > 0)
                {
                    var lastTimeExtent = PhaseList.Last().VisibleTimeExtent;

                    phase.VisibleTimeExtent = new TimeExtent(lastTimeExtent.End.AddSeconds(1.0), lastTimeExtent.Offset(new TimeSpan(1, 0, 0)).End);
                }
                else
                {
                    // set default time extent
                    phase.VisibleTimeExtent = new TimeExtent(DateTime.Now, DateTime.Now.AddSeconds(3599));
                }

                PhaseList.Add(phase);
            }
            catch
            {
                return false;
            }

            return true;
        }

        public Mission ShallowCopy()
        {
            return (Mission)MemberwiseClone();
        }

        public Mission DeepCopy()
        {
            Mission mission = (Mission)MemberwiseClone();

            mission.Name = String.Copy(Name);

            var pl = PhaseList.Select(mp => new MissionPhase
            {
                ID = String.Copy(mp.ID), Name = String.Copy(mp.Name), VisibleTimeExtent = new TimeExtent(mp.VisibleTimeExtent.Start, mp.VisibleTimeExtent.End)
            }).ToList();

            mission.PhaseList = pl;

            return mission;
        }
    }

    public class MissionPhase : NotificationObject
    {
        public MissionPhase()
        {
        }

        public MissionPhase(string name)
        {
            Name = name;
        }

        private string _name;

        public string Name
        {
            get { return _name; }
            set
            {
                if (_name != value)
                {
                    _name = value;
                    RaisePropertyChanged(() => Name);
                }
            }
        }

        public string ID { get; set; }

        public TimeExtent VisibleTimeExtent { get; set; }
    }

}
