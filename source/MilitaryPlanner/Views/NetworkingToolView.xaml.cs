using System.Windows.Controls.Primitives;
using MilitaryPlanner.ViewModels;

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
            ViewModel = new NetworkingToolViewModel();
            DataContext = ViewModel;
        }

        public NetworkingToolViewModel ViewModel { get; set; }
    }
}
