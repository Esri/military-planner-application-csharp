using System.Windows;

namespace MilitaryPlanner.Views
{
    /// <summary>
    /// Interaction logic for EditMissionPhasesView.xaml
    /// </summary>
    public partial class EditMissionPhasesView : Window
    {
        public EditMissionPhasesView()
        {
            InitializeComponent();
        }

        private void okButton_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = true;
        }
    }
}
