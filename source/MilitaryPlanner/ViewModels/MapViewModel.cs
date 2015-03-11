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
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using Esri.ArcGISRuntime.Controls;
using Esri.ArcGISRuntime.Data;
using Esri.ArcGISRuntime.Geometry;
using Esri.ArcGISRuntime.Layers;
using Esri.ArcGISRuntime.Symbology;
using Esri.ArcGISRuntime.Symbology.Specialized;
using Esri.ArcGISRuntime.Tasks.Imagery;
using Microsoft.Win32;
using MilitaryPlanner.Behavior;
using MilitaryPlanner.Controllers;
using MilitaryPlanner.Helpers;
using MilitaryPlanner.Models;
using MilitaryPlanner.Views;
using Geometry = Esri.ArcGISRuntime.Geometry.Geometry;
using MapView = Esri.ArcGISRuntime.Controls.MapView;

namespace MilitaryPlanner.ViewModels
{
    public class MapViewModel : BaseViewModel, IDropable
    {
        private enum EditState
        {
            Create,
            DragDrop,
            Move,
            Tool,
            None
        };

        private Point _lastKnownPoint;
        private Point _pointOffset = new Point();
        private MapView _mapView;
        private Map _map;
        private Message _currentMessage;
        private EditState _editState = EditState.None;
        private MessageLayer _militaryMessageLayer;
        private TimeExtent _currentTimeExtent = null; //new TimeExtent(DateTime.Now, DateTime.Now.AddSeconds(3599));
        private readonly Mission _mission = new Mission("Default Mission");
        private int _currentPhaseIndex = 0;

        /// <summary>
        /// Dictionary containing a message layer ID as the KEY and a list of military message ID's as the value
        /// </summary>
        private readonly Dictionary<string, List<string>> _phaseMessageDictionary = new Dictionary<string, List<string>>();

        public RelayCommand SetMapCommand { get; set; }
        public RelayCommand PhaseAddCommand { get; set; }
        public RelayCommand PhaseBackCommand { get; set; }
        public RelayCommand PhaseNextCommand { get; set; }

        public RelayCommand SaveCommand { get; set; }
        public RelayCommand LoadCommand { get; set; }
        public RelayCommand MeasureCommand { get; set; }
        public RelayCommand CoordinateReadoutFormatCommand { get; set; }

        public RelayCommand StartViewShedCommand { get; set; }
        public RelayCommand ToggleViewShedToolCommand { get; set; }
        public RelayCommand ToggleGotoXYToolCommand { get; set; }
        public RelayCommand ToggleNetworkingToolCommand { get; set; }

        // controllers
        private GotoXYToolController _gotoXYToolController;
        private NetworkingToolController _networkingToolController;
        private ViewShedToolController _viewShedToolController;
        private CoordinateReadoutController _coordinateReadoutController;

        public MapViewModel()
        {
            Mediator.Register(Constants.ACTION_SELECTED_SYMBOL_CHANGED, DoActionSymbolChanged);
            Mediator.Register(Constants.ACTION_CANCEL, DoActionCancel);
            Mediator.Register(Constants.ACTION_DELETE, DoActionDelete);
            Mediator.Register(Constants.ACTION_DRAG_DROP_STARTED, DoDragDropStarted);
            Mediator.Register(Constants.ACTION_PHASE_NEXT, DoSliderPhaseNext);
            Mediator.Register(Constants.ACTION_PHASE_BACK, DoSliderPhaseBack);
            Mediator.Register(Constants.ACTION_SAVE_MISSION, DoSaveMission);
            Mediator.Register(Constants.ACTION_OPEN_MISSION, DoOpenMission);
            Mediator.Register(Constants.ACTION_EDIT_MISSION_PHASES, DoEditMissionPhases);
            Mediator.Register(Constants.ACTION_CLONE_MISSION, DoCloneMission);

            SetMapCommand = new RelayCommand(OnSetMap);
            PhaseAddCommand = new RelayCommand(OnPhaseAdd);
            PhaseBackCommand = new RelayCommand(OnPhaseBack);
            PhaseNextCommand = new RelayCommand(OnPhaseNext);

            SaveCommand = new RelayCommand(OnSaveCommand);
            LoadCommand = new RelayCommand(OnLoadCommand);
            MeasureCommand = new RelayCommand(OnMeasureCommand);

            CoordinateReadoutFormatCommand = new RelayCommand(OnCoordinateReadoutFormatCommand);

            ToggleViewShedToolCommand = new RelayCommand(OnToggleViewShedToolCommand);
            ToggleGotoXYToolCommand = new RelayCommand(OnToggleGotoXYToolCommand);
            ToggleNetworkingToolCommand = new RelayCommand(OnToggleNetworkingToolCommand);
        }

        private void DoCloneMission(object obj)
        {
            Mission cloneMission = _mission.DeepCopy();

            // update mission cloned
            Mediator.NotifyColleagues(Constants.ACTION_MISSION_CLONED, cloneMission);
        }

