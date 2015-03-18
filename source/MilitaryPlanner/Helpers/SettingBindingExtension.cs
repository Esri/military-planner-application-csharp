using System.Windows.Data;
using MilitaryPlanner.Properties;

namespace MilitaryPlanner.Helpers
{
    public class SettingBindingExtension : Binding
    {
        public SettingBindingExtension()
        {
            Initialize();
        }

        public SettingBindingExtension(string path)
            : base(path)
        {
            Initialize();
        }

        private void Initialize()
        {
            this.Source = Settings.Default;
            this.Mode = BindingMode.TwoWay;
        }
    }
}
