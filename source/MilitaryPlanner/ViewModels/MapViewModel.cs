//using ESRI.ArcGIS.Client;
//using ESRI.ArcGIS.Client.AdvancedSymbology;
//using ESRI.ArcGIS.Client.Geometry;
//using ESRI.ArcGIS.Client.Symbols;
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

namespace MilitaryPlanner.ViewModels
{
    public class MapViewModel : BaseViewModel, IDropable
    {
        private enum EditState
        {
            Create,
            DragDrop,
            Move,
            None
        };

        private Point _lastKnownPoint;
        private Point _pointOffset = new Point();
        private MapView _mapView;
        private Map _map;
        private Message _currentMessage;
        private EditState _editState = EditState.None;
        private List<TimeAwareMessageLayer> _messageLayerList = new List<TimeAwareMessageLayer>();
        private TimeAwareMessageLayer _currentMessageLayer;
        private TimeExtent _currentTimeExtent = new TimeExtent(DateTime.Now);
        private int _messageLayerCount = 1;
        //private List<string> _messageIDList = new List<string>();
        //TODO change this dictionary to be string key for phase ID, and string list of message ID's
        //private Dictionary<string, string> _messageDictionary = new Dictionary<string, string>();
        private Dictionary<string, List<string>> _phaseMessageDictionary = new Dictionary<string, List<string>>();

        public RelayCommand SetMapCommand { get; set; }
        //public RelayCommand SetMessageLayerCommand { get; set; }
        public RelayCommand PhaseAddCommand { get; set; }
        public RelayCommand PhaseBackCommand { get; set; }
        public RelayCommand PhaseNextCommand { get; set; }

        public RelayCommand MeasureCommand { get; set; }

        public MapViewModel()
        {
            Mediator.Register(Constants.ACTION_SELECTED_SYMBOL_CHANGED, DoActionSymbolChanged);
            Mediator.Register(Constants.ACTION_CANCEL, DoActionCancel);
            Mediator.Register(Constants.ACTION_DELETE, DoActionDelete);
            Mediator.Register(Constants.ACTION_MISSION_LOADED, DoMissionLoaded);
            Mediator.Register(Constants.ACTION_MISSION_HYDRATE, DoMissionHydrate);
            Mediator.Register(Constants.ACTION_DRAG_DROP_STARTED, DoDragDropStarted);
            //Mediator.Register(Constants.ACTION_SLIDER_NEXT, OnPhaseNext);
            //Mediator.Register(Constants.ACTION_SLIDER_BACK, OnPhaseBack);

            SetMapCommand = new RelayCommand(OnSetMap);
            //SetMessageLayerCommand = new RelayCommand(OnSetMessageLayer);
            PhaseAddCommand = new RelayCommand(OnPhaseAdd);
            PhaseBackCommand = new RelayCommand(OnPhaseBack);
            PhaseNextCommand = new RelayCommand(OnPhaseNext);

            MeasureCommand = new RelayCommand(OnMeasureCommand);
            //AddMessageLayer();
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
                //foreach (var kvp in _messageDictionary.Where(s => s.Value.Equals(phase.ID)))
                //foreach (var kvp in _phaseMessageDictionary.Where(s => s.Key.Equals(phase.ID)))
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
                            phase.VisibleTimeExtent = _messageLayerList.Where(s => s.MessageLayer.ID == phase.ID).First().VisibleTimeExtent;

                            var msg = ml.GetMessage(msgID);

                            //temp.CorrectProperties = msg;
                            temp.PropertyItems = new List<PropertyItem>();

                            for (int x = 0; x < msg.Count; x++)
                            {
                                temp.PropertyItems.Add(new PropertyItem() { Key = msg.ElementAt(x).Key, Value = msg.ElementAt(x).Value });
                            }
                        }

                        phase.PersistentMessages.Add(temp);
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

        private int GetCurrentMessageLayerIndex()
        {
            if (_currentMessageLayer != null && _messageLayerList.Count > 0)
            {
                return _messageLayerList.IndexOf(_currentMessageLayer);
            }

            return -1;
        }

        private void OnPhaseNext(object param)
        {
            if (!_currentMessageLayer.Equals(_messageLayerList.Last()))
            {
                var temp = GetCurrentMessageLayerIndex() + 1;
                Mediator.NotifyColleagues(Constants.ACTION_PHASE_NEXT, temp);
                SetCurrentMessageLayer(temp);
            }
        }