        private void OnToggleNetworkingToolCommand(object obj)
        {
            _networkingToolController.Toggle();
        }

        private void OnToggleGotoXYToolCommand(object obj)
        {
            _gotoXYToolController.Toggle();
        }

        private void OnSaveCommand(object obj)
        {
            // file dialog
            var sfd = new SaveFileDialog
            {
                Filter = "xml files (*.xml)|*.xml|Geomessage xml files (*.xml)|*.xml",
                RestoreDirectory = true
            };

            if (sfd.ShowDialog() == true)
            {
                Mediator.NotifyColleagues(Constants.ACTION_SAVE_MISSION, String.Format("{0}{1}{2}",sfd.FilterIndex, Constants.SAVE_AS_DELIMITER, sfd.FileName));
            }
        }

        private void OnLoadCommand(object obj)
        {
            var ofd = new OpenFileDialog
            {
                Filter = "xml files (*.xml)|*.xml",
                RestoreDirectory = true,
                Multiselect = false
            };

            if (ofd.ShowDialog() == true)
            {
                Mediator.NotifyColleagues(Constants.ACTION_OPEN_MISSION, ofd.FileName);
            }
        }

        private string _coordinateReadout = "";
        public string CoordinateReadout
        {
            get
            {
                return _coordinateReadout;
            }

            set
            {
                _coordinateReadout = value;
                RaisePropertyChanged(() => CoordinateReadout);
            }
        }

        private void OnCoordinateReadoutFormatCommand(object obj)
        {
            Mediator.NotifyColleagues(Constants.ACTION_COORDINATE_READOUT_FORMAT_CHANGED, obj);
        }

        private void DoEditMissionPhases(object obj)
        {
            // clone mission phases
            //var cloneMissionPhases = Utilities.DeepClone(_mission.PhaseList);
            Mission cloneMission = _mission.DeepCopy(); //Utilities.CloneObject(_mission) as Mission;

            // load edit mission phases dialog
            var editPhaseDialog = new EditMissionPhasesView();

            // update mission cloned
            Mediator.NotifyColleagues(Constants.ACTION_MISSION_CLONED, cloneMission);
            Mediator.NotifyColleagues(Constants.ACTION_PHASE_INDEX_CHANGED, _currentPhaseIndex);

            editPhaseDialog.WindowStartupLocation = WindowStartupLocation.CenterScreen;

            if (editPhaseDialog.ShowDialog() == true)
            {
                _mission.PhaseList = cloneMission.PhaseList;
                OnCurrentPhaseIndexChanged();
                RaisePropertyChanged(() => PhaseDescription);
            }
        }

        public bool HasTimeExtent
        {
            get
            {
                if (CurrentTimeExtent != null)
                {
                    return true;
                }
                else
                {
                    return false;
                }
            }
        }

        public TimeExtent CurrentTimeExtent
        {
            get
            {
                return _currentTimeExtent;
            }
            set
            {
                _currentTimeExtent = value;
                RaisePropertyChanged(() => CurrentTimeExtent);
                RaisePropertyChanged(() => HasTimeExtent);
            }
        }

        public string PhaseDescription
        {
            get
            {
                if (CurrentPhaseIndex >= 0 && CurrentPhaseIndex < _mission.PhaseList.Count)
                {
                    var mp = _mission.PhaseList[CurrentPhaseIndex];
                    return String.Format("Phase : {0} \nStart : {1:yyyy/MM/dd HH:mm} \nEnd  : {2:yyyy/MM/dd HH:mm}", mp.Name, mp.VisibleTimeExtent.Start, mp.VisibleTimeExtent.End);
                }

                return "Testing";
            }
        }

        private void OnToggleViewShedToolCommand(object obj)
        {
            _viewShedToolController.Toggle();
        }

        private void DoOpenMission(object obj)
        {
            string fileName = obj.ToString();

            if (!String.IsNullOrWhiteSpace(fileName) && File.Exists(fileName))
            {
                if (_mission.Load(fileName))
                {
                    InitializeMapWithMission();
                }
            }
        }

        private void InitializeMapWithMission()
        {
            CurrentPhaseIndex = 0;

            Mediator.NotifyColleagues(Constants.ACTION_MISSION_LOADED, _mission);

            OnCurrentPhaseIndexChanged();
        }

        private void DoSaveMission(object obj)
        {
            string param = obj.ToString();

            string fileName;
            int fileType = 1; // MISSION type

            if (param.Contains(Constants.SAVE_AS_DELIMITER))
            {
                var temp = param.Split(new[] {Constants.SAVE_AS_DELIMITER}, StringSplitOptions.None);
                fileType = Convert.ToInt32(temp[0]);
                fileName = temp[1];
            }
            else
            {
                fileName = param;
            }

            if (!String.IsNullOrWhiteSpace(fileName))
            {
                _mission.Save(fileName, fileType);
            }
        }

