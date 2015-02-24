using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using MilitaryPlanner.Helpers;
using System.IO;
using System.Xml.Serialization;
using System.Xml;
using Esri.ArcGISRuntime.Symbology.Specialized;
using Esri.ArcGISRuntime.Data;

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
            if (String.IsNullOrWhiteSpace(filename))
            {
                return false;
            }

            XmlSerializer x = new XmlSerializer(this.GetType());
            XmlWriter writer = new XmlTextWriter(filename, System.Text.Encoding.UTF8);

            x.Serialize(writer, this);

            return true;
        }

        public bool Load(string filename)
        {
            if (!String.IsNullOrWhiteSpace(filename) && File.Exists(filename))
            {
                try
                {
                    XmlSerializer x = new XmlSerializer(this.GetType());
                    TextReader tr = new StreamReader(filename);
                    var temp = x.Deserialize(tr) as Mission;

                    if(temp != null)
                    {
                        this.Name = temp.Name;
                        this.PhaseList = temp.PhaseList;
                        this.MilitaryMessages = temp.MilitaryMessages;

                        return true;
                    }
                }
                catch
                {

                }
                
            }

            return false;
        }

        public bool AddPhase(string name)
        {
            try
            {
                var phase = new MissionPhase(name);

                phase.ID = Guid.NewGuid().ToString("D");

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
            return (Mission)this.MemberwiseClone();
        }

        public Mission DeepCopy()
        {
            Mission mission = (Mission)this.MemberwiseClone();

            mission.Name = String.Copy(Name);

            var pl = new List<MissionPhase>();

            foreach (var mp in PhaseList)
            {
                pl.Add(new MissionPhase()
                    {
                        ID = String.Copy(mp.ID),
                        Name = String.Copy(mp.Name),
                        VisibleTimeExtent = new TimeExtent(mp.VisibleTimeExtent.Start, mp.VisibleTimeExtent.End)
                    });
            }

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
