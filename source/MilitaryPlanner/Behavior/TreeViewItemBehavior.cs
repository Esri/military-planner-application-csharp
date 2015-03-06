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
