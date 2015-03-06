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
using System.Windows.Input;

namespace MilitaryPlanner.Helpers
{
    public class EventToCommand
    {
        #region Command

        public static ICommand GetCommand(DependencyObject obj)
        {
            return (ICommand)obj.GetValue(CommandProperty);
        }

        public static void SetCommand(DependencyObject obj, ICommand value)
        {
            obj.SetValue(CommandProperty, value);
        }

        public static readonly DependencyProperty CommandProperty =
            DependencyProperty.RegisterAttached("Command", typeof(ICommand), typeof(EventToCommand), new UIPropertyMetadata(null));

        #endregion

        #region CommandParameter

        public static object GetCommandParameter(DependencyObject obj)
        {
            return (object)obj.GetValue(CommandParameterProperty);
        }

        public static void SetCommandParameter(DependencyObject obj, object value)
        {
            obj.SetValue(CommandParameterProperty, value);
        }

        public static readonly DependencyProperty CommandParameterProperty =
    DependencyProperty.RegisterAttached("CommandParameter", typeof(object), typeof(EventToCommand), new UIPropertyMetadata(null));

        #endregion

        #region Event

        public static RoutedEvent GetEvent(DependencyObject obj)
        {
            return (RoutedEvent)obj.GetValue(EventProperty);
        }

        public static void SetEvent(DependencyObject obj, RoutedEvent value)
        {
            obj.SetValue(EventProperty, value);
        }

        public static readonly DependencyProperty EventProperty =
            DependencyProperty.RegisterAttached("Event", typeof(RoutedEvent), typeof(EventToCommand), new UIPropertyMetadata(null, EventChanged));

        #endregion

        static void EventChanged(DependencyObject sender, DependencyPropertyChangedEventArgs e)
        {
            var ele = sender as UIElement;
            if (ele != null)
                ele.AddHandler((RoutedEvent)e.NewValue, new RoutedEventHandler(DoCommand));
        }

        static void DoCommand(object sender, RoutedEventArgs e)
        {
            var ele = sender as FrameworkElement;
            if (ele != null)
            {
                var command = (ICommand)ele.GetValue(CommandProperty);
                if (command != null)
                {
                    var parameter = ele.GetValue(CommandParameterProperty);
                    parameter = parameter ?? e;
                    command.Execute(parameter);
                }
            }
        }

    }
}
