using System.Windows.Controls.Primitives;
using MilitaryPlanner.ViewModels;

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
            ViewModel = new GotoXYToolViewModel();
            DataContext = ViewModel;
        }

        public GotoXYToolViewModel ViewModel { get; set; }
    }
}
