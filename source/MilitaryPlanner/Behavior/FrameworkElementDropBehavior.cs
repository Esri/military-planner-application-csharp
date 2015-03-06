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
using System;
using System.Windows;
using System.Windows.Interactivity;

namespace MilitaryPlanner.Behavior
{
    public class FrameworkElementDropBehavior : Behavior<FrameworkElement>
    {
        private Type _dataType; //the type of the data that can be dropped into this control
        //private FrameworkElementAdorner adorner;

        protected override void OnAttached()
        {
            base.OnAttached();

            AssociatedObject.AllowDrop = true;
            AssociatedObject.DragEnter += AssociatedObject_DragEnter;
            AssociatedObject.DragOver += AssociatedObject_DragOver;
            AssociatedObject.DragLeave += AssociatedObject_DragLeave;
            AssociatedObject.Drop += AssociatedObject_Drop;
        }

        void AssociatedObject_Drop(object sender, DragEventArgs e)
        {
            if (_dataType != null)
            {
                //if the data type can be dropped 
                if (e.Data.GetDataPresent(_dataType))
                {
                    //drop the data
                    IDropable target = AssociatedObject.DataContext as IDropable;
                    //var point = e.GetPosition(this.AssociatedObject.DataContext as IInputElement);
                    if (target != null) target.Drop(e.Data.GetData(_dataType), e);

                    //remove the data from the source
                    IDragable source = e.Data.GetData(_dataType) as IDragable;
                    if (source != null) source.Remove(e.Data.GetData(_dataType));
                }
            }

            //if (this.adorner != null)
            //    this.adorner.Remove();

            e.Handled = true;
        }

        void AssociatedObject_DragLeave(object sender, DragEventArgs e)
        {
            //if (this.adorner != null)
            //    this.adorner.Remove();

            e.Handled = true;
        }

        void AssociatedObject_DragOver(object sender, DragEventArgs e)
        {
            if (_dataType != null)
            {
                //if item can be dropped
                if (e.Data.GetDataPresent(_dataType))
                {
                    //give mouse effect
                    SetDragDropEffects(e);

                    //draw the dots
                    //if (this.adorner != null)
                    //    this.adorner.Update();
                }
            }
            e.Handled = true;
        }

        void AssociatedObject_DragEnter(object sender, DragEventArgs e)
        {
            //if the DataContext implements IDropable, record the data type that can be dropped
            if (_dataType == null)
            {
                var dropObject = AssociatedObject.DataContext as IDropable;

                if (dropObject != null)
                {
                    _dataType = dropObject.DataType;
                }
            }

            //if (this.adorner == null)
            //    this.adorner = new FrameworkElementAdorner(sender as UIElement);
            e.Handled = true;
        }

        /// <summary>
        /// Provides feedback on if the data can be dropped
        /// </summary>
        /// <param name="e"></param>
        private void SetDragDropEffects(DragEventArgs e)
        {
            e.Effects = DragDropEffects.None;  //default to None

            //if the data type can be dropped 
            if (e.Data.GetDataPresent(_dataType))
            {
                e.Effects = DragDropEffects.Move;
            }
        }
    }
}