        private void DoSliderPhaseBack(object obj)
        {
            OnPhaseBack(null);
        }

        private void DoSliderPhaseNext(object obj)
        {
            OnPhaseNext(null);
        }

        public int CurrentPhaseIndex
        {
            get
            {
                return _currentPhaseIndex;
            }

            set
            {
                if (value != _currentPhaseIndex)
                {
                    _currentPhaseIndex = value;

                    RaisePropertyChanged(() => CurrentPhaseIndex);
                    RaisePropertyChanged(() => PhaseDescription);

                    OnCurrentPhaseIndexChanged();

                    Mediator.NotifyColleagues(Constants.ACTION_PHASE_INDEX_CHANGED, _currentPhaseIndex);
                }
            }
        }

        private void OnCurrentPhaseIndexChanged()
        {
            ClearMilitaryMessageLayer();

            // process military messages for current phase
            ProccessMilitaryMessages(_mission.PhaseList[CurrentPhaseIndex].VisibleTimeExtent);
        }

        private void ClearMilitaryMessageLayer()
        {
            if (_militaryMessageLayer != null && _mapView != null)
            {
                _mapView.Map.Layers.Remove(_militaryMessageLayer.ID);

                AddNewMilitaryMessagelayer();
            }
        }

        private void AddNewMilitaryMessagelayer()
        {
            _militaryMessageLayer = new MessageLayer(SymbolDictionaryType.Mil2525c) {ID = Guid.NewGuid().ToString("D")};
            _mapView.Map.Layers.Add(_militaryMessageLayer);
        }

        private void ProccessMilitaryMessages(TimeExtent timeExtent)
        {
            // get a list of military messages that intersect this time extent
            var militaryMessages = _mission.MilitaryMessages.Where(m => m.VisibleTimeExtent.Intersects(timeExtent)).ToList();
            var phaseID = _mission.PhaseList[CurrentPhaseIndex].ID;

            foreach (var mm in militaryMessages)
            {
                if (mm.ContainsKey(MilitaryMessage.ControlPointsPropertyName))
                {
                    // load the correct control points for the current phase
                    if (mm.PhaseControlPointsDictionary.ContainsKey(phaseID))
                    {
                        mm[MilitaryMessage.ControlPointsPropertyName] = mm.PhaseControlPointsDictionary[phaseID];
                    }
                    else
                    {
                        Console.WriteLine(@"ERROR : Control points not found for phase id {0}", phaseID);
                    }
                }

                if (mm.ContainsKey(MilitaryMessage.ActionPropertyName))
                {
                    mm[MilitaryMessage.ActionPropertyName] = Constants.MSG_ACTION_UPDATE;
                }

                if (ProcessMessage(_militaryMessageLayer, mm))
                {
                    Mediator.NotifyColleagues(Constants.ACTION_ITEM_WITH_GUID_ADDED, mm.Id);
                }
            }
        }

        private void DoDragDropStarted(object obj)
        {
            _editState = EditState.DragDrop;
        }

        private void OnPhaseNext(object param)
        {
            if (CurrentPhaseIndex < _mission.PhaseList.Count - 1)
            {
                // clear any selections
                ClearSelectedMessage();

                CurrentPhaseIndex++;
            }
        }

        private void OnPhaseBack(object param)
        {
            if (CurrentPhaseIndex > 0)
            {
                // clear any selections
                ClearSelectedMessage();

                CurrentPhaseIndex--;
            }
        }

        private void OnPhaseAdd(object param)
        {
            if (_mission.AddPhase("Default Phase Name"))
            {
                Mediator.NotifyColleagues(Constants.ACTION_PHASE_ADDED, null);

                ExtendTimeExtentOnMilitaryMessages(CurrentPhaseIndex);

                CurrentPhaseIndex = _mission.PhaseList.Count - 1;
            }
        }

        private void ExtendTimeExtentOnMilitaryMessages(int currentPhaseIndex)
        {
            // update any military message time extent to the next phase if current extent END matches current phase time extent END
            // this will allow the current phase symbols with unedited time extents to be included in the next phase

            var currentTimeExtentEnd = _mission.PhaseList[currentPhaseIndex].VisibleTimeExtent.End;
            var nextTimeExtentEnd = _mission.PhaseList[currentPhaseIndex + 1].VisibleTimeExtent.End;
            var nextPhaseID = _mission.PhaseList[currentPhaseIndex + 1].ID;

            var currentPhaseMessages = _mission.MilitaryMessages.Where(m => m.VisibleTimeExtent.End == currentTimeExtentEnd).ToList();

            foreach (var tam in currentPhaseMessages)
            {
                tam.VisibleTimeExtent.End = nextTimeExtentEnd;

                if (tam.ContainsKey(MilitaryMessage.ControlPointsPropertyName))
                {
                    if (tam.PhaseControlPointsDictionary.ContainsKey(nextPhaseID))
                    {
                        tam.PhaseControlPointsDictionary[nextPhaseID] = tam[MilitaryMessage.ControlPointsPropertyName];
                    }
                    else
                    {
                        tam.PhaseControlPointsDictionary.Add(nextPhaseID, tam[MilitaryMessage.ControlPointsPropertyName]);
                    }
                }
            }
        }

