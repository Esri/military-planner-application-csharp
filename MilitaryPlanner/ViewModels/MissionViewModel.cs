using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using MilitaryPlanner.Models;
using System.Collections.ObjectModel;
//using ESRI.ArcGIS.Client.AdvancedSymbology;
using System.Windows.Data;
using Esri.ArcGISRuntime.Symbology.Specialized;

namespace MilitaryPlanner.ViewModels
{
    public class MissionViewModel : BaseViewModel
    {
        readonly List<PhaseSymbolViewModel> _symbols = new List<PhaseSymbolViewModel>();

        private Mission _mission;

        public Mission CurrentMission
        {
            get
            {
                return _mission;
            }

            set
            {
                _mission = value;
                ProcessMission();
            }
        }

        public MissionViewModel()
        {
            //_symbols = new ReadOnlyCollection<SymbolViewModel>(new List<SymbolViewModel>());

            // Create a new SymbolDictionary instance 
            SymbolLoader._symbolDictionary = new SymbolDictionary(SymbolDictionaryType.Mil2525c);

            CurrentMission =  Mission.Load(@".\data\missions\testMission.xml");
        }

        public IReadOnlyCollection<PhaseSymbolViewModel> Symbols
        {
            get
            {
                return _symbols;
            }
        }

        public int PhaseCount
        {
            get
            {
                return _mission.PhaseList.Count;
            }
        }

        private void ProcessMission()
        {
            if (_mission == null || _mission.PhaseList.Count < 1)
            {
                return;
            }

            // ok, we have a mission with at least 1 phase
            int currentStartPhase = 0;
            int currentEndPhase = 0;
            //int currentPhaseLength = 1;

            foreach (var phase in _mission.PhaseList)
            {
                // for each message in the phase
                foreach (var pm in phase.PersistentMessages)
                {
                    // for each message, create/update a phase symbol in the symbol list
                    CreateUpdateSymbolWithPM(pm, currentStartPhase, currentEndPhase);
                }

                currentStartPhase++;
                currentEndPhase++;
            }
        }

        private void CreateUpdateSymbolWithPM(PersistentMessage pm, int currentStartPhase, int currentEndPhase)
        {
            // is this an update or a new symbol
            var foundSymbol = _symbols.Where(sl => sl.ItemSVM.Model.Values.ContainsKey("_id") && sl.ItemSVM.Model.Values["_id"] == pm.ID);

            if (foundSymbol != null && foundSymbol.Count() > 0)
            {
                // symbol is in list, do an update
                var ps = foundSymbol.ElementAt(0);

                ps.EndPhase = currentEndPhase;
            }
            else
            {
                // symbol is missing, ADD a new one
                var psvm = new PhaseSymbolViewModel();
                psvm.StartPhase = currentStartPhase;
                psvm.EndPhase = currentEndPhase;

                // create SVM
                psvm.ItemSVM = SymbolLoader.Search(pm.PropertyItems.Where(pi => pi.Key == "sic").ElementAt(0).Value);
                if (!psvm.ItemSVM.Model.Values.ContainsKey("_id"))
                {
                    psvm.ItemSVM.Model.Values.Add("_id", pm.ID);
                }

                _symbols.Add(psvm);
            }
        }

    }

    public class PhaseSymbolViewModel : BaseViewModel
    {
        public PhaseSymbolViewModel() 
        {

        }

        private SymbolViewModel _itemSVM;
        private int _startPhase = 0;
        private int _endPhase = 0;
        //private int _phaseLength = 0;

        public SymbolViewModel ItemSVM
        {
            get
            {
                return _itemSVM;
            }
            set
            {
                _itemSVM = value;
            }
        }

        public int StartPhase
        {
            get { return _startPhase; }
            set { _startPhase = value; }
        }

        public int EndPhase
        {
            get { return _endPhase; }
            set { _endPhase = value; }
        }

        public int PhaseLength
        {
            get { return (_endPhase - _startPhase) + 1; }
        }

        public int ViewWidth
        {
            get
            {
                return PhaseLength * 40;
            }
        }

    }

    public class VariableWidthConverter : IMultiValueConverter
    {

        public object Convert(object[] values, Type targetType, object parameter, System.Globalization.CultureInfo culture)
        {
            int totalPhaseLength = (int)values[0];
            int phaseLength = (int)values[1];
            double listWidth = (double)values[2];
            
            var width = ((listWidth / totalPhaseLength) * phaseLength);

            if (phaseLength-1 > 0)
            {
                width -= 12;
            }

            return width;
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, System.Globalization.CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }

}
