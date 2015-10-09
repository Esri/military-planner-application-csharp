using System;
using System.Collections.Generic;
using System.IO;
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
using System.Windows.Shapes;

namespace MilitaryPlanner.Views
{
    /// <summary>
    /// Interaction logic for ADMainWindow.xaml
    /// </summary>
    public partial class ADMainWindow : Window
    {
        public ADMainWindow()
        {
            InitializeComponent();

            this.Loaded += new RoutedEventHandler(MainWindow_Loaded);
            this.Unloaded += new RoutedEventHandler(MainWindow_Unloaded);
        }

        void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            var serializer = new Xceed.Wpf.AvalonDock.Layout.Serialization.XmlLayoutSerializer(dockingManager);
            serializer.LayoutSerializationCallback += (s, args) =>
            {
                args.Content = args.Content;
            };

            if (File.Exists(@".\AvalonDock.config"))
                serializer.Deserialize(@".\AvalonDock.config");
        }

        void MainWindow_Unloaded(object sender, RoutedEventArgs e)
        {
            var serializer = new Xceed.Wpf.AvalonDock.Layout.Serialization.XmlLayoutSerializer(dockingManager);
            serializer.Serialize(@".\AvalonDock.config");
        }

        protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
        {
            base.OnClosing(e);
            // if window is minimized, restore to avoid opening minimized on next run
            if (WindowState == System.Windows.WindowState.Minimized)
            {
                WindowState = System.Windows.WindowState.Normal;
            }
        }

    }
}