        private void SetCurrentMessageLayer(int index)
        {
            if (index >= 0 && index < _messageLayerList.Count)
            {
                _currentMessageLayer = _messageLayerList[index];

                //_map.TimeExtent = _currentMessageLayer.VisibleTimeExtent;
                _mapView.TimeExtent = _currentMessageLayer.VisibleTimeExtent;

                //get phase and fire notifications for messages
                var phaseMessageList = _phaseMessageDictionary[_currentMessageLayer.MessageLayer.ID];

                foreach (var msgID in phaseMessageList)
                {
                    Mediator.NotifyColleagues(Constants.ACTION_ITEM_WITH_GUID_ADDED, msgID);
                }

                RefreshMapLayers();
            }
        }

        private void OnPhaseBack(object param)
        {
            if (!_currentMessageLayer.Equals(_messageLayerList.First()))
            {
                // clear any selections
                ClearSelectedMessage();

                var temp = GetCurrentMessageLayerIndex() - 1;
                Mediator.NotifyColleagues(Constants.ACTION_PHASE_BACK, temp);
                SetCurrentMessageLayer(temp);
            }
        }

        private void OnPhaseAdd(object param)
        {
            // Add a new message layer
            AddMessageLayer();
            // refresh layers, this will honor any new time extents
            RefreshMapLayers();
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

        private TimeAwareMessageLayer CreateMessageLayer(string displayName, string id, TimeExtent timeExtent, bool visible, SymbolDictionaryType symbolDictType)
        {
            var messageLayer = new MessageLayer()
            {
                DisplayName = displayName,
                ID = id,
                //VisibleTimeExtent = timeExtent,
                IsVisible = visible,
                SymbolDictionaryType = symbolDictType
            };

            var tamLayer = new TimeAwareMessageLayer()
            {
                MessageLayer = messageLayer,
                VisibleTimeExtent = timeExtent
            };

            return tamLayer;
        }

        private void AddMessageLayer(TimeAwareMessageLayer messageLayer, bool makeCurrent)
        {
            _messageLayerList.Add(messageLayer);

            if (makeCurrent)
            {
                _currentMessageLayer = messageLayer;
                _mapView.TimeExtent = messageLayer.VisibleTimeExtent;
                _currentTimeExtent = messageLayer.VisibleTimeExtent;
            }

            OnSetMessageLayer(messageLayer);
        }

        private void AddMessageLayer()
        {
            if (_messageLayerList.Count <= 0)
            {
                // default message layer
                var messageLayer = CreateMessageLayer(String.Format("Message Layer {0}",_messageLayerCount++),
                                                      Guid.NewGuid().ToString("D"),
                                                      _currentTimeExtent,
                                                      true,
                                                      SymbolDictionaryType.Mil2525c);

                // add message layer to list
                _messageLayerList.Add(messageLayer);
                // set this layer as the current message layer
                _currentMessageLayer = messageLayer;

                // initialize message layer
                OnSetMessageLayer(messageLayer);

                // set the map view to the current time extent
                _mapView.TimeExtent = _currentTimeExtent;

                // notify colleagues of new layer
                Mediator.NotifyColleagues(Constants.ACTION_MSG_LAYER_ADDED, messageLayer);
            }
            else
            {
                // new message layer
                var messageLayer = new MessageLayer()
                {
                    DisplayName = String.Format("Message Layer {0}", _messageLayerCount++),
                    ID = Guid.NewGuid().ToString("D"),
                    //VisibleTimeExtent = GetNewMessageLayerTimeExtent(),
                    IsVisible = true,
                    SymbolDictionaryType = SymbolDictionaryType.Mil2525c
                };

                var tamLayer = new TimeAwareMessageLayer()
                {
                    MessageLayer = messageLayer,
                    VisibleTimeExtent = GetNewMessageLayerTimeExtent()
                };

                _messageLayerList.Add(tamLayer);
                _currentMessageLayer = tamLayer;

                OnSetMessageLayer(tamLayer);
                
                _mapView.TimeExtent = tamLayer.VisibleTimeExtent;
                _currentTimeExtent = tamLayer.VisibleTimeExtent;

                Mediator.NotifyColleagues(Constants.ACTION_MSG_LAYER_ADDED, messageLayer);

                AddPreviousLayerSymbols();
            }
        }

        private void AddPreviousLayerSymbols()
        {
            if (_messageLayerList.Count > 1)
            {
                var previousMessageLayer = _messageLayerList[_messageLayerList.Count - 2];

                //foreach (var msgKVP in _messageDictionary.Where(kvp => kvp.Value == previousMessageLayer.ID))
                //foreach(var phaseKVP in _phaseMessageDictionary.Where(kvp => kvp.Key == previousMessageLayer.ID))

                var phaseMessageList = _phaseMessageDictionary[previousMessageLayer.MessageLayer.ID];

                if (phaseMessageList != null && phaseMessageList.Count > 0)
                {
                    foreach (var phaseMessageID in phaseMessageList)
                    {
                        var oldMsg = previousMessageLayer.MessageLayer.GetMessage(phaseMessageID);

                        //TODO test guid
                        //oldMsg.Id = Guid.NewGuid().ToString();

                        if (oldMsg.ContainsKey(Constants.MSG_ACTION_KEY_NAME))
                        {
                            oldMsg[Constants.MSG_ACTION_KEY_NAME] = "update";
                        }

                        if (ProcessMessage(_currentMessageLayer.MessageLayer, oldMsg))
                        {
                            Mediator.NotifyColleagues(Constants.ACTION_ITEM_WITH_GUID_ADDED, oldMsg.Id);
                        }
                    }
                }
            }
        }

        private TimeExtent GetNewMessageLayerTimeExtent()
        {
            // we are doing a 1 hour time span for now
            return _messageLayerList.Last().VisibleTimeExtent.Offset(new TimeSpan(0, 1, 0));
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
            //_draw = new Draw(map);

            mapView.MouseLeftButtonDown += mapView_MouseLeftButtonDown;//map_MouseLeftButtonDown;
            mapView.MouseLeftButtonUp += mapView_MouseLeftButtonUp;
            mapView.MouseMove += mapView_MouseMove;

            // add default message layer
            AddMessageLayer();
        }

        void mapView_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
        {
            if (_map == null)
            {
                return;
            }

            _lastKnownPoint = e.GetPosition(_mapView);

            var adjustedPoint = AdjustPointWithOffset(_lastKnownPoint);

            //if a selected symbol, move it
            if (_editState == EditState.Move && e.LeftButton == System.Windows.Input.MouseButtonState.Pressed)
            {
                UpdateCurrentMessage(_mapView.ScreenToLocation(adjustedPoint));
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
            //if (_draw.IsEnabled)
            //    return;

            if (_editState == EditState.Create)
            {
                //e.Handled = false;
                return;
            }

            //if (_currentMessage != null)
            //{
            //    e.Handled = true;
            //    _editState = EditState.Move;
            //}
            if (_editState == EditState.None)
            {
                // hit test on message layer
                if (_currentMessageLayer != null)
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
            }
        }

        private void SelectMessageGraphic(Graphic graphic)
        {
            if (graphic == null)
                return;

            if (graphic.Attributes.ContainsKey(Constants.MSG_ID_KEY_NAME))
            {
                var selectMessage = _currentMessageLayer.MessageLayer.GetMessage(graphic.Attributes[Constants.MSG_ID_KEY_NAME].ToString());
                SelectMessage(selectMessage, true);
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
            if (_mapView != null && _currentMessageLayer != null)
            {
                foreach (var subLayer in _currentMessageLayer.MessageLayer.ChildLayers)
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

        private void RefreshMapLayers()
        {
            if (_map == null)
            {
                return;
            }

            foreach (var layer in _map.Layers)
            {
                var ml = layer as MessageLayer;

                if (ml != null)
                {
                    if (_messageLayerList.Where(s => s.MessageLayer.ID == ml.ID).First().VisibleTimeExtent.Intersects(_mapView.TimeExtent))
                    {
                        ml.IsVisible = true;
                    }
                    else
                    {
                        ml.IsVisible = false;
                    }
                }
            }
        }

        private void OnSetMessageLayer(object param)
        {
            var messageLayer = param as TimeAwareMessageLayer;

            if (messageLayer != null)
            {
                _mapView.Map.Layers.Add(messageLayer.MessageLayer);
                //_map.Layers.Add(messageLayer);
            }
        }

        private void SelectMessage(Message message, bool isSelected)
        {
            if (_currentMessageLayer == null || message == null)
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

            _currentMessageLayer.MessageLayer.ProcessMessage(msg);
        }

        private void UpdateCurrentMessage(MapPoint mapPoint)
        {
            if (_currentMessage != null && _currentMessageLayer != null)
            {
                var msg = new MilitaryMessage(_currentMessage.Id, MilitaryMessageType.PositionReport, MilitaryMessageAction.Update, new List<MapPoint>() { mapPoint });

                _currentMessageLayer.MessageLayer.ProcessMessage(msg);
            }
        }

        private void RemoveMessage(Message message)
        {
            var msg = new MilitaryMessage(message.Id, MilitaryMessageType.PositionReport, MilitaryMessageAction.Remove);
            _currentMessageLayer.MessageLayer.ProcessMessage(msg);

            //if (_messageDictionary.ContainsKey(message.Id))
            //{
            //    _messageDictionary.Remove(message.Id);
            //    // notify removal of item with guid
            //    Mediator.NotifyColleagues(Constants.ACTION_ITEM_WITH_GUID_REMOVED, message.Id);
            //}

            if (_phaseMessageDictionary[_currentMessageLayer.MessageLayer.ID].Contains(message.Id))
            {
                _phaseMessageDictionary[_currentMessageLayer.MessageLayer.ID].Remove(message.Id);
                Mediator.NotifyColleagues(Constants.ACTION_ITEM_WITH_GUID_REMOVED, message.Id);
            }
        }

        //private Draw _draw;
        //private MessageLayer _messageLayer;
        private SymbolViewModel _SelectedSymbol;
        private string _geometryType = String.Empty;

        // edit support
        //Graphic selectedPointGraphic;
        Message selectedMessage;

        private void DoMissionLoaded(object obj)
        {
            var mission = obj as Mission;

            if(mission == null)
            {
                return;
            }

            // clear out current layers
            ClearMessageLayers();

            foreach (var phase in mission.PhaseList)
            {
                var first = phase.Equals(mission.PhaseList.First());
                // add message layer
                var messageLayer = CreateMessageLayer(phase.Name, phase.ID, phase.VisibleTimeExtent, first, SymbolDictionaryType.Mil2525c);

                AddMessageLayer(messageLayer, first);

                //Mediator.NotifyColleagues(Constants.ACTION_MSG_LAYER_ADDED, messageLayer);

                foreach (var pm in phase.PersistentMessages)
                {
                    var message = new Message();

                    //message.Id = pm.ID;

                    foreach (var item in pm.PropertyItems)
                    {
                        if (item.Key.ToLower().Contains(Constants.MSG_ACTION_KEY_NAME))
                        {
                            item.Value = "update";
                        }

                        message.Add(item.Key, item.Value);
                    }

                    //messageLayer.ProcessMessage(message);
                    ProcessMessage(messageLayer.MessageLayer, message);
                }
            }
        }

        private void ClearMessageLayers()
        {
            if (_map == null)
            {
                return;
            }

            var mls = _map.Layers.Where(l => l is MessageLayer).ToList();

            foreach (var item in mls)
            {
                _map.Layers.Remove(item);
            }

            _messageLayerList.Clear();
        }

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
                if (_mapView.Editor.IsActive)
                {
                    //_mapView.Editor.Cancel;
                }
            }
            //if (_draw != null)
            //{
            //    _draw.IsEnabled = false;
            //}
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

                
                //_draw.LineSymbol = new SimpleLineSymbol()
                //{
                //    Color = new SolidColorBrush(Colors.Yellow),
                //    Style = SimpleLineSymbol.LineStyle.Solid,
                //    Width = 2
                //};
                //_draw.FillSymbol = new SimpleFillSymbol()
                //{
                //    BorderBrush = new SolidColorBrush(Colors.Yellow),
                //    BorderThickness = 1,
                //    Fill = new SolidColorBrush(Colors.Green)
                //};

                //_draw.DrawComplete -= _draw_DrawComplete;
                //_draw.DrawComplete += _draw_DrawComplete;

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

                    //_draw.IsEnabled = (_draw.DrawMode != DrawMode.None);
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
            Message msg = new Message();

            //set the ID and other parts of the message
            msg.Id = Guid.NewGuid().ToString();
            msg.Add("_type", Constants.MSG_TYPE_POSITION_REPORT);
            msg.Add(Constants.MSG_ACTION_KEY_NAME, "update");
            msg.Add("_wkid", "3857");
            //msg.Add("_wkid", _draw.Map.SpatialReference.WKID.ToString());
            msg.Add("sic", symbol.SymbolID);
            msg.Add("uniquedesignation", "1");

            // Construct the Control Points based on the geometry type of the drawn geometry.
            switch (geometry.GeometryType)
            {
                case GeometryType.Point:
                    MapPoint point = geometry as MapPoint;
                    msg.Add("_control_points", point.X.ToString() + "," + point.Y.ToString());
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
                    msg.Add("_control_points", cpts);
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

                    msg.Add("_control_points", cpts);
                    break;
            }

            //Process the message
            if (ProcessMessage(_currentMessageLayer.MessageLayer, msg))
            {
                //_draw.IsEnabled = true;
            }
            else
            {
                MessageBox.Show("Failed to process message.");
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
            var mapPoints = new List<MapPoint>();

            if (drawShape == DrawShape.Arrow)
            {
                var tempPoly = polyline.Parts;
                //var mpList = new List<MapPoint>();
                MapPoint lastMapPoint = null;
                foreach (var pt in tempPoly)
                {
                    foreach (var segpt in pt.GetPoints())
                    {
                        if (segpt != pt.GetPoints().Last())
                        {
                            mapPoints.Add(segpt);
                        }
                        else
                        {
                            lastMapPoint = segpt;
                        }
                    }
                }

                mapPoints.Reverse();
                mapPoints.Add(lastMapPoint);
            }
            else
            {
                var tempPoly = polyline.Parts;

                foreach (var pt in tempPoly)
                {
                    foreach (var segpt in pt.GetPoints())
                    {
                        mapPoints.Add(segpt);
                    }
                }
            }

            return mapPoints;
        }

        //void _draw_DrawComplete(object sender, DrawEventArgs e)
        //{
        //    _draw.IsEnabled = false;

        //    //create a new message
        //    Message msg = new Message();

        //    //set the ID and other parts of the message
        //    msg.Id = Guid.NewGuid().ToString();
        //    msg.Add("_type", Constants.MSG_TYPE_POSITION_REPORT);
        //    msg.Add(Constants.MSG_ACTION_KEY_NAME, "update");
        //    msg.Add("_wkid", "3857");
        //    //msg.Add("_wkid", _draw.Map.SpatialReference.WKID.ToString());
        //    msg.Add("sic", _SelectedSymbol.SymbolID);
        //    msg.Add("uniquedesignation", "1");

        //    // Construct the Control Points based on the geometry type of the drawn geometry.
        //    switch (_draw.DrawMode)
        //    {
        //        case DrawMode.Point:
        //            MapPoint point = e.Geometry as MapPoint;
        //            msg.Add("_control_points", point.X.ToString() + "," + point.Y.ToString());
        //            break;
        //        case DrawMode.Polygon:
        //            Polygon polygon = e.Geometry as Polygon;
        //            string cpts = string.Empty;
        //            foreach (var pt in polygon.Rings[0])
        //            {
        //                cpts += ";" + pt.X.ToString() + "," + pt.Y.ToString();
        //            }
        //            msg.Add("_control_points", cpts);
        //            break;
        //        case DrawMode.Polyline:
        //            Polyline polyline = e.Geometry as Polyline;
        //            cpts = string.Empty;
        //            foreach (var pt in polyline.Paths[0].Reverse())
        //            {
        //                cpts += ";" + pt.X.ToString() + "," + pt.Y.ToString();
        //            }

        //            if (_geometryControlType == "ArrowWithOffset")
        //            {
        //                cpts += ";" + cpts.Split(new char[] { ';' }).Last();
        //            }

        //            msg.Add("_control_points", cpts);
        //            break;
        //    }

        //    //Process the message
        //    if (ProcessMessage(_currentMessageLayer, msg))
        //    {
        //        _draw.IsEnabled = true;
        //    }
        //    else
        //    {
        //        MessageBox.Show("Failed to process message.");
        //    }
        //}

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
            Message msg = new Message();

            //set the ID and other parts of the message
            //msg.Id = Guid.NewGuid().ToString();
            msg.Id = guid;
            msg.Add("_type", Constants.MSG_TYPE_POSITION_REPORT);
            msg.Add(Constants.MSG_ACTION_KEY_NAME, "update");
            msg.Add("_wkid", "3857");
            //msg.Add("_wkid", _draw.Map.SpatialReference.WKID.ToString());
            msg.Add("sic", symbolViewModel.SymbolID);
            msg.Add("uniquedesignation", "1");

            // Construct the Control Points based on the geometry type of the drawn geometry.
            //MapPoint point = e.Geometry as MapPoint;
            var point = _mapView.ScreenToLocation(p);
            msg.Add("_control_points", point.X.ToString() + "," + point.Y.ToString());

            //Process the message
            if (ProcessMessage(_currentMessageLayer.MessageLayer, msg))
            {
                //_draw.IsEnabled = true;
            }
            else
            {
                MessageBox.Show("Failed to process message.");
            }
        }
    }
}
