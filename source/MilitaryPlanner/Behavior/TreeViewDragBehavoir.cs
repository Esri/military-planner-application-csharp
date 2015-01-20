using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Windows.Controls;
using System.Windows.Interactivity;
using System.Windows;
using System.Windows.Media;
using System.Windows.Documents;
using System.Windows.Input;
using MilitaryPlanner.Helpers;

namespace MilitaryPlanner.DragDrop.UI.Behavior
{
    /// <summary>
    /// For enabling Drop on ItemsControl
    /// </summary>
    public class TreeViewDragBehavior : Behavior<ItemsControl>
    {
        private bool isMouseClicked = false;

        protected override void OnAttached()
        {
            base.OnAttached();
            this.AssociatedObject.MouseLeftButtonDown += new MouseButtonEventHandler(AssociatedObject_MouseLeftButtonDown);
            this.AssociatedObject.MouseLeftButtonUp += new MouseButtonEventHandler(AssociatedObject_MouseLeftButtonUp);
            this.AssociatedObject.MouseLeave += new MouseEventHandler(AssociatedObject_MouseLeave);
        }

        void AssociatedObject_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            isMouseClicked = true;
        }

        void AssociatedObject_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            isMouseClicked = false;
        }

        void AssociatedObject_MouseLeave(object sender, MouseEventArgs e)
        {
            if (isMouseClicked)
            {
                //set the item's DataContext as the data to be transferred
                IDragable dragObject = this.AssociatedObject.DataContext as IDragable;
                if (dragObject != null && dragObject.IsDragable)
                {
                    DataObject data = new DataObject();
                    data.SetData(dragObject.DataType, this.AssociatedObject.DataContext);
                    System.Windows.DragDrop.DoDragDrop(this.AssociatedObject, data, DragDropEffects.Move);
                    Mediator.NotifyColleagues(Constants.ACTION_DRAG_DROP_STARTED, data);
                }
            }
            isMouseClicked = false;
        }
    }
}
