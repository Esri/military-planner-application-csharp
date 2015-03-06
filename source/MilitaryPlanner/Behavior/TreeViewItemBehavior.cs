using System.Windows;
using System.Windows.Controls;

namespace MilitaryPlanner.Behavior
{
    public static class TreeViewItemBehavior
    {
        public static readonly DependencyProperty IsTempProperty = DependencyProperty.RegisterAttached("IsTemp", typeof(bool), typeof(TreeViewItemBehavior), new UIPropertyMetadata(false, OnIsTempChanged));

        static void OnIsTempChanged(DependencyObject sender, DependencyPropertyChangedEventArgs e)
        {
            var item = e.NewValue;
            var tvi = sender as TreeViewItem;
        }

        public static bool GetIsTemp(TreeViewItem treeViewItem)
        {
            return (bool)treeViewItem.GetValue(IsTempProperty);
        }

        public static void SetIsTemp(TreeViewItem treeViewItem, bool value)
        {
            treeViewItem.SetValue(IsTempProperty, value);
        }

        //public bool IsTemp
        //{
        //    get { return (bool)GetValue(IsTempProperty); }
        //    set { SetValue(IsTempProperty, value); }
        //}

//        private bool isMouseClicked = false;

        //protected void OnAttached()
        //{
        //    base.OnAttached();
        //    this.AssociatedObject.MouseLeftButtonDown += new MouseButtonEventHandler(AssociatedObject_MouseLeftButtonDown);
        //    this.AssociatedObject.MouseLeftButtonUp += new MouseButtonEventHandler(AssociatedObject_MouseLeftButtonUp);
        //    this.AssociatedObject.MouseLeave += new MouseEventHandler(AssociatedObject_MouseLeave);
        //}

        //void AssociatedObject_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        //{
        //    isMouseClicked = true;
        //}

        //void AssociatedObject_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        //{
        //    isMouseClicked = false;
        //}

        //void AssociatedObject_MouseLeave(object sender, MouseEventArgs e)
        //{
        //    if (isMouseClicked)
        //    {
        //        //set the item's DataContext as the data to be transferred
        //        //IDragable dragObject =  as IDragable;
        //        //if (dragObject != null)
        //        //{
        //        //    DataObject data = new DataObject();
        //        //    data.SetData(dragObject.DataType, this.AssociatedObject.DataContext);
        //        //    System.Windows.DragDrop.DoDragDrop(this.AssociatedObject, data, DragDropEffects.Move);
        //        //}
        //    }
        //    isMouseClicked = false;
        //}
    }
}
