using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
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
    /// Interaction logic for PaletteSearch.xaml
    /// </summary>
    public partial class PaletteSearchView : UserControl
    {
        public PaletteSearchView()
        {
            InitializeComponent();
        }

        private void SymbolListBox_PreviewMouseDown(object sender, MouseButtonEventArgs e)
        {
            // Reset the selected item so that every mouse click of the listbox generates a selectionchanged event
            SymbolListBox.SelectedItem = null;
        }
    }
}
