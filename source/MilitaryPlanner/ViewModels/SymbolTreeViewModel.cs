using Esri.ArcGISRuntime.Symbology.Specialized;
using MilitaryPlanner.DragDrop.UI.Behavior;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Media;
using System.Xml;
using System.Xml.Serialization;

namespace MilitaryPlanner.ViewModels
{
    public static class SymbolLoader
    {
        public static SymbolDictionary _symbolDictionary;

        public static ObservableCollection<SymbolViewModel> Symbols { get; private set; }
        private static int _imageSize = 48;

        public static SymbolViewModelWrapper LoadSymbolWrapper()
        {
            // Create a new SymbolDictionary instance 
            _symbolDictionary = new SymbolDictionary(SymbolDictionaryType.Mil2525c);

            var swRoot = new SymbolViewModelWrapper();
            swRoot = swRoot.Load(@".\data\oob\oobexample.xml");

            return swRoot;
        }

        public static SymbolViewModel Search(string SearchString)
        {
            Dictionary<string, string> filters = new Dictionary<string, string>();

            // Perform the search applying any selected keywords and filters 
            IEnumerable<SymbolProperties> symbols = _symbolDictionary.FindSymbols(filters);

            if (!String.IsNullOrWhiteSpace(SearchString))
            {
                foreach (var ss in SearchString.Split(new char[] { ';', ',' }))
                {
                    if (!String.IsNullOrWhiteSpace(ss))
                    {
                        symbols = symbols.Where(s => s.Name.ToLower().Contains(ss.ToLower().Trim()) || s.Keywords.Where(kw => kw.ToLower().Contains(ss.ToLower().Trim())).Count() > 0);
                    }
                }
            }

            var allSymbols = symbols.ToList();

            // Add symbols to UI collection
            foreach (var s in from symbol in allSymbols select new SymbolViewModel(symbol, _imageSize))
            {
                //Symbols.Add(s);
                return s;
            }

            return null;
        }
    }

    [Serializable]
    public class SymbolViewModelWrapper
    {
        List<SymbolViewModelWrapper> _children = new List<SymbolViewModelWrapper>();
        string _sic;

        [XmlElement]
        public List<SymbolViewModelWrapper> Children
        {
            get { return _children; }
            set { _children = value; }
        }

        [XmlIgnore]
        public SymbolViewModel SVM { get; set; }

        [XmlElement]
        public string SIC { get { return _sic; } set { _sic = value; } }

        internal void Save(string filename)
        {
            XmlSerializer x = new XmlSerializer(this.GetType());
            FileStream fs = new FileStream(filename, FileMode.Create);
            x.Serialize(fs, this);
            fs.Close();
        }

        internal SymbolViewModelWrapper Load(string filename)
        {
            XmlSerializer x = new XmlSerializer(this.GetType());
            //XmlWriter writer = new XmlTextWriter(filename, System.Text.Encoding.UTF8);
            FileStream fs = new FileStream(filename, FileMode.Open);
            XmlReader reader = XmlReader.Create(fs);
            var temp = x.Deserialize(reader) as SymbolViewModelWrapper;

            InitializeWrapper(temp);

            return temp;
        }

        private void InitializeWrapper(SymbolViewModelWrapper temp)
        {
            if (temp.Children == null || temp.Children.Count <= 0)
            {
                return;
            }

            foreach (var w in temp.Children)
            {
                InitializeWrapper(w);

                w.SVM = SymbolLoader.Search(w.SIC);
            }

            temp.SVM = SymbolLoader.Search(temp.SIC);
        }
    }

    public class SymbolTreeViewModel : BaseViewModel, IDragable
    {
        readonly ReadOnlyCollection<SymbolTreeViewModel> _children;
        readonly SymbolTreeViewModel _parent;
        readonly SymbolViewModelWrapper _symbolWrapper;

