using MilitaryPlanner.Helpers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;
using MilitaryPlanner.Models;
using MilitaryPlanner.DragDrop.UI.Behavior;
using Esri.ArcGISRuntime.Symbology.Specialized;
using Esri.ArcGISRuntime.Geometry;
using Esri.ArcGISRuntime.Controls;
using Esri.ArcGISRuntime.Data;
using Esri.ArcGISRuntime.Layers;
using Esri.ArcGISRuntime.Tasks.Imagery;
using Esri.ArcGISRuntime.Symbology;
using System.IO;
using Esri.ArcGISRuntime.Tasks.Geoprocessing;
using MilitaryPlanner.Controllers;
using Microsoft.Win32;

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

        private enum CoordinateReadoutFormat
        {
            DD,
            DMS,
            GARS,
            GEOREF,
            MGRS,
            USNG,
            UTM
        };

        private Point _lastKnownPoint;
        private Point _pointOffset = new Point();
        private MapView _mapView;
        private Map _map;
        private Message _currentMessage;
        private EditState _editState = EditState.None;
        private MessageLayer _militaryMessageLayer;
        private TimeExtent _currentTimeExtent = null; //new TimeExtent(DateTime.Now, DateTime.Now.AddSeconds(3599));
        private Mission _mission = new Mission("Default Mission");
        private int _currentPhaseIndex = 0;
        private CoordinateReadoutFormat _coordinateReadoutFormat = CoordinateReadoutFormat.DD;

        /// <summary>
        /// Dictionary containing a message layer ID as the KEY and a list of military message ID's as the value
        /// </summary>
        private Dictionary<string, List<string>> _phaseMessageDictionary = new Dictionary<string, List<string>>();

        public RelayCommand SetMapCommand { get; set; }
        public RelayCommand PhaseAddCommand { get; set; }
        public RelayCommand PhaseBackCommand { get; set; }
        public RelayCommand PhaseNextCommand { get; set; }

        public RelayCommand SaveCommand { get; set; }
        public RelayCommand MeasureCommand { get; set; }
        public RelayCommand CoordinateReadoutCommand { get; set; }

        public RelayCommand StartViewShedCommand { get; set; }
        public RelayCommand ToggleViewShedToolCommand { get; set; }
        public RelayCommand ToggleGotoXYToolCommand { get; set; }

        // controllers
        private GotoXYToolController gotoXYToolController;

        //viewshed
        private const string ViewshedServiceUrl = "http://sampleserver6.arcgisonline.com/arcgis/rest/services/Elevation/ESRI_Elevation_World/GPServer/Viewshed";

        private GraphicsOverlay _inputOverlay;
        private GraphicsOverlay _viewshedOverlay;
        private Geoprocessor _gpTask;

        private bool _ViewShedEnabled = true;
        public bool ViewShedEnabled 
        {
            get
            {
                return _ViewShedEnabled;
            }
            set
            {
                _ViewShedEnabled = value;
                RaisePropertyChanged(() => ViewShedEnabled);
            }
        }
        private bool _ViewShedProgressVisible = false;
        public bool ViewShedProgressVisible 
        {
            get
            {
                return _ViewShedProgressVisible;
            }
            set
            {
                _ViewShedProgressVisible = value;
                RaisePropertyChanged(() => ViewShedProgressVisible);
            }
        }
        private string _ToolStatus = "";
        public string ToolStatus
        {
            get
            {
                return _ToolStatus;
            }
            set
            {
                _ToolStatus = value;
                RaisePropertyChanged(() => ToolStatus);
            }
        }


        public MapViewModel()
        {
            Mediator.Register(Constants.ACTION_SELECTED_SYMBOL_CHANGED, DoActionSymbolChanged);
            Mediator.Register(Constants.ACTION_CANCEL, DoActionCancel);
            Mediator.Register(Constants.ACTION_DELETE, DoActionDelete);
            Mediator.Register(Constants.ACTION_MISSION_HYDRATE, DoMissionHydrate);
            Mediator.Register(Constants.ACTION_DRAG_DROP_STARTED, DoDragDropStarted);
            Mediator.Register(Constants.ACTION_PHASE_NEXT, DoSliderPhaseNext);
            Mediator.Register(Constants.ACTION_PHASE_BACK, DoSliderPhaseBack);
            Mediator.Register(Constants.ACTION_SAVE_MISSION, DoSaveMission);
            Mediator.Register(Constants.ACTION_OPEN_MISSION, DoOpenMission);
            Mediator.Register(Constants.ACTION_EDIT_MISSION_PHASES, DoEditMissionPhases);

            SetMapCommand = new RelayCommand(OnSetMap);
            PhaseAddCommand = new RelayCommand(OnPhaseAdd);
            PhaseBackCommand = new RelayCommand(OnPhaseBack);
            PhaseNextCommand = new RelayCommand(OnPhaseNext);

            SaveCommand = new RelayCommand(OnSaveCommand);
            MeasureCommand = new RelayCommand(OnMeasureCommand);

            CoordinateReadoutCommand = new RelayCommand(OnCoordinateReadoutCommand);

            StartViewShedCommand = new RelayCommand(OnStartViewShedCommand);
            ToggleViewShedToolCommand = new RelayCommand(OnToggleViewShedToolCommand);
            ToggleGotoXYToolCommand = new RelayCommand(OnToggleGotoXYToolCommand);

            _IsViewShedToolVisible = false;
        }

        private void OnToggleGotoXYToolCommand(object obj)
        {
            //Mediator.NotifyColleagues(Constants.ACTION_GOTO_XY_COORDINATES, "-103.793;40.259");
            gotoXYToolController.Toggle();
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

        private string _coordinateReadout = "";
        public string CoordinateReadout
        {
            get
            {
                return _coordinateReadout;
            }

            private set
            {
                _coordinateReadout = value;
                RaisePropertyChanged(() => CoordinateReadout);
            }
        }

        private void DoEditMissionPhases(object obj)
        {
            // clone mission phases
            //var cloneMissionPhases = Utilities.DeepClone(_mission.PhaseList);
            Mission cloneMission = _mission.DeepCopy(); //Utilities.CloneObject(_mission) as Mission;

            // load edit mission phases dialog
            var editPhaseDialog = new MilitaryPlanner.Views.EditMissionPhasesView();

            // update mission cloned
            Mediator.NotifyColleagues(Constants.ACTION_MISSION_CLONED, cloneMission);

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
            string temp = obj as string;
            if (temp == "True")
            {
                IsViewShedToolVisible = true;
            }
            else
            {
                IsViewShedToolVisible = false;
            }
        }

        private bool _IsViewShedToolVisible = false;
        public bool IsViewShedToolVisible
        {
            get
            {
                return _IsViewShedToolVisible;
            }

            set
            {
                _IsViewShedToolVisible = value;
                RaisePropertyChanged(() => IsViewShedToolVisible);
            }
        }

        private async void OnStartViewShedCommand(object obj)
        {
            try
            {
                string txtMiles = obj as string;

                //uiPanel.IsEnabled = false;
                ViewShedEnabled = false;
                _inputOverlay.Graphics.Clear();
                _viewshedOverlay.Graphics.Clear();

                //get the user's input point
                var inputPoint = await _mapView.Editor.RequestPointAsync();

                //progress.Visibility = Visibility.Visible;
                ViewShedProgressVisible = true;
                _inputOverlay.Graphics.Add(new Graphic() { Geometry = inputPoint });

                var parameter = new GPInputParameter() { OutSpatialReference = SpatialReferences.WebMercator };
                parameter.GPParameters.Add(new GPFeatureRecordSetLayer("Input_Observation_Point", inputPoint));
                parameter.GPParameters.Add(new GPLinearUnit("Viewshed_Distance ", LinearUnits.Miles, Convert.ToDouble(txtMiles)));

                //txtStatus.Text = "Processing on server...";
                ToolStatus = "Processing on server...";
                var result = await _gpTask.ExecuteAsync(parameter);
                if (result == null || result.OutParameters == null || !(result.OutParameters[0] is GPFeatureRecordSetLayer))
                    throw new ApplicationException("No viewshed graphics returned for this start point.");

                //txtStatus.Text = "Finished processing. Retrieving results...";
                ToolStatus = "Finished processing. Retrieving results...";
                var viewshedLayer = result.OutParameters[0] as GPFeatureRecordSetLayer;
                _viewshedOverlay.Graphics.AddRange(viewshedLayer.FeatureSet.Features.OfType<Graphic>());
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "Sample Error");
            }
            finally
            {
                //uiPanel.IsEnabled = true;
                ViewShedEnabled = true;
                //progress.Visibility = Visibility.Collapsed;
                ViewShedProgressVisible = false;
            }
        }

        private void DoOpenMission(object obj)
        {
            string fileName = obj.ToString();

            if (!String.IsNullOrWhiteSpace(fileName) && File.Exists(fileName))
            {
                try
                {
                    _mission.Load(fileName);

                    InitializeMapWithMission();
                }
                catch
                {

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
            string fileName = obj.ToString();

            if (!String.IsNullOrWhiteSpace(fileName))
            {
                _mission.Save(fileName);
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
            _militaryMessageLayer = new MessageLayer(SymbolDictionaryType.Mil2525c);
            _militaryMessageLayer.ID = Guid.NewGuid().ToString("D");
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
                        Console.WriteLine("ERROR : Control points not found for phase id {0}", phaseID);
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

            //RefreshMapLayers();
        }

        private void DoDragDropStarted(object obj)
        {
            _editState = EditState.DragDrop;
        }

        private void DoMissionHydrate(object obj)
        {
            HydrateMissionMessages(obj as Mission);
        }

        private void HydrateMissionMessages(Mission mission)
        {
            foreach (var phase in mission.PhaseList)
            {
                var phaseMessageList = _phaseMessageDictionary[phase.ID];

                if(phaseMessageList != null && phaseMessageList.Count > 0)
                {
                    foreach (var msgID in phaseMessageList)
                    {
                        var temp = new PersistentMessage()
                        {
                            ID = msgID
                        };

                        // get properties
                        var ml = GetMessageLayer(phase.ID);

                        if (ml != null)
                        {
                            //TODO revisit
                            //phase.VisibleTimeExtent = _messageLayerList.Where(s => s.MessageLayer.ID == phase.ID).First().VisibleTimeExtent;

                            var msg = ml.GetMessage(msgID);

                            //temp.CorrectProperties = msg;
                            temp.PropertyItems = new List<PropertyItem>();

                            for (int x = 0; x < msg.Count; x++)
                            {
                                temp.PropertyItems.Add(new PropertyItem() { Key = msg.ElementAt(x).Key, Value = msg.ElementAt(x).Value });
                            }
                        }
                        // TODO revisit
                        //phase.PersistentMessages.Add(temp);
                    }
                }
            }
        }

        private MessageLayer GetMessageLayer(string layerID)
        {
            if (_map != null && _map.Layers.Count > 0)
            {
                var layer = _map.Layers.Where(l => l is MessageLayer && l.ID == layerID);

                if (layer != null && layer.Count() == 1)
                {
                    return layer.First() as MessageLayer;
                }
            }

            return null;
        }

        //private int GetCurrentMessageLayerIndex()
        //{
        //    if (_currentMessageLayer != null && _messageLayerList.Count > 0)
        //    {
        //        return _messageLayerList.IndexOf(_currentMessageLayer);
        //    }

        //    return -1;
        //}

        private void OnPhaseNext(object param)
        {
            if (CurrentPhaseIndex < _mission.PhaseList.Count - 1)
            {
                // clear any selections
                ClearSelectedMessage();

                CurrentPhaseIndex++;
            }
        }

        private void SetMapViewVisibleTimeExtent(TimeExtent timeExtent)
        {
            _mapView.TimeExtent = timeExtent;
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
            
            // refresh layers, this will honor any new time extents
            //RefreshMapLayers();
        }

        private void ExtendTimeExtentOnMilitaryMessages(int CurrentPhaseIndex)
        {
            // update any military message time extent to the next phase if current extent END matches current phase time extent END
            // this will allow the current phase symbols with unedited time extents to be included in the next phase

            var currentTimeExtentEnd = _mission.PhaseList[CurrentPhaseIndex].VisibleTimeExtent.End;
            var nextTimeExtentEnd = _mission.PhaseList[CurrentPhaseIndex + 1].VisibleTimeExtent.End;
            var nextPhaseID = _mission.PhaseList[CurrentPhaseIndex + 1].ID;

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

        private void OnCoordinateReadoutCommand(object obj)
        {
            string format = obj as string;

            if (!String.IsNullOrWhiteSpace(format))
            {
                switch (format)
                {
                    case "DD":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.DD;
                        break;
                    case "DMS":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.DMS;
                        break;
                    case "GARS":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.GARS;
                        break;
                    case "GEOREF":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.GEOREF;
                        break;
                    case "MGRS":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.MGRS;
                        break;
                    case "USNG":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.USNG;
                        break;
                    case "UTM":
                        _coordinateReadoutFormat = CoordinateReadoutFormat.UTM;
                        break;
                    default:
                        _coordinateReadoutFormat = CoordinateReadoutFormat.MGRS;
                        break;
                }
            }
        }

        private Symbol _pointSymbol;
        private Symbol _lineSymbol;
        private Symbol _polygonSymbol;
        private GraphicsOverlay _graphicsOverlay;
        private MensurationTask _mensurationTask;

        private async void OnMeasureCommand(object param)
        {
            if (_editState == EditState.None && _mapView != null && !_mapView.Editor.IsActive)
            {
                //_pointSymbol = layoutGrid.Resources["PointSymbol"] as Symbol;
                //_lineSymbol = layoutGrid.Resources["LineSymbol"] as Symbol;
                //_polygonSymbol = layoutGrid.Resources["PolygonSymbol"] as Symbol;

                _lineSymbol = new SimpleLineSymbol() { Color = System.Windows.Media.Colors.Red, Style = SimpleLineStyle.Solid, Width = 2 } as Symbol;

                _graphicsOverlay = _mapView.GraphicsOverlays["graphicsOverlay"];

                // World Topo Map doesn't support mensuration
                //var temp = _mapView.Map.Layers["World Topo Map"];
                var temp = _mapView.Map.Layers["TestMapServiceLayer"];

                _mensurationTask = new MensurationTask(new Uri((temp as ArcGISTiledMapServiceLayer).ServiceUri));

                //_mensurationTask.

                // lets do a basic distance measure
                try
                {
                    var line = await RequestUserShape(DrawShape.LineSegment, _lineSymbol) as Polyline;

                    // Requesting shape cancelled
                    if (line == null)
                        return;

                    var parameters = new MensurationLengthParameters()
                    {
                        AngularUnit = Esri.ArcGISRuntime.Geometry.AngularUnits.Degrees,//comboAngularUnit.SelectedItem as AngularUnit,
                        LinearUnit = Esri.ArcGISRuntime.Geometry.LinearUnits.Meters//comboLinearUnit.SelectedItem as LinearUnit
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
        private async Task<Esri.ArcGISRuntime.Geometry.Geometry> RequestUserShape(DrawShape drawShape, Symbol symbol)
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

            // viewshed
            _inputOverlay = _mapView.GraphicsOverlays["inputOverlay"];
            _viewshedOverlay = _mapView.GraphicsOverlays["ViewshedOverlay"];

            _gpTask = new Geoprocessor(new Uri(ViewshedServiceUrl));

            // setup any controllers that use the map view
            gotoXYToolController = new GotoXYToolController(mapView, this);

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

        void mapView_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
        {
            if (_map == null || _editState == EditState.Tool)
            {
                return;
            }

            _lastKnownPoint = e.GetPosition(_mapView);

            UpdateCoordinateReadout(_lastKnownPoint);

            var adjustedPoint = AdjustPointWithOffset(_lastKnownPoint);

            //if a selected symbol, move it
            if (_editState == EditState.Move && e.LeftButton == System.Windows.Input.MouseButtonState.Pressed)
            {
                UpdateCurrentMessage(_mapView.ScreenToLocation(adjustedPoint));
            }
        }

        private void UpdateCoordinateReadout(Point point)
        {
            var mp = _mapView.ScreenToLocation(point);

            if (mp == null)
                return;

            // we can do DD, DMS, GARS, GEOREF, MGRS, USNG, UTM
            switch (_coordinateReadoutFormat)
            {
                case CoordinateReadoutFormat.DD:
                    CoordinateReadout = ConvertCoordinate.ToDecimalDegrees(mp, 3);
                    break;
                case CoordinateReadoutFormat.DMS:
                    CoordinateReadout = ConvertCoordinate.ToDegreesMinutesSeconds(mp, 1);
                    break;
                case CoordinateReadoutFormat.GARS:
                    CoordinateReadout = ConvertCoordinate.ToGars(mp);
                    break;
                case CoordinateReadoutFormat.GEOREF:
                    CoordinateReadout = ConvertCoordinate.ToGeoref(mp, 4, true);
                    break;
                case CoordinateReadoutFormat.MGRS:
                    CoordinateReadout = ConvertCoordinate.ToMgrs(mp, MgrsConversionMode.Automatic, 5, true, true);
                    break;
                case CoordinateReadoutFormat.USNG:
                    CoordinateReadout = ConvertCoordinate.ToUsng(mp, 5, true, true);
                    break;
                case CoordinateReadoutFormat.UTM:
                    CoordinateReadout = ConvertCoordinate.ToUtm(mp, UtmConversionMode.None, true);
                    break;
                default:
                    CoordinateReadout = ConvertCoordinate.ToMgrs(mp, MgrsConversionMode.Automatic, 5, true, true);
                    break;
            }
        }

        private Point AdjustPointWithOffset(Point _lastKnownPoint)
        {
            return new Point(_lastKnownPoint.X + _pointOffset.X, _lastKnownPoint.Y + _pointOffset.Y);
        }

        void mapView_MouseLeftButtonUp(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            //if (_draw.IsEnabled)
            //    return;

            if (_editState == EditState.Move)
            {
                _editState = EditState.None;
            }
        }

        async void mapView_MouseLeftButtonDown(object sender, System.Windows.Input.MouseButtonEventArgs e)
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

                    if (point != null)
                    {
                        resultPoint.X = point.X - screenPoint.X;
                        resultPoint.Y = point.Y - screenPoint.Y;
                    }
                }
            }

            return resultPoint;
        }

        private async Task<Graphic> HitTestMessageLayerAsync(System.Windows.Input.MouseButtonEventArgs e)
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

        //private void RefreshMapLayers()
        //{
        //    if (_map == null)
        //    {
        //        return;
        //    }

        //    foreach (var layer in _map.Layers)
        //    {
        //        var ml = layer as MessageLayer;

        //        if (ml != null)
        //        {
        //            //TODO revisit
        //            //if (_messageLayerList.Where(s => s.MessageLayer.ID == ml.ID).First().VisibleTimeExtent.Intersects(_mapView.TimeExtent))
        //            //{
        //            //    ml.IsVisible = true;
        //            //}
        //            //else
        //            //{
        //            //    ml.IsVisible = false;
        //            //}
        //        }
        //    }
        //}

        //private void OnSetMessageLayer(object param)
        //{
        //    var messageLayer = param as TimeAwareMessageLayer;

        //    if (messageLayer != null)
        //    {
        //        _mapView.Map.Layers.Add(messageLayer.MessageLayer);
        //    }
        //}

        private void SelectMessage(Message message, bool isSelected)
        {
            if (_militaryMessageLayer == null || message == null)
                return;

            if (isSelected)
            {
                _currentMessage = message;
            }
            else
            {
                _currentMessage = null;
            }

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
            var tam = _mission.MilitaryMessages.Where(m => m.Id == msg.Id).First();

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

            RemoveMessageFromPhase(CurrentPhaseIndex, _mission.MilitaryMessages.Where(m => m.Id == message.Id).First());
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

        private SymbolViewModel _SelectedSymbol;
        private string _geometryType = String.Empty;

        // edit support
        //Graphic selectedPointGraphic;
        //Message selectedMessage;

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
            _SelectedSymbol = param as SymbolViewModel;

            //Cancel editing if started
            if (_mapView.Editor.Cancel.CanExecute(null))
            {
                _mapView.Editor.Cancel.Execute(null);
            }

            if (_SelectedSymbol != null)
            {
                Dictionary<string, string> values = (Dictionary<string, string>)_SelectedSymbol.Model.Values;
                _geometryType = values["GeometryType"];

                Esri.ArcGISRuntime.Geometry.Geometry geometry = null;

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
                        break;
                }

                _editState = EditState.Create;

                try
                {
                    // get geometry from editor
                    geometry = await _mapView.Editor.RequestShapeAsync(drawShape);

                    _editState = EditState.None;

                    // process symbol with geometry
                    ProcessSymbol(_SelectedSymbol, geometry);
                }
                catch (TaskCanceledException tex)
                {
                    // clean up when drawing task is canceled
                }
            }
        }

        private void ProcessSymbol(SymbolViewModel symbol, Esri.ArcGISRuntime.Geometry.Geometry geometry)
        {
            if (symbol == null || geometry == null)
            {
                return;
            }

            //create a new message
            var msg = new TimeAwareMilitaryMessage();

            // set default time extent
            msg.VisibleTimeExtent = new TimeExtent(_mission.PhaseList[CurrentPhaseIndex].VisibleTimeExtent.Start,
                                                    _mission.PhaseList[CurrentPhaseIndex].VisibleTimeExtent.End);

            //set the ID and other parts of the message
            msg.Id = Guid.NewGuid().ToString("D");
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
                    msg.Add(MilitaryMessage.ControlPointsPropertyName, point.X.ToString() + "," + point.Y.ToString());
                    break;
                case GeometryType.Polygon:
                    Polygon polygon = geometry as Polygon;
                    string cpts = string.Empty;
                    //foreach (var pt in polygon.Rings[0])
                    foreach (var pt in polygon.Parts)
                    {
                        foreach (var segpt in pt.GetPoints())
                        {
                            cpts += ";" + segpt.X.ToString() + "," + segpt.Y.ToString();
                        }
                    }
                    msg.Add(MilitaryMessage.ControlPointsPropertyName, cpts);
                    break;
                case GeometryType.Polyline:
                    Polyline polyline = geometry as Polyline;
                    cpts = string.Empty;

                    // TODO find a way to determine if polyline map points need adjustment based on symbol being drawn
                    var mpList = AdjustMapPoints(polyline, symbol);

                    foreach (var mp in mpList)
                    {
                        cpts += ";" + mp.X.ToString() + "," + mp.Y.ToString();
                    }

                    // WARNING, this is from the WPF Runtime, the .net Runtime doesn't have this
                    //if (_geometryControlType == "ArrowWithOffset")
                    //{
                    //    cpts += ";" + cpts.Split(new char[] { ';' }).Last();
                    //}

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
            if (_mission.MilitaryMessages.Where(m => m.Id == tam.Id).Count() == 0)
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
            if (polyline == null || polyline.Parts == null || polyline.Parts.Count() < 1)
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

                foreach (var point in points)
                {
                    if (point != points.Last())
                    {
                        mapPoints.Add(point);
                    }
                }

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

        private void AddNewMessage(SymbolViewModel symbolViewModel, System.Windows.Point p, string guid)
        {
            //create a new message
            var tam = new TimeAwareMilitaryMessage();

            // set default time extent
            tam.VisibleTimeExtent = new TimeExtent(_mission.PhaseList[CurrentPhaseIndex].VisibleTimeExtent.Start,
                                                    _mission.PhaseList[CurrentPhaseIndex].VisibleTimeExtent.End);

            //set the ID and other parts of the message
            //msg.Id = Guid.NewGuid().ToString();
            tam.Id = guid;
            tam.Add(MilitaryMessage.TypePropertyName, Constants.MSG_TYPE_POSITION_REPORT);
            tam.Add(MilitaryMessage.ActionPropertyName, Constants.MSG_ACTION_UPDATE);
            tam.Add(MilitaryMessage.WkidPropertyName, "3857");
            tam.Add(MilitaryMessage.SicCodePropertyName, symbolViewModel.SymbolID);
            tam.Add(MilitaryMessage.UniqueDesignationPropertyName, "1");

            // Construct the Control Points based on the geometry type of the drawn geometry.
            //MapPoint point = e.Geometry as MapPoint;
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
