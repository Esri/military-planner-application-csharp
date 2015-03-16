using System.Windows;
using MilitaryPlanner.ViewModels;
using System.Windows.Controls.Primitives;

namespace MilitaryPlanner.Views
{
    /// <summary>
    /// Interaction logic for BasemapGalleryView.xaml
    /// </summary>
    public partial class BasemapGalleryView : Popup
    {
        public BasemapGalleryView()
        {
            InitializeComponent();
            ViewModel = new BasemapGalleryViewModel();
            DataContext = ViewModel;
        }

        public BasemapGalleryViewModel ViewModel { get; set; }
    }
}
