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

        public string X { get; set; }

        public string Y { get; set; }

        public string SelectedItem { get; set; }

        private void OnGotoXYToolCommand(object obj)
        {
            var item = new GotoItem();
            item.X = X;
            item.Y = Y;

            if (SelectedItem != null && !String.IsNullOrWhiteSpace(SelectedItem))
            {
                var temp = SelectedItem.Split(new string[] { "1:" }, StringSplitOptions.None);
                if (temp.Count() == 2)
                {
                    item.Scale = temp[1];
                }
            }

            Mediator.NotifyColleagues(Constants.ACTION_GOTO_XY_COORDINATES, item);
        }
    }
}
