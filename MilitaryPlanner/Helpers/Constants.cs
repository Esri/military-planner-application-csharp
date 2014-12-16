using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MilitaryPlanner.Helpers
{
    static public class Constants
    {
        public const string ACTION_SELECTED_SYMBOL_CHANGED = "SelectedSymbolChanged";
        public const string ACTION_CANCEL = "ActionCancel";
        public const string ACTION_DELETE = "ActionDelete";
        public const string ACTION_MSG_LAYER_ADDED = "MessageLayerAdded";
        public const string ACTION_MSG_LAYER_REMOVED = "MessageLayerRemoved";
        public const string ACTION_MISSION_LOADED = "MissionLoaded";
        public const string ACTION_MISSION_HYDRATE = "MissionHydrate";
        public const string ACTION_MSG_PROCESSED = "MessageProcessed";
        public const string ACTION_SLIDER_NEXT = "SliderNext";
        public const string ACTION_SLIDER_BACK = "SliderBack";
        public const string ACTION_ITEM_WITH_GUID_REMOVED = "ItemWithGuidRemoved";
        public const string ACTION_ITEM_WITH_GUID_ADDED = "ItemWithGuidAdded";

        public const string MSG_TYPE_POSITION_REPORT = "position_report";
    }
}
