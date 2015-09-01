using System.Windows;
using MilitaryPlanner.ViewModels;

namespace MilitaryPlanner.Views
{
    /// <summary>
    /// Interaction logic for NetworkingToolView.xaml
    /// </summary>
    public partial class NetworkingToolView : Window
    {
        public NetworkingToolView()
        {
            InitializeComponent();
            ViewModel = new NetworkingToolViewModel();
            DataContext = ViewModel;
        }

        public NetworkingToolViewModel ViewModel { get; set; }

        protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
        {
            e.Cancel = true;
            ViewModel.CloseToolCommand.Execute(null);
        }
    }
}
