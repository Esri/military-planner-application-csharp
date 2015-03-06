using System.Windows;
using System.Windows.Input;
using System.Windows.Interactivity;

namespace MilitaryPlanner.Behavior
{
    public class FrameworkElementDragBehavior : Behavior<FrameworkElement>
    {
        private bool _isMouseClicked;

        protected override void OnAttached()
        {
            base.OnAttached();
            AssociatedObject.MouseLeftButtonDown += AssociatedObject_MouseLeftButtonDown;
            AssociatedObject.MouseLeftButtonUp += AssociatedObject_MouseLeftButtonUp;
            AssociatedObject.MouseLeave += AssociatedObject_MouseLeave;
        }

        void AssociatedObject_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            _isMouseClicked = true;
        }

        void AssociatedObject_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            _isMouseClicked = false;
        }

        void AssociatedObject_MouseLeave(object sender, MouseEventArgs e)
        {
            if (_isMouseClicked)
            {
                //set the item's DataContext as the data to be transferred
                IDragable dragObject = AssociatedObject.DataContext as IDragable;
                if (dragObject != null && dragObject.IsDragable && !dragObject.HasBeenDragged)
                {
                    DataObject data = new DataObject();
                    data.SetData(dragObject.DataType, AssociatedObject.DataContext);
                    DragDrop.DoDragDrop(AssociatedObject, data, DragDropEffects.Move);
                }
            }
            _isMouseClicked = false;
        }
    }
}
