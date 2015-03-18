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
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;
using Esri.ArcGISRuntime.Data;
using Esri.ArcGISRuntime.Symbology.Specialized;
using MilitaryPlanner.Helpers;
using MilitaryPlanner.Models;

namespace MilitaryPlanner.ViewModels
{
    public class MissionViewModel : BaseViewModel
    {
        //List<PhaseSymbolViewModel> _phaseSymbols = new List<PhaseSymbolViewModel>();
        readonly ObservableCollection<PhaseSymbolViewModel> _phaseSymbols = new ObservableCollection<PhaseSymbolViewModel>(); 

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
                _phaseSymbols.Clear();
                ProcessMission();
                RaisePropertyChanged(() => CurrentMission);
                RaisePropertyChanged(() => PhaseCount);
                RaisePropertyChanged(() => CurrentPhase);
                RaisePropertyChanged(() => MissionTimeExtent);
                RaisePropertyChanged(() => PhaseSymbols);
            }
        }

        public RelayCommand PhaseBackCommand { get; set; }
        public RelayCommand PhaseNextCommand { get; set; }
        public RelayCommand DeletePhaseCommand { get; set; }

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
            DeletePhaseCommand = new RelayCommand(OnDeletePhase);
        }

        private void OnDeletePhase(object obj)
        {
            var question = String.Format("Are you sure you want to delete phase?\n\rName : {0}",CurrentPhase.Name);
            var result = MessageBox.Show(question, "Delete Phase?", MessageBoxButton.YesNo, MessageBoxImage.Warning);

            if (result == MessageBoxResult.Yes)
            {
                if (CurrentPhaseIndex < PhaseCount)
                {
                    // remove phase
                    _mission.PhaseList.RemoveAt(CurrentPhaseIndex);
                    if (CurrentPhaseIndex >= PhaseCount && CurrentPhaseIndex != 0)
                    {
                        CurrentPhaseIndex--;
                    }
                    else
                    {
                        CurrentPhaseIndex = CurrentPhaseIndex;
                    }
                }
            }
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

        public ObservableCollection<PhaseSymbolViewModel> PhaseSymbols
        {
            get
            {
                return _phaseSymbols;
            }
        }

        public int PhaseCount
        {
            get
            {
                return _mission.PhaseList.Count;
            }
        }

        public TimeExtent MissionTimeExtent
        {
            get
            {
                return new TimeExtent(_mission.PhaseList.Min(t => t.VisibleTimeExtent.Start), _mission.PhaseList.Max(t => t.VisibleTimeExtent.End));
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
                if (value < _mission.PhaseList.Count)
                {
                    _currentPhaseIndex = value;
                    CurrentPhase = _mission.PhaseList[_currentPhaseIndex];
                    RaisePropertyChanged(() => CurrentPhaseIndex);
                    RaisePropertyChanged(() => PhaseMessage);
                }
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

            foreach (var mm in _mission.MilitaryMessages)
            {
                currentStartPhase = 0;
                currentEndPhase = -1;

                foreach (var phase in _mission.PhaseList)
                {
                    if (mm.VisibleTimeExtent.Intersects(phase.VisibleTimeExtent))
                    {
                        currentEndPhase = _mission.PhaseList.IndexOf(phase);
                    }
                    else
                    {
                        //if (_mission.PhaseList.IndexOf(phase) <= currentEndPhase)
                        if (currentEndPhase < 0)
                        {
                            //currentStartPhase = _mission.PhaseList.IndexOf(phase);
                            currentStartPhase++;
                        }
                    }
                }

                var pm = new PersistentMessage() { ID = mm.Id, VisibleTimeExtent = mm.VisibleTimeExtent};

                var piList = new List<PropertyItem>();

                foreach (var item in mm)
                {
                    piList.Add(new PropertyItem() { Key = item.Key, Value = item.Value });
                }

                pm.PropertyItems = piList;

                CreateUpdateSymbolWithPM(pm, currentStartPhase, currentEndPhase);
            }

        }

        private void CreateUpdateSymbolWithPM(PersistentMessage pm, int currentStartPhase, int currentEndPhase)
        {
            // is this an update or a new symbol
            var foundSymbol = _phaseSymbols.FirstOrDefault(sl => sl.ItemSVM.Model.Values.ContainsKey(Message.IdPropertyName) && sl.ItemSVM.Model.Values[Message.IdPropertyName] == pm.ID);

            //if (foundSymbol != null && foundSymbol.Any())
            if(foundSymbol != null)
            {
                // symbol is in list, do an update
                var ps = foundSymbol;//.ElementAt(0);

                ps.EndPhase = currentEndPhase;
            }
            else
            {
                // symbol is missing, ADD a new one
                PropertyItem first = pm.PropertyItems.FirstOrDefault(pi => pi.Key == "sic");

                if (first != null)
                {
                    var psvm = new PhaseSymbolViewModel
                    {
                        StartPhase = currentStartPhase,
                        EndPhase = currentEndPhase,
                        ItemSVM = SymbolLoader.Search(first.Value),
                        VisibleTimeExtent = pm.VisibleTimeExtent
                    };

                    // create SVM
                    if (!psvm.ItemSVM.Model.Values.ContainsKey(Message.IdPropertyName))
                    {
                        psvm.ItemSVM.Model.Values.Add(Message.IdPropertyName, pm.ID);
                    }

                    _phaseSymbols.Add(psvm);
                }
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

        private TimeExtent _visibleTimeExtent = new TimeExtent();

        public TimeExtent VisibleTimeExtent
        {
            get
            {
                return _visibleTimeExtent;
            }
            set
            {
                _visibleTimeExtent = value;
                RaisePropertyChanged(() => VisibleTimeExtent);
            }
        }

    }

    public class PadLeftVariableWidthConverter : IMultiValueConverter
    {

        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            double listWidth = (double)values[0];
            TimeExtent messageTimeExtent = (TimeExtent)values[1];
            TimeExtent missionTimeExtent = (TimeExtent)values[2];

            TimeSpan ts = messageTimeExtent.Start.Subtract(missionTimeExtent.Start);
            TimeSpan mts = missionTimeExtent.End.Subtract(missionTimeExtent.Start);

            var widthFactor = ts.TotalSeconds / mts.TotalSeconds;
            var width = listWidth * widthFactor;

            return Math.Max(width,0.0);
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }

    public class VariableWidthConverter : IMultiValueConverter
    {

        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            double listWidth = (double)values[0];
            TimeExtent messageTimeExtent = (TimeExtent)values[1];
            TimeExtent missionTimeExtent = (TimeExtent)values[2];

            TimeSpan ts = messageTimeExtent.End.Subtract(messageTimeExtent.Start);
            TimeSpan mts = missionTimeExtent.End.Subtract(missionTimeExtent.Start);

            var widthFactor = ts.TotalSeconds / mts.TotalSeconds;
            var width = listWidth * widthFactor;

            return Math.Max(0.0, width - 12);
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }

    public class PhaseWidthConverter : IMultiValueConverter
    {

        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            int totalPhaseCount = (int)values[0];
            double listWidth = (double)values[1];

            var width = (listWidth - (listWidth % totalPhaseCount)) / totalPhaseCount;

            var offset = 0;

            while (totalPhaseCount*(width - offset) > listWidth - 3)
            {
                offset++;
            }

            return Math.Max(0.0,width - offset);
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
    public class PhaseHeightConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            return (double)value;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }

    public class SIC2BrushConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var sic = (string) value;

            Brush brush;

            switch (sic[1].ToString().ToLower())
            {
                case "f":
                    brush = Brushes.DeepSkyBlue;
                    break;
                case "n":
                    brush = Brushes.LightGreen;
                    break;
                case "h":
                    brush = Brushes.Salmon;
                    break;
                default:
                    brush = Brushes.Yellow;
                    break;
            }

            return brush;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }

}