        bool _isExpanded;
        bool _isSelected;
        //bool _isDragable = true;
        bool _hasBeenDragged = false;
        double _opacity = 1.0;
        string _guid;

        public SymbolTreeViewModel(SymbolViewModelWrapper symbolWrapper)
            : this(symbolWrapper, null)
        {
        }

        private SymbolTreeViewModel(SymbolViewModelWrapper symbolWrapper, SymbolTreeViewModel parent)
        {
            _guid = System.Guid.NewGuid().ToString("D");
            _symbolWrapper = symbolWrapper;
            _parent = parent;

            _children = new ReadOnlyCollection<SymbolTreeViewModel>(
                (from child in _symbolWrapper.Children
                 select new SymbolTreeViewModel(child, this))
                 .ToList<SymbolTreeViewModel>());
        }

        #region SymbolVM Properties

        public ReadOnlyCollection<SymbolTreeViewModel> Children
        {
            get { return _children; }
        }

        public string Name
        {
            get { return _symbolWrapper.SVM.Name; }
        }

        public ImageSource Thumbnail
        {
            get { return _symbolWrapper.SVM.Thumbnail; }
        }

        public int ImageSize
        {
            get { return _symbolWrapper.SVM.ImageSize; }
        }

        public SymbolViewModel ItemSVM
        {
            get { return _symbolWrapper.SVM; }
        }

        #endregion

        #region IsExpanded

        /// <summary>
        /// Gets/sets whether the TreeViewItem 
        /// associated with this object is expanded.
        /// </summary>
        public bool IsExpanded
        {
            get { return _isExpanded; }
            set
            {
                if (value != _isExpanded)
                {
                    _isExpanded = value;
                    RaisePropertyChanged(() => IsExpanded);
                }

                // Expand all the way up to the root.
                if (_isExpanded && _parent != null)
                    _parent.IsExpanded = true;
            }
        }

        #endregion // IsExpanded

        #region IsSelected

        /// <summary>
        /// Gets/sets whether the TreeViewItem 
        /// associated with this object is selected.
        /// </summary>
        public bool IsSelected
        {
            get { return _isSelected; }
            set
            {
                if (value != _isSelected)
                {
                    _isSelected = value;
                    RaisePropertyChanged(() => IsSelected);
                }
            }
        }

        #endregion // IsSelected

        public string GUID
        {
            get
            {
                return _guid;
            }
        }

        public bool HasBeenDragged
        {
            get
            {
                return _hasBeenDragged;
            }

            set
            {
                if (value != _hasBeenDragged)
                {
                    _hasBeenDragged = value;
                    RaisePropertyChanged(() => HasBeenDragged);
                }
            }
        }

        public bool IsDragable
        {
            get 
            {
             //   return _isDragable;
                if (_children != null && _children.Count > 0)
                {
                    return false;
                }
                else
                {
                    return true;
                }
            }

            //set
            //{
            //    if (value != _isDragable)
            //    {
            //        _isDragable = value;
            //        RaisePropertyChanged(() => IsDragable);
            //    }
            //}
        }

        #region NameContainsText

        public bool NameContainsText(string text)
        {
            if (String.IsNullOrEmpty(text) || String.IsNullOrEmpty(this.Name))
                return false;

            return this.Name.IndexOf(text, StringComparison.InvariantCultureIgnoreCase) > -1;
        }

        #endregion // NameContainsText

        #region Parent

        public SymbolTreeViewModel Parent
        {
            get { return _parent; }
        }

        #endregion // Parent

        public Type DataType
        {
            get { return typeof(SymbolTreeViewModel); }
        }

        public void Remove(object i)
        {
            // set as disabled?
            // We will need to disable the drag on this model until another slide is created or is deleted from current slide
            var stvm = i as SymbolTreeViewModel;

            if (i != null)
            {
                //TODO need to use msg.ID or something to keep track of item, for delete, add, etc
                //stvm.IsDragable = false;
                stvm.HasBeenDragged = true;
            }
        }
    }
}
