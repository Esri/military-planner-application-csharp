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
using System.Globalization;
using System.Linq;
using System.Windows.Data;
using Esri.ArcGISRuntime.Symbology.Specialized;
using MilitaryPlanner.Helpers;
using MilitaryPlanner.Models;

namespace MilitaryPlanner.ViewModels
{
    public class MissionViewModel : BaseViewModel
    {
        readonly List<PhaseSymbolViewModel> _symbols = new List<PhaseSymbolViewModel>();

        private Mission _mission = new Mission();

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
                RaisePropertyChanged(() => CurrentMission);
                RaisePropertyChanged(() => PhaseCount);
                RaisePropertyChanged(() => CurrentPhase);
            }
        }

        public RelayCommand PhaseBackCommand { get; set; }
        public RelayCommand PhaseNextCommand { get; set; }

        public MissionViewModel()
        {
            // Create a new MilitarySymbolDictionary instance 
            SymbolLoader.MilitarySymbolDictionary = new SymbolDictionary(SymbolDictionaryType.Mil2525c);

            // use this for testing
            //CurrentMission =  Mission.Load(@".\data\missions\testMission.xml");

            Mediator.Register(Constants.ACTION_MISSION_CLONED, OnMissionCloned);
            Mediator.Register(Constants.ACTION_PHASE_INDEX_CHANGED, OnPhaseIndexChanged);

            PhaseBackCommand = new RelayCommand(OnPhaseBack);
            PhaseNextCommand = new RelayCommand(OnPhaseNext);
        }

        private void OnPhaseIndexChanged(object obj)
        {
            CurrentPhaseIndex = (int) obj;
        }

        private void OnPhaseNext(object obj)
        {
            if (CurrentPhaseIndex < PhaseCount - 1)
            {
                CurrentPhaseIndex++;
            }
        }

        private void OnPhaseBack(object obj)
        {
            if (CurrentPhaseIndex > 0)
            {
                CurrentPhaseIndex--;
            }
        }

        private void OnMissionCloned(object obj)
        {
            Mission mission = obj as Mission;

            if (mission != null)
            {
                CurrentMission = mission;
                CurrentPhaseIndex = 0;
            }
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

        private int _currentPhaseIndex = 0;
        public int CurrentPhaseIndex
        {
            get
            {
                return _currentPhaseIndex;
            }

            set
            {
                _currentPhaseIndex = value;
                CurrentPhase = _mission.PhaseList[_currentPhaseIndex];
                RaisePropertyChanged(() => CurrentPhaseIndex);
                RaisePropertyChanged(() => PhaseMessage);
            }
        }

        private MissionPhase _currentPhase = new MissionPhase();
        public MissionPhase CurrentPhase
        {
            get
            {
                return _currentPhase;
            }

            set
            {
                _currentPhase = value;
                RaisePropertyChanged(() => CurrentPhase);
            }
        }

        public string PhaseMessage
        {
            get
            {
                return String.Format("{0} of {1}", CurrentPhaseIndex + 1, PhaseCount);
            }
        }

        private void ProcessMission()
        {
            if (_mission == null || _mission.PhaseList.Count < 1)
            {
                return;
            }

            CurrentPhase = _mission.PhaseList[CurrentPhaseIndex];

            // ok, we have a mission with at least 1 phase
            int currentStartPhase = 0;
            int currentEndPhase = 0;

            foreach (var phase in _mission.PhaseList)
            {
                // for each message in the phase
                //TODO revisit
                //foreach (var pm in phase.PersistentMessages)
                //{
                //    // for each message, create/update a phase symbol in the symbol list
                //    CreateUpdateSymbolWithPM(pm, currentStartPhase, currentEndPhase);
                //}

                currentStartPhase++;
                currentEndPhase++;
            }
        }

        private void CreateUpdateSymbolWithPM(PersistentMessage pm, int currentStartPhase, int currentEndPhase)
        {
            // is this an update or a new symbol
            var foundSymbol = _symbols.Where(sl => sl.ItemSVM.Model.Values.ContainsKey(Message.IdPropertyName) && sl.ItemSVM.Model.Values[Message.IdPropertyName] == pm.ID);

            if (foundSymbol != null && foundSymbol.Any())
            {
                // symbol is in list, do an update
                var ps = foundSymbol.ElementAt(0);

                ps.EndPhase = currentEndPhase;
            }
            else
            {
                // symbol is missing, ADD a new one
                var psvm = new PhaseSymbolViewModel
                {
                    StartPhase = currentStartPhase,
                    EndPhase = currentEndPhase,
                    ItemSVM = SymbolLoader.Search(pm.PropertyItems.Where(pi => pi.Key == "sic").ElementAt(0).Value)
                };

                // create SVM
                if (!psvm.ItemSVM.Model.Values.ContainsKey(Message.IdPropertyName))
                {
                    psvm.ItemSVM.Model.Values.Add(Message.IdPropertyName, pm.ID);
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

        public SymbolViewModel ItemSVM
        {
            get
            {
                return _itemSVM;
            }
            set
            {
                _itemSVM = value;
                RaisePropertyChanged(() => ItemSVM);
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

        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
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

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }

}
