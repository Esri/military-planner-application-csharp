using System.Windows;
using MilitaryPlanner.ViewModels;

namespace MilitaryPlanner.Views
{
    /// <summary>
    /// Interaction logic for BasemapGalleryView.xaml
    /// </summary>
    public partial class BasemapGalleryView : Window
    {
        public BasemapGalleryView()
        {
            InitializeComponent();
            ViewModel = new BasemapGalleryViewModel();
            DataContext = ViewModel;
        }

        public BasemapGalleryViewModel ViewModel { get; set; }

        protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
        {
            e.Cancel = true;
            ViewModel.CloseToolCommand.Execute(null);
        }
    }
}
