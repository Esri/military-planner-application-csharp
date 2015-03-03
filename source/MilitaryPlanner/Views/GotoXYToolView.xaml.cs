using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;

namespace MilitaryPlanner.Views
{
    /// <summary>
    /// Interaction logic for GotoXYToolView.xaml
    /// </summary>
    public partial class GotoXYToolView : Popup
    {
        public GotoXYToolView()
        {
            InitializeComponent();
            this.ViewModel = new ViewModels.GotoXYToolViewModel();
            this.DataContext = ViewModel;
        }

        public ViewModels.GotoXYToolViewModel ViewModel { get; set; }
    }
}
