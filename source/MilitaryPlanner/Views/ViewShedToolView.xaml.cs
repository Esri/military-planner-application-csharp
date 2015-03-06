using System.Windows.Controls.Primitives;
using MilitaryPlanner.ViewModels;

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
            ViewModel = new ViewShedToolViewModel();
            DataContext = ViewModel;
        }

        public ViewShedToolViewModel ViewModel { get; set; }
    }
}
