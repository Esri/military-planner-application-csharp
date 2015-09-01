using System.Windows;
using MilitaryPlanner.ViewModels;

namespace MilitaryPlanner.Views
{
    /// <summary>
    /// Interaction logic for GotoXYToolView.xaml
    /// </summary>
    public partial class GotoXYToolView : Window
    {
        public GotoXYToolView()
        {
            InitializeComponent();
            ViewModel = new GotoXYToolViewModel();
            DataContext = ViewModel;
        }

        public GotoXYToolViewModel ViewModel { get; set; }

        protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
        {
            e.Cancel = true;
            ViewModel.CloseToolCommand.Execute(null);
        }
    }
}
