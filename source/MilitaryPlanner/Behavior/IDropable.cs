using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Windows;

namespace MilitaryPlanner.DragDrop.UI.Behavior
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
        /// <param name="index">optional: The index location to insert the data</param>
        void Drop(object data, DragEventArgs e);
    }
}
