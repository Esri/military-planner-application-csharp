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

namespace MilitaryPlanner.ViewModels
{
    public class MapViewModel : BaseViewModel, IDropable
    {
        private enum EditState
        {
            Create,
            Move,
            None
        };

        private Point _lastKnownPoint;
        private MapView _mapView;
        private Map _map;
        private Message _currentMessage;
        private EditState _editState = EditState.None;
        private List<MessageLayer> _messageLayerList = new List<MessageLayer>();
        private MessageLayer _currentMessageLayer;
        private TimeExtent _currentTimeExtent = new TimeExtent(DateTime.Now);
        private int _messageLayerCount = 1;
        //private List<string> _messageIDList = new List<string>();
        //TODO change this dictionary to be string key for phase ID, and string list of message ID's
        //private Dictionary<string, string> _messageDictionary = new Dictionary<string, string>();
        private Dictionary<string, List<string>> _phaseMessageDictionary = new Dictionary<string, List<string>>();

        public RelayCommand SetMapCommand { get; set; }
        //public RelayCommand SetMessageLayerCommand { get; set; }
        public RelayCommand SlideAddCommand { get; set; }
        public RelayCommand SlideBackCommand { get; set; }
        public RelayCommand SlideNextCommand { get; set; }

        public MapViewModel()
        {
            Mediator.Register(Constants.ACTION_SELECTED_SYMBOL_CHANGED, DoActionSymbolChanged);
            Mediator.Register(Constants.ACTION_CANCEL, DoActionCancel);
            Mediator.Register(Constants.ACTION_DELETE, DoActionDelete);
            Mediator.Register(Constants.ACTION_MISSION_LOADED, DoMissionLoaded);
            Mediator.Register(Constants.ACTION_MISSION_HYDRATE, DoMissionHydrate);
            //Mediator.Register(Constants.ACTION_SLIDER_NEXT, OnSlideNext);
            //Mediator.Register(Constants.ACTION_SLIDER_BACK, OnSlideBack);

            SetMapCommand = new RelayCommand(OnSetMap);
            //SetMessageLayerCommand = new RelayCommand(OnSetMessageLayer);
            SlideAddCommand = new RelayCommand(OnSlideAdd);
            SlideBackCommand = new RelayCommand(OnSlideBack);
            SlideNextCommand = new RelayCommand(OnSlideNext);

            //AddMessageLayer();
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
                            //TODO phase visible time Extent from message layer?
                            //phase.VisibleTimeExtent = ml.VisibleTimeExtent;

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

        private void OnSlideNext(object param)
        {
            if (!_currentMessageLayer.Equals(_messageLayerList.Last()))
            {
                var temp = GetCurrentMessageLayerIndex() + 1;
                Mediator.NotifyColleagues(Constants.ACTION_SLIDER_NEXT, temp);
                SetCurrentMessageLayer(temp);
            }
        }

        private void SetCurrentMessageLayer(int index)
        {
            if (index >= 0 && index < _messageLayerList.Count)
            {
                _currentMessageLayer = _messageLayerList[index];

                //_map.TimeExtent = _currentMessageLayer.VisibleTimeExtent;

                //get phase and fire notifications for messages
                var phaseMessageList = _phaseMessageDictionary[_currentMessageLayer.ID];

                foreach (var msgID in phaseMessageList)
                {
                    Mediator.NotifyColleagues(Constants.ACTION_ITEM_WITH_GUID_ADDED, msgID);
                }

                RefreshMapLayers();
            }
        }

        private void OnSlideBack(object param)
        {
            if (!_currentMessageLayer.Equals(_messageLayerList.First()))
            {
                var temp = GetCurrentMessageLayerIndex() - 1;
                Mediator.NotifyColleagues(Constants.ACTION_SLIDER_BACK, temp);
                SetCurrentMessageLayer(temp);
            }
        }

        private void OnSlideAdd(object param)
        {
            AddMessageLayer();

            RefreshMapLayers();
        }


        private MessageLayer CreateMessageLayer(string displayName, string id, TimeExtent timeExtent, bool visible, SymbolDictionaryType symbolDictType)
        {
            var messageLayer = new MessageLayer()
            {
                DisplayName = displayName,
                ID = id,
                //VisibleTimeExtent = timeExtent,
                IsVisible = visible,
                SymbolDictionaryType = symbolDictType
            };

            return messageLayer;
        }

        private void AddMessageLayer(MessageLayer messageLayer, bool makeCurrent)
        {
            _messageLayerList.Add(messageLayer);

            if (makeCurrent)
            {
                _currentMessageLayer = messageLayer;
                //_map.TimeExtent = messageLayer.VisibleTimeExtent;
                //_currentTimeExtent = messageLayer.VisibleTimeExtent;
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

                _messageLayerList.Add(messageLayer);
                _currentMessageLayer = messageLayer;

                OnSetMessageLayer(messageLayer);

                _mapView.TimeExtent = _currentTimeExtent;

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

                _messageLayerList.Add(messageLayer);
                _currentMessageLayer = messageLayer;

                OnSetMessageLayer(messageLayer);
                
                //TODO fix time extent
                //_mapView.TimeExtent = messageLayer.VisibleTimeExtent;
                //_currentTimeExtent = messageLayer.VisibleTimeExtent;

                

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

                var phaseMessageList = _phaseMessageDictionary[previousMessageLayer.ID];

                if (phaseMessageList != null && phaseMessageList.Count > 0)
                {
                    foreach (var phaseMessageID in phaseMessageList)
                    {
                        var oldMsg = previousMessageLayer.GetMessage(phaseMessageID);

                        //TODO test guid
                        //oldMsg.Id = Guid.NewGuid().ToString();

                        if (oldMsg.ContainsKey("_action"))
                        {
                            oldMsg["_action"] = "update";
                        }

                        if (ProcessMessage(_currentMessageLayer, oldMsg))
                        {
                            Mediator.NotifyColleagues(Constants.ACTION_ITEM_WITH_GUID_ADDED, oldMsg.Id);
                        }

                        //update phase message dictionary
                        //if (_currentMessageLayer.ProcessMessage(oldMsg))
                        //{
                        //    if (!_phaseMessageDictionary.ContainsKey(_currentMessageLayer.ID))
                        //    {
                        //        _phaseMessageDictionary.Add(_currentMessageLayer.ID, new List<string>());
                        //    }

                        //    _phaseMessageDictionary[_currentMessageLayer.ID].Add(oldMsg.Id);
                        //}
                    }
                }
            }
        }

        private TimeExtent GetNewMessageLayerTimeExtent()
        {
            //TODO fix time extent
            //return _messageLayerList.Last().VisibleTimeExtent.Offset(new TimeSpan(0, 0, 1));
            return new TimeExtent();
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

            mapView.MouseLeftButtonDown += map_MouseLeftButtonDown;
            mapView.MouseLeftButtonUp += map_MouseLeftButtonUp;
            mapView.MouseMove += map_MouseMove;

            // add default message layer
            AddMessageLayer();
        }

        void map_MouseMove(object sender, System.Windows.Input.MouseEventArgs e)
        {
            if (_map == null)
            {
                return;
            }

            _lastKnownPoint = e.GetPosition(_mapView);

            //if a selected symbol, move it
            if (_editState == EditState.Move)
            {
                UpdateCurrentMessage(_mapView.ScreenToLocation(_lastKnownPoint));
            }
        }

        void map_MouseLeftButtonUp(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            //if (_draw.IsEnabled)
            //    return;

            _editState = EditState.None;
        }

        void map_MouseLeftButtonDown(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            //if (_draw.IsEnabled)
            //    return;

            if (_currentMessage != null)
            {
                e.Handled = true;
                _editState = EditState.Move;
            }
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
                    //TODO fix time extent
                    //if (ml.VisibleTimeExtent.Intersects(_mapView.TimeExtent))
                    //{
                    //    ml.Visible = true;
                    //}
                    //else
                    //{
                    //    ml.Visible = false;
                    //}
                }
            }
        }

