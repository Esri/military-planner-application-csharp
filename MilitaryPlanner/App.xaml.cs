using System;
using System.Windows;
using ESRI.ArcGIS.Client;

namespace MilitaryPlanner
{
    /// <summary>
    /// Interaction logic for App.xaml
    /// </summary>
    public partial class App : Application
    {
        private void Application_Startup(object sender, StartupEventArgs e)
        {
            // Before initializing the ArcGIS Runtime first 
            // set the ArcGIS Runtime license by providing the license string 
            // obtained from the License Viewer tool.
            //ArcGISRuntime.SetLicense("Place the License String in here");

            // Initialize the ArcGIS Runtime before any components are created.
            try
            {
                ArcGISRuntime.Initialize();
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.ToString());

                // Exit application
                this.Shutdown();
            }

        }
    }


}
