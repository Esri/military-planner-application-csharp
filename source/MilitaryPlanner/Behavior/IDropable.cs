using System;
using System.Windows;

namespace MilitaryPlanner.Behavior
{
    interface IDropable
    {
        /// <summary>
        /// Type of the data item
        /// </summary>
        Type DataType { get; }

        /// <summary>
        /// Drop data into the collection.
        /// </summary>
        /// <param name="data">The data to be dropped</param>
        /// <param name="e">drag event args</param>
        void Drop(object data, DragEventArgs e);
    }
}
