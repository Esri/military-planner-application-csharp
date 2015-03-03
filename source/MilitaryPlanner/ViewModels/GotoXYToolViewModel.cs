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

        private void OnGotoXYToolCommand(object obj)
        {
            
        }
    }
}