        private void OnSetMessageLayer(object param)
        {
            var messageLayer = param as MessageLayer;

            if (messageLayer != null)
            {
                //TODO mouse enter and leave event handler on message layer?
                //messageLayer.MouseEnter += messageLayer_MouseEnter;
                //messageLayer.MouseLeave += messageLayer_MouseLeave;

                _map.Layers.Add(messageLayer);
            }
        }

        //void messageLayer_MouseLeave(object sender, MessageEventArgs e)
        //{
        //    if (_editState == EditState.Move)
        //        return;

        //    SelectMessage(selectedMessage, false);
        //    selectedMessage = null;
        //}

        //void messageLayer_MouseEnter(object sender, MessageEventArgs e)
        //{
        //    if (_editState == EditState.Move)
        //        return;

        //    selectedMessage = e.Message;
        //    Console.WriteLine(e.Message.Id);
        //    SelectMessage(e.Message, true);
        //}

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

            //var msg = MessageHelper.CreateMilitarySelectMessage(message.Id, Constants.MSG_TYPE_POSITION_REPORT, isSelected);
            //_currentMessageLayer.ProcessMessage(msg);
        }

        private void UpdateCurrentMessage(MapPoint mapPoint)
        {
            if (_currentMessage != null && _currentMessageLayer != null)
            {
                //var msg = MessageHelper.CreateMilitaryUpdateMessage(_currentMessage.Id, Constants.MSG_TYPE_POSITION_REPORT, new List<MapPoint>(){mapPoint});
                //_currentMessageLayer.ProcessMessage(msg);
            }
        }

        private void RemoveMessage(Message message)
        {
            //var msg = MessageHelper.CreateMilitaryRemoveMessage(message.Id, Constants.MSG_TYPE_POSITION_REPORT);
            //_currentMessageLayer.ProcessMessage(msg);

            //if (_messageDictionary.ContainsKey(message.Id))
            //{
            //    _messageDictionary.Remove(message.Id);
            //    // notify removal of item with guid
            //    Mediator.NotifyColleagues(Constants.ACTION_ITEM_WITH_GUID_REMOVED, message.Id);
            //}

            if (_phaseMessageDictionary[_currentMessageLayer.ID].Contains(message.Id))
            {
                _phaseMessageDictionary[_currentMessageLayer.ID].Remove(message.Id);
                Mediator.NotifyColleagues(Constants.ACTION_ITEM_WITH_GUID_REMOVED, message.Id);
            }
        }

        //private Draw _draw;
        //private MessageLayer _messageLayer;
        private SymbolViewModel _SelectedSymbol;
        private string _geometryControlType = String.Empty;

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
                        if(item.Key.ToLower().Contains("_action"))
                        {
                            item.Value = "update";
                        }

                        message.Add(item.Key, item.Value);
                    }

                    //messageLayer.ProcessMessage(message);
                    ProcessMessage(messageLayer, message);
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
            //if (_draw != null)
            //{
            //    _draw.IsEnabled = false;
            //}
        }

        private void DoActionSymbolChanged(object param)
        {
            _SelectedSymbol = param as SymbolViewModel;

            if (_SelectedSymbol != null)
            {
                Dictionary<string, string> values = (Dictionary<string, string>)_SelectedSymbol.Model.Values;
                _geometryControlType = values["GeometryConversionType"];

                
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

                //switch (_geometryControlType)
                //{
                //    case "Point":
                //        _draw.DrawMode = DrawMode.Point;
                //        break;
                //    case "Polyline":
                //        _draw.DrawMode = DrawMode.Polyline;
                //        break;
                //    case "Polygon":
                //        _draw.DrawMode = DrawMode.Polygon;
                //        break;
                //    case "Circle":
                //        _draw.DrawMode = DrawMode.Circle;
                //        break;
                //    case "Rectangular":
                //        _draw.DrawMode = DrawMode.Rectangle;
                //        break;
                //    case "ArrowWithOffset":
                //        _draw.DrawMode = DrawMode.Polyline;
                //        break;
                //    default:
                //        break;
                //}
                //_draw.IsEnabled = (_draw.DrawMode != DrawMode.None);
            }
        }

        //void _draw_DrawComplete(object sender, DrawEventArgs e)
        //{
        //    _draw.IsEnabled = false;

        //    //create a new message
        //    Message msg = new Message();

        //    //set the ID and other parts of the message
        //    msg.Id = Guid.NewGuid().ToString();
        //    msg.Add("_type", Constants.MSG_TYPE_POSITION_REPORT);
        //    msg.Add("_action", "update");
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
        }

        private void AddNewMessage(SymbolViewModel symbolViewModel, System.Windows.Point p, string guid)
        {
            //create a new message
            Message msg = new Message();

            //set the ID and other parts of the message
            //msg.Id = Guid.NewGuid().ToString();
            msg.Id = guid;
            msg.Add("_type", Constants.MSG_TYPE_POSITION_REPORT);
            msg.Add("_action", "update");
            msg.Add("_wkid", "3857");
            //msg.Add("_wkid", _draw.Map.SpatialReference.WKID.ToString());
            msg.Add("sic", symbolViewModel.SymbolID);
            msg.Add("uniquedesignation", "1");

            // Construct the Control Points based on the geometry type of the drawn geometry.
            //MapPoint point = e.Geometry as MapPoint;
            var point = _mapView.ScreenToLocation(p);
            msg.Add("_control_points", point.X.ToString() + "," + point.Y.ToString());

            //Process the message
            if (ProcessMessage(_currentMessageLayer, msg))
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
