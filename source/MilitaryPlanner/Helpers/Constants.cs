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
        public const string ACTION_SAVE_MISSION = "SaveMission";
        public const string ACTION_OPEN_MISSION = "OpenMission";
        public const string ACTION_MSG_PROCESSED = "MessageProcessed";
        public const string ACTION_PHASE_ADDED = "PhaseAdded";
        public const string ACTION_PHASE_NEXT = "PhaseNext";
        public const string ACTION_PHASE_BACK = "PhaseBack";
        public const string ACTION_PHASE_INDEX_CHANGED = "PhaseIndexChanged";
        public const string ACTION_ITEM_WITH_GUID_REMOVED = "ItemWithGuidRemoved";
        public const string ACTION_ITEM_WITH_GUID_ADDED = "ItemWithGuidAdded";
        public const string ACTION_DRAG_DROP_STARTED = "DragDropStart";
        public const string ACTION_DRAG_DROP_ENDED = "DragDropEnded";

        public const string ACTION_EDIT_MISSION_PHASES = "EditMissionPhases";
        public const string ACTION_MISSION_CLONED = "EditMissionCloned";

        public const string MSG_ACTION_UPDATE = "update";
        public const string MSG_ACTION_REMOVE = "remove";
        public const string MSG_TYPE_POSITION_REPORT = "position_report";

        public const string ACTION_GOTO_XY_COORDINATES = "ActionGotoXYCoordinates";
    }
}