        private Symbol _lineSymbol;
        private GraphicsOverlay _graphicsOverlay;
        private MensurationTask _mensurationTask;

        private async void OnMeasureCommand(object param)
        {
            if (_editState == EditState.None && _mapView != null && !_mapView.Editor.IsActive)
            {
                _lineSymbol = new SimpleLineSymbol() { Color = Colors.Red, Style = SimpleLineStyle.Solid, Width = 2 } as Symbol;

                _graphicsOverlay = _mapView.GraphicsOverlays["graphicsOverlay"];

                // World Topo Map doesn't support mensuration
                //var temp = _mapView.Map.Layers["World Topo Map"];
                var temp = _mapView.Map.Layers["TestMapServiceLayer"];

                _mensurationTask = new MensurationTask(new Uri((temp as ArcGISTiledMapServiceLayer).ServiceUri));

                // lets do a basic distance measure
                try
                {
                    var line = await RequestUserShape(DrawShape.LineSegment, _lineSymbol) as Polyline;

                    // Requesting shape cancelled
                    if (line == null)
                        return;

                    var parameters = new MensurationLengthParameters()
                    {
                        AngularUnit = AngularUnits.Degrees,
                        LinearUnit = LinearUnits.Meters
                    };

                    var result = await _mensurationTask.DistanceAndAngleAsync(
                        line.Parts.First().StartPoint,
                        line.Parts.First().EndPoint, parameters);

                    if (result.Distance != null)
                    {
                        ShowResults(result, "Measure results");
                    }
                    else
                    {
                        MessageBox.Show("Error", "Mensuration Error");
                    }
                }
                catch (Exception ex)
                {
                    MessageBox.Show(ex.Message, "Mensuration Error");
                }
            }
        }

        // Retrieve the given shape type from the user
        private async Task<Geometry> RequestUserShape(DrawShape drawShape, Symbol symbol)
        {
            if (_mapView == null)
                return null;

            try
            {
                _graphicsOverlay.Graphics.Clear();

                var shape = await _mapView.Editor.RequestShapeAsync(drawShape, symbol);

                _graphicsOverlay.Graphics.Add(new Graphic(shape, symbol));
                return shape;
            }
            catch (TaskCanceledException)
            {
                return null;
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "Shape Drawing Error");
                return null;
            }
        }

        // Show results from mensuration task in string format
        private void ShowResults(object result, string caption = "")
        {
            StringBuilder sb = new StringBuilder();

            if (result is MensurationPointResult)
            {
                MensurationPointResult pointResult = (MensurationPointResult)result;

                if (pointResult.Point != null)
                {
                    sb.Append(pointResult.Point);
                    sb.Append("\n");
                }
            }
            else if (result is MensurationHeightResult)
            {
                var heightResult = (MensurationHeightResult)result;

                if (heightResult.Height != null)
                {
                    sb.Append("Height\n");
                    sb.AppendFormat("Value:\t\t{0}\n", heightResult.Height.Value);
                    sb.AppendFormat("Display Value:\t{0}\n", heightResult.Height.DisplayValue);
                    sb.AppendFormat("Uncertainty:\t{0}\n", heightResult.Height.Uncertainty);
                    sb.AppendFormat("Unit:\t\t{0}\n", heightResult.Height.LinearUnit);
                    sb.Append("\n");
                }
            }
            else if (result is MensurationLengthResult)
            {
                var lengthResult = (MensurationLengthResult)result;

                if (lengthResult.Distance != null)
                {
                    sb.Append("Distance\n");
                    sb.AppendFormat("Value:\t\t{0}\n", lengthResult.Distance.Value);
                    sb.AppendFormat("Display Value:\t{0}\n", lengthResult.Distance.DisplayValue);
                    sb.AppendFormat("Uncertainty:\t{0}\n", lengthResult.Distance.Uncertainty);
                    sb.AppendFormat("Unit:\t\t{0}\n", lengthResult.Distance.LinearUnit);
                    sb.Append("\n");
                }
                if (lengthResult.AzimuthAngle != null)
                {
                    sb.Append("Azimuth Angle\n");
                    sb.AppendFormat("Value:\t\t{0}\n", lengthResult.AzimuthAngle.Value);
                    sb.AppendFormat("Display Value:\t{0}\n", lengthResult.AzimuthAngle.DisplayValue);
                    sb.AppendFormat("Uncertainty:\t{0}\n", lengthResult.AzimuthAngle.Uncertainty);
                    sb.AppendFormat("Unit:\t\t{0}\n", lengthResult.AzimuthAngle.AngularUnit);
                    sb.Append("\n");
                }
                if (lengthResult.ElevationAngle != null)
                {
                    sb.Append("Elevation Angle\n");
                    sb.AppendFormat("Value:\t\t{0}\n", lengthResult.ElevationAngle.Value);
                    sb.AppendFormat("Display Value:\t{0}\n", lengthResult.ElevationAngle.DisplayValue);
                    sb.AppendFormat("Uncertainty:\t{0}\n", lengthResult.ElevationAngle.Uncertainty);
                    sb.AppendFormat("Unit:\t\t{0}\n", lengthResult.ElevationAngle.AngularUnit);
                    sb.Append("\n");
                }
            }
            else if (result is MensurationAreaResult)
            {
                var areaResult = (MensurationAreaResult)result;

                if (areaResult.Area != null)
                {
                    sb.Append("Area\n");
                    sb.AppendFormat("Value:\t\t{0}\n", areaResult.Area.Value);
                    sb.AppendFormat("Display Value:\t{0}\n", areaResult.Area.DisplayValue);
                    sb.AppendFormat("Uncertainty:\t{0}\n", areaResult.Area.Uncertainty);
                    sb.AppendFormat("Unit:\t\t{0}\n", areaResult.Area.AreaUnit);
                    sb.Append("\n");
                }

                if (areaResult.Perimeter != null)
                {
                    sb.Append("Perimeter\n");
                    sb.AppendFormat("Value:\t\t{0}\n", areaResult.Perimeter.Value);
                    sb.AppendFormat("Display Value:\t{0}\n", areaResult.Perimeter.DisplayValue);
                    sb.AppendFormat("Uncertainty:\t{0}\n", areaResult.Perimeter.Uncertainty);
                    sb.AppendFormat("Unit:\t\t{0}\n", areaResult.Perimeter.LinearUnit);
                    sb.Append("\n");
                }
            }

            MessageBox.Show(sb.ToString(), caption);
        }

