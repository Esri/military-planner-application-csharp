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
using System.Linq;
using MilitaryPlanner.Helpers;

namespace MilitaryPlanner.ViewModels
{
    public class GotoXYToolViewModel : BaseToolViewModel
    {
        public RelayCommand GotoXYToolCommand { get; set; }

        public GotoXYToolViewModel()
        {
            GotoXYToolCommand = new RelayCommand(OnGotoXYToolCommand);
        }

        public string Coordinate { get; set; }

        public string ScaleSelectedValue { get; set; }

        public string FormatSelectedValue { get; set; }

        private void OnGotoXYToolCommand(object obj)
        {
            var item = new GotoItem();

            if (!String.IsNullOrWhiteSpace(ScaleSelectedValue))
            {
                var temp = ScaleSelectedValue.Split(new[] { "1:" }, StringSplitOptions.None);
                if (temp.Count() == 2)
                {
                    item.Scale = temp[1];
                }
            }

            item.Coordinate = Coordinate;
            item.Format = FormatSelectedValue;

            Mediator.NotifyColleagues(Constants.ACTION_GOTO_XY_COORDINATES, item);
        }
    }
}
