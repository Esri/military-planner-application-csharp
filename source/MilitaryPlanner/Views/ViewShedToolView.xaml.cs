using System.Windows;
using MilitaryPlanner.ViewModels;

namespace MilitaryPlanner.Views
{
    /// <summary>
    /// Interaction logic for ViewShedToolView.xaml
    /// </summary>
    public partial class ViewShedToolView : Window
    {
        public ViewShedToolView()
        {
            InitializeComponent();
            ViewModel = new ViewShedToolViewModel();
            DataContext = ViewModel;
        }

        public ViewShedToolViewModel ViewModel { get; set; }

        protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
        {
            e.Cancel = true;
            ViewModel.CloseToolCommand.Execute(null);
        }
    }
}
