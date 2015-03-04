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
    /// Interaction logic for NetworkingToolView.xaml
    /// </summary>
    public partial class NetworkingToolView : Popup
    {
        public NetworkingToolView()
        {
            InitializeComponent();
            this.ViewModel = new ViewModels.NetworkingToolViewModel();
            this.DataContext = ViewModel;
        }

        public ViewModels.NetworkingToolViewModel ViewModel { get; set; }
    }
}
