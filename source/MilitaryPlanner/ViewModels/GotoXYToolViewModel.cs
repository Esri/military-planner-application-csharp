using MilitaryPlanner.Helpers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

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

            if (ScaleSelectedValue != null && !String.IsNullOrWhiteSpace(ScaleSelectedValue))
            {
                var temp = ScaleSelectedValue.Split(new string[] { "1:" }, StringSplitOptions.None);
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