        private void OnSetMap(object param)
        {
            var mapView = param as MapView;

            if (mapView == null)
            {
                return;
            }
            _mapView = mapView;
            _map = mapView.Map;

            mapView.MouseLeftButtonDown += mapView_MouseLeftButtonDown;
            mapView.MouseLeftButtonUp += mapView_MouseLeftButtonUp;
            mapView.MouseMove += mapView_MouseMove;

            // setup any controllers that use the map view
            _gotoXYToolController = new GotoXYToolController(mapView, this);
            _networkingToolController = new NetworkingToolController(mapView, this);
            _viewShedToolController = new ViewShedToolController(mapView, this);
            _coordinateReadoutController = new CoordinateReadoutController(mapView, this);

            // add default message layer
            AddNewMilitaryMessagelayer();

            if (_mission.PhaseList.Count < 1)
            {
                if (_mission.AddPhase("Phase 1"))
                {
                    Mediator.NotifyColleagues(Constants.ACTION_PHASE_ADDED, null);
                    RaisePropertyChanged(() => PhaseDescription);
                }
            }
        }

        void mapView_MouseMove(object sender, MouseEventArgs e)
        {
            if (_map == null || _editState == EditState.Tool)
            {
                return;
            }

            _lastKnownPoint = e.GetPosition(_mapView);

            var adjustedPoint = AdjustPointWithOffset(_lastKnownPoint);

            //if a selected symbol, move it
            if (_editState == EditState.Move && e.LeftButton == MouseButtonState.Pressed)
            {
                UpdateCurrentMessage(_mapView.ScreenToLocation(adjustedPoint));
            }
        }

        private Point AdjustPointWithOffset(Point lastKnownPoint)
        {
            return new Point(lastKnownPoint.X + _pointOffset.X, lastKnownPoint.Y + _pointOffset.Y);
        }

