using System;
using System.Collections.ObjectModel;
using System.Windows.Input;
using MilitaryPlanner.Helpers;
using MilitaryPlanner.Models;
using System.Windows.Data;
using Microsoft.Win32;

namespace MilitaryPlanner.ViewModels
{
    public class MainWindowViewModel : BaseViewModel
    {
        #region Properties

        private bool IsFromMediator = false;

        #region MyDateTime

        private DateTime _myDateTime;
        public DateTime MyDateTime
        {
            get { return _myDateTime; }
            set
            {
                if (_myDateTime != value)
                {
                    _myDateTime = value;
                    RaisePropertyChanged(() => MyDateTime);
                }
            }
        }

        #endregion

        private int _sliderMinimum = 0;
        public int SliderMinimum
        {
            get
            {
                return _sliderMinimum;
            }

            set
            {
                if (_sliderMinimum != value)
                {
                    _sliderMinimum = value;
                    RaisePropertyChanged(() => SliderMinimum);
                }
            }
        }

        private int _sliderMaximum = -1;
        public int SliderMaximum
        {
            get
            {
                return _sliderMaximum;
            }

            set
            {
                if (_sliderMaximum != value)
                {
                    _sliderMaximum = value;
                    RaisePropertyChanged(() => SliderMaximum);
                }
            }
        }

        private int _sliderValue = 0;
        public int SliderValue
        {
            get
            {
                return _sliderValue;
            }

            set
            {
                if (_sliderValue != value)
                {
                    if (!IsFromMediator)
                    {
                        if (value > _sliderValue)
                        {
                            // next
                            Mediator.NotifyColleagues(Constants.ACTION_PHASE_NEXT, value);
                        }
                        else
                        {
                            // back
                            Mediator.NotifyColleagues(Constants.ACTION_PHASE_BACK, value);
                        }
                    }

                    IsFromMediator = false;

                    _sliderValue = value;
                    RaisePropertyChanged(() => SliderValue);
                }
            }
        }

        private MilitaryPlanner.Views.MapView _mapView;
        public MilitaryPlanner.Views.MapView MapView
        {
            get { return _mapView; }
            set{
                if (_mapView != value)
                {
                    _mapView = value;
                    RaisePropertyChanged(() => MapView);
                }
            }
        }

        private MilitaryPlanner.Views.OrderOfBattleView _OOBView;
        public MilitaryPlanner.Views.OrderOfBattleView OOBView
        {
            get { return _OOBView; }
            set
            {
                if (_OOBView != value)
                {
                    _OOBView = value;
                    RaisePropertyChanged(() => OOBView);
                }
            }
        }

        #endregion

        #region Commands

        public RelayCommand CancelCommand { get; set; }
        public RelayCommand DeleteCommand { get; set; }
        public RelayCommand SaveCommand { get; set; }
        public RelayCommand OpenCommand { get; set; }
        public RelayCommand EditMissionPhasesCommand { get; set; }

        #endregion

        #region Ctor

        public MainWindowViewModel()
        {
            //Esri.ArcGISRuntime.ArcGISRuntimeEnvironment.ClientId = "sloy45Jis4XaPxFd";

            try
            {
                Esri.ArcGISRuntime.ArcGISRuntimeEnvironment.Initialize();
            }
            catch (Exception ex)
            {
                Console.WriteLine("Unable to initialize the ArcGIS Runtime with the client id provided: " + ex.Message);
            }

            Mediator.Register(Constants.ACTION_MSG_LAYER_ADDED, DoMessageLayerAdded);
            Mediator.Register(Constants.ACTION_PHASE_ADDED, DoPhaseAdded);
            Mediator.Register(Constants.ACTION_PHASE_INDEX_CHANGED, DoPhaseIndexChanged);
            Mediator.Register(Constants.ACTION_MISSION_LOADED, DoMissionLoaded);

            CancelCommand = new RelayCommand(OnCancelCommand);
            DeleteCommand = new RelayCommand(OnDeleteCommand);
            SaveCommand = new RelayCommand(OnSaveCommand);
            OpenCommand = new RelayCommand(OnOpenCommand);
            EditMissionPhasesCommand = new RelayCommand(OnEditMissionPhases);
            
            MapView = new Views.MapView();
            OOBView = new Views.OrderOfBattleView();
        }

        private void OnEditMissionPhases(object obj)
        {
            Mediator.NotifyColleagues(Constants.ACTION_EDIT_MISSION_PHASES, null);
        }

        private void DoPhaseIndexChanged(object obj)
        {
            int index = (int)obj;

            IsFromMediator = true;

            SliderValue = index;
        }

        private void DoPhaseAdded(object obj)
        {
            IsFromMediator = true;
            SliderMaximum++;
            SliderValue = SliderMaximum;
        }

        private void DoMessageLayerAdded(object obj)
        {
            //_mission.DoMessageLayerAdded(obj);

            //SliderMaximum = _mission.PhaseList.Count - 1;
            //SliderValue = SliderMaximum;
        }

        #endregion

        #region Command Handlers

        private void OnCancelCommand(object obj)
        {
            Mediator.NotifyColleagues(Constants.ACTION_CANCEL, obj);
        }

        private void OnDeleteCommand(object obj)
        {
            Mediator.NotifyColleagues(Constants.ACTION_DELETE, obj);
        }

        private void OnSaveCommand(object obj)
        {
            // file dialog
            var sfd = new SaveFileDialog();

            sfd.Filter = "xml files (*.xml)|*.xml";
            sfd.RestoreDirectory = true;

            if (sfd.ShowDialog() == true)
            {
                Mediator.NotifyColleagues(Constants.ACTION_SAVE_MISSION, sfd.FileName);
            }
        }

        private void OnOpenCommand(object obj)
        {
            var ofd = new OpenFileDialog();

            ofd.Filter = "xml files (*.xml)|*.xml";
            ofd.RestoreDirectory = true;
            ofd.Multiselect = false;

            if (ofd.ShowDialog() == true)
            {
                Mediator.NotifyColleagues(Constants.ACTION_OPEN_MISSION, ofd.FileName);
            }
        }

        private void DoMissionLoaded(object obj)
        {
            var mission = obj as Mission;

            if (mission != null)
            {
                InitializeUI(mission);
            }
        }

        private void InitializeUI(Mission _mission)
        {
            SliderMinimum = 0;
            SliderMaximum = _mission.PhaseList.Count - 1;
            SliderValue = 0;
        }

        #endregion

    }
}