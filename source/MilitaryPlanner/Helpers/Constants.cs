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
        public const string ACTION_CLONE_MISSION = "CloneMission";

        public const string MSG_ACTION_UPDATE = "update";
        public const string MSG_ACTION_REMOVE = "remove";
        public const string MSG_TYPE_POSITION_REPORT = "position_report";

        public const string ACTION_GOTO_XY_COORDINATES = "ActionGotoXYCoordinates";

        public const string ACTION_COORDINATE_READOUT_FORMAT_CHANGED = "ActionCoordinateReadoutFormatChanged";

        public const string ACTION_EDIT_GEOMETRY = "ActionEditGeometry";
        public const string ACTION_EDIT_UNDO = "ActionEditUndo";
        public const string ACTION_EDIT_REDO = "ActionEditRedo";

        public const string ACTION_UPDATE_BASEMAP = "ActionUpdateBasemap";

        public const int SAVE_AS_MISSION = 1;
        public const int SAVE_AS_GEOMESSAGES = 2;
        public const string SAVE_AS_DELIMITER = "::";
    }
}