        void mapView_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            if (_editState == EditState.Move)
            {
                _editState = EditState.None;
            }
        }

        async void mapView_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (_editState == EditState.Create || _editState == EditState.Tool)
            {
                return;
            }

            if (_editState == EditState.None)
            {
                // hit test on message layer
                if (_militaryMessageLayer != null)
                {
                    ClearSelectedMessage();

                    var graphic = await HitTestMessageLayerAsync(e);

                    if (graphic != null)
                    {
                        _pointOffset = GetMessageOffset(graphic, e.GetPosition(_mapView));

                        SelectMessageGraphic(graphic);

                        _editState = EditState.Move;

                        _mapView.ReleaseMouseCapture();
                    }
                }
            }
        }

        private void ClearSelectedMessage()
        {
            if (_currentMessage != null)
            {
                SelectMessage(_currentMessage, false);

                CurrentTimeExtent = null;
            }
        }

        private void SelectMessageGraphic(Graphic graphic)
        {
            if (graphic == null)
                return;

            if (graphic.Attributes.ContainsKey(Message.IdPropertyName))
            {
                var selectMessage = _militaryMessageLayer.GetMessage(graphic.Attributes[Message.IdPropertyName].ToString());
                SelectMessage(selectMessage, true);

                UpdateCurrentTimeExtent(selectMessage);
            }
        }

        private void UpdateCurrentTimeExtent(Message selectMessage)
        {
            var mm = _mission.MilitaryMessages.First(m => m.Id == selectMessage.Id);

            if (mm != null)
            {
                CurrentTimeExtent = mm.VisibleTimeExtent;
            }
        }

        private Point GetMessageOffset(Graphic graphic, Point screenPoint)
        {
            var resultPoint = new Point();

            if (graphic == null || _mapView == null)
                return resultPoint;

            if (graphic.Geometry.GeometryType == GeometryType.Point)
            {
                var mp = graphic.Geometry as MapPoint;

                if (mp != null)
                {
                    var point = _mapView.LocationToScreen(mp);

                    resultPoint.X = point.X - screenPoint.X;
                    resultPoint.Y = point.Y - screenPoint.Y;
                }
            }

            return resultPoint;
        }

        private async Task<Graphic> HitTestMessageLayerAsync(MouseButtonEventArgs e)
        {
            if (_mapView != null && _militaryMessageLayer != null)
            {
                foreach (var subLayer in _militaryMessageLayer.ChildLayers)
                {
                    var messageSubLayer = subLayer as MessageSubLayer;

                    if(messageSubLayer != null)
                    {
                        var graphic = await messageSubLayer.HitTestAsync(_mapView, e.GetPosition(_mapView));

                        if (graphic != null)
                        {
                            return graphic;
                        }
                    }
                }
            }

            return null;
        }

        private void SelectMessage(Message message, bool isSelected)
        {
            if (_militaryMessageLayer == null || message == null)
                return;

            _currentMessage = isSelected ? message : null;

            var msg = new MilitaryMessage(message.Id, MilitaryMessageType.PositionReport, isSelected ? MilitaryMessageAction.Select : MilitaryMessageAction.UnSelect);

            if (_militaryMessageLayer.ProcessMessage(msg))
            {
            }
        }

        private void UpdateCurrentMessage(MapPoint mapPoint)
        {
            if (_currentMessage != null && _militaryMessageLayer != null)
            {
                var msg = new MilitaryMessage(_currentMessage.Id, MilitaryMessageType.PositionReport, MilitaryMessageAction.Update, new List<MapPoint>() { mapPoint });

                if (_militaryMessageLayer.ProcessMessage(msg))
                {
                    UpdateMilitaryMessageControlPoints(msg);
                }
            }
        }

        private void UpdateMilitaryMessageControlPoints(MilitaryMessage msg)
        {
            var tam = _mission.MilitaryMessages.First(m => m.Id == msg.Id);

            if (tam != null)
            {
                //tam[MilitaryMessage.ControlPointsPropertyName] = msg[MilitaryMessage.ControlPointsPropertyName];
                tam.StoreControlPoints(_mission.PhaseList[CurrentPhaseIndex].ID, msg);
            }
        }

        private void RemoveMessage(Message message)
        {
            var msg = new MilitaryMessage(message.Id, MilitaryMessageType.PositionReport, MilitaryMessageAction.Remove);

            // remove from visible layer
            _militaryMessageLayer.ProcessMessage(msg);

            RemoveMessageFromPhase(CurrentPhaseIndex, _mission.MilitaryMessages.First(m => m.Id == message.Id));
        }

        private void RemoveMessageFromPhase(int phaseIndex, TimeAwareMilitaryMessage tam)
        {
            // check if message is only is this phase
            var phaseTimeExtent = _mission.PhaseList[phaseIndex].VisibleTimeExtent;

            if (tam.VisibleTimeExtent.Start >= phaseTimeExtent.Start && tam.VisibleTimeExtent.End <= phaseTimeExtent.End)
            {
                // contained in this phase only, remove completely
                _mission.MilitaryMessages.Remove(tam);

                Mediator.NotifyColleagues(Constants.ACTION_ITEM_WITH_GUID_REMOVED, tam.Id);
                return;
            }
            else if (tam.VisibleTimeExtent.Start >= phaseTimeExtent.Start && tam.VisibleTimeExtent.End > phaseTimeExtent.End)
            {
                // message starts in this phase but goes into next phase
                // update start with next phase Start
                if (phaseIndex < _mission.PhaseList.Count() - 1)
                {
                    tam.VisibleTimeExtent.Start = _mission.PhaseList[phaseIndex + 1].VisibleTimeExtent.Start;
                }
            }
            else if (tam.VisibleTimeExtent.Start < phaseTimeExtent.Start)
            {
                // message starts in previous phase, update END to previous phase END
                if (phaseIndex > 0)
                {
                    tam.VisibleTimeExtent.End = _mission.PhaseList[phaseIndex - 1].VisibleTimeExtent.End;
                }
            }
        }

        private SymbolViewModel _selectedSymbol;
        private string _geometryType = String.Empty;

        private bool ProcessMessage(MessageLayer messageLayer, Message msg)
        {
            if (messageLayer != null && msg != null)
            {
                var result = messageLayer.ProcessMessage(msg);

                // add id to messageIDList
                //if (!_messageDictionary.ContainsKey(msg.Id) && result)
                //{
                //    _messageDictionary.Add(msg.Id, messageLayer.ID);
                //}

                if (!_phaseMessageDictionary.ContainsKey(messageLayer.ID))
                {
                    _phaseMessageDictionary.Add(messageLayer.ID, new List<string>());
                }

                if (!_phaseMessageDictionary[messageLayer.ID].Contains(msg.Id))
                {
                    // add
                    _phaseMessageDictionary[messageLayer.ID].Add(msg.Id);
                }

                return result;
            }

            return false;
        }

        private void DoActionDelete(object obj)
        {
            // remove any selected messages
            if (_currentMessage != null)
            {
                // remove message
                RemoveMessage(_currentMessage);
            }
        }

        private void DoActionCancel(object obj)
        {
            if (_mapView != null)
            {
                if (_mapView.Editor.Cancel.CanExecute(null))
                {
                    _mapView.Editor.Cancel.Execute(null);
                }
            }

            if (_editState == EditState.Create)
            {
                _editState = EditState.None;
            }
        }

        private async void DoActionSymbolChanged(object param)
        {
            _selectedSymbol = param as SymbolViewModel;

            //Cancel editing if started
            if (_mapView.Editor.Cancel.CanExecute(null))
            {
                _mapView.Editor.Cancel.Execute(null);
            }

            if (_selectedSymbol != null)
            {
                Dictionary<string, string> values = (Dictionary<string, string>)_selectedSymbol.Model.Values;
                _geometryType = values["GeometryType"];

                DrawShape drawShape = DrawShape.Point;

                switch (_geometryType)
                {
                    case "Point":
                        drawShape = DrawShape.Point;
                        break;
                    case "Line":
                        drawShape = DrawShape.Polyline;
                        break;
                    case "Polygon":
                        drawShape = DrawShape.Polygon;
                        break;
                    default:
                        drawShape = DrawShape.Point;
                        break;
                }

                _editState = EditState.Create;

                try
                {
                    // get geometry from editor
                    var geometry = await _mapView.Editor.RequestShapeAsync(drawShape);

                    _editState = EditState.None;

                    // process symbol with geometry
                    ProcessSymbol(_selectedSymbol, geometry);
                }
                catch (TaskCanceledException)
                {
                    // clean up when drawing task is canceled
                }
            }
        }

        private void ProcessSymbol(SymbolViewModel symbol, Geometry geometry)
        {
            if (symbol == null || geometry == null)
            {
                return;
            }

            //create a new message
            var msg = new TimeAwareMilitaryMessage
            {
                VisibleTimeExtent = new TimeExtent(_mission.PhaseList[CurrentPhaseIndex].VisibleTimeExtent.Start,
                    _mission.PhaseList[CurrentPhaseIndex].VisibleTimeExtent.End),
                Id = Guid.NewGuid().ToString("D")
            };

            // set default time extent

            //set the ID and other parts of the message
            msg.Add(MilitaryMessage.TypePropertyName, Constants.MSG_TYPE_POSITION_REPORT);
            msg.Add(MilitaryMessage.ActionPropertyName, Constants.MSG_ACTION_UPDATE);
            msg.Add(MilitaryMessage.WkidPropertyName, "3857");
            msg.Add(MilitaryMessage.SicCodePropertyName, symbol.SymbolID);
            msg.Add(MilitaryMessage.UniqueDesignationPropertyName, "1");

            // Construct the Control Points based on the geometry type of the drawn geometry.
            switch (geometry.GeometryType)
            {
                case GeometryType.Point:
                    MapPoint point = geometry as MapPoint;
                    if (point != null)
                        msg.Add(MilitaryMessage.ControlPointsPropertyName, string.Format("{0},{1}", point.X.ToString(), point.Y.ToString()));
                    break;
                case GeometryType.Polygon:
                    Polygon polygon = geometry as Polygon;
                    string cpts = polygon.Parts.SelectMany(pt => pt.GetPoints()).Aggregate(string.Empty, (current, segpt) => current + (";" + segpt.X.ToString() + "," + segpt.Y.ToString()));
                    //foreach (var pt in polygon.Rings[0])
                    msg.Add(MilitaryMessage.ControlPointsPropertyName, cpts);
                    break;
                case GeometryType.Polyline:
                    Polyline polyline = geometry as Polyline;
                    cpts = string.Empty;

                    // TODO find a way to determine if polyline map points need adjustment based on symbol being drawn
                    var mpList = AdjustMapPoints(polyline, symbol);

                    cpts = mpList.Aggregate(cpts, (current, mp) => current + (";" + mp.X.ToString() + "," + mp.Y.ToString()));

                    msg.Add(MilitaryMessage.ControlPointsPropertyName, cpts);
                    break;
            }

            //Process the message
            if (ProcessMessage(_militaryMessageLayer, msg))
            {
                RecordMessageBeingAdded(msg);
            }
            else
            {
                MessageBox.Show("Failed to process message.");
            }

        }

        private void RecordMessageBeingAdded(TimeAwareMilitaryMessage tam)
        {
            tam.PhaseControlPointsDictionary.Add(_mission.PhaseList[CurrentPhaseIndex].ID, tam[MilitaryMessage.ControlPointsPropertyName]);

            AddMilitaryMessageToMessageList(tam);
        }

        private void AddMilitaryMessageToMessageList(TimeAwareMilitaryMessage tam)
        {
            if (_mission.MilitaryMessages.Count(m => m.Id == tam.Id) == 0)
            {
                _mission.MilitaryMessages.Add(tam);
            }
        }

        private List<MapPoint> AdjustMapPoints(Polyline polyline, SymbolViewModel symbol)
        {
            // TODO find a better way to determine if we need to adjust the control points for the symbol
            if (symbol.SymbolID.Contains("POLA") || symbol.SymbolID.Contains("PPA"))
            {
                return AdjustMapPoints(polyline, DrawShape.Arrow);
            }

            return AdjustMapPoints(polyline, DrawShape.Polyline);
        }

        private List<MapPoint> AdjustMapPoints(Polyline polyline, DrawShape drawShape)
        {
            if (polyline == null || polyline.Parts == null || !polyline.Parts.Any())
            {
                return null;
            }

            var mapPoints = new List<MapPoint>();

            var points = polyline.Parts.First().GetPoints().ToList();

            if (drawShape == DrawShape.Arrow)
            {
                // Arrow shapes like axis of advance 
                // requires at least 3 points, 1 back, 2 front, 3 width

                if (points.Count() == 2)
                {
                    // add a third point, otherwise the message processor will fail
                    var thridPoint = new MapPoint(points.Last().X, points.Last().Y);
                    points.Add(thridPoint);
                }

                mapPoints.AddRange(points.Where(point => point != points.Last()));

                mapPoints.Reverse();
                mapPoints.Add(points.Last());
            }
            else
            {
                mapPoints = points;
            }

            return mapPoints;
        }

        /// <summary>
        /// IDragable.DataType
        /// the type of object that can be dropped on the map
        /// typeof SymbolTreeViewModel
        /// </summary>
        public Type DataType
        {
            get { return typeof(SymbolTreeViewModel); }
        }

        /// <summary>
        /// IDragable.Drop
        /// Method called when an object of a valid type is dropped on the Map
        /// The data is a SymbolTreeViewModel along with the DragEventArgs
        /// </summary>
        /// <param name="data"></param>
        /// <param name="e"></param>
        public void Drop(object data, DragEventArgs e)
        {
            var stvm = data as SymbolTreeViewModel;

            if (stvm != null)
            {
                AddNewMessage(stvm.ItemSVM, e.GetPosition(_mapView), stvm.GUID);
            }

            Mediator.NotifyColleagues(Constants.ACTION_DRAG_DROP_ENDED, data);
            _editState = EditState.None;
        }

        private void AddNewMessage(SymbolViewModel symbolViewModel, Point p, string guid)
        {
            //create a new message
            var tam = new TimeAwareMilitaryMessage
            {
                VisibleTimeExtent = new TimeExtent(_mission.PhaseList[CurrentPhaseIndex].VisibleTimeExtent.Start,
                    _mission.PhaseList[CurrentPhaseIndex].VisibleTimeExtent.End),
                Id = guid
            };

            tam.Add(MilitaryMessage.TypePropertyName, Constants.MSG_TYPE_POSITION_REPORT);
            tam.Add(MilitaryMessage.ActionPropertyName, Constants.MSG_ACTION_UPDATE);
            tam.Add(MilitaryMessage.WkidPropertyName, "3857");
            tam.Add(MilitaryMessage.SicCodePropertyName, symbolViewModel.SymbolID);
            tam.Add(MilitaryMessage.UniqueDesignationPropertyName, "1");

            // Construct the Control Points based on the geometry type of the drawn geometry.
            var point = _mapView.ScreenToLocation(p);
            tam.Add(MilitaryMessage.ControlPointsPropertyName, point.X.ToString() + "," + point.Y.ToString());

            //Process the message
            if (ProcessMessage(_militaryMessageLayer, tam))
            {
                RecordMessageBeingAdded(tam);
            }
            else
            {
                MessageBox.Show("Failed to process message.");
            }
        }
    }
}
