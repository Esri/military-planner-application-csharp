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
    /// Interaction logic for ViewShedToolView.xaml
    /// </summary>
    public partial class ViewShedToolView : Popup
    {
        public ViewShedToolView()
        {
            InitializeComponent();
            this.ViewModel = new ViewModels.ViewShedToolViewModel();
            this.DataContext = ViewModel;
        }

        public ViewModels.ViewShedToolViewModel ViewModel { get; set; }
    }
}
