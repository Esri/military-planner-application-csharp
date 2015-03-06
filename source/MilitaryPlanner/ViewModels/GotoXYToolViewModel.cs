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
