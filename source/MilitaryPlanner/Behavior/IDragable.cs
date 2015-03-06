using System;

namespace MilitaryPlanner.Behavior
{
    interface IDragable
    {
        bool HasBeenDragged { get; set; }
        bool IsDragable { get; }//set; }
        /// <summary>
        /// Type of the data item
        /// </summary>
        Type DataType { get; }

        /// <summary>
        /// Remove the object from the collection
        /// </summary>
        void Remove(object i);
    }
}
