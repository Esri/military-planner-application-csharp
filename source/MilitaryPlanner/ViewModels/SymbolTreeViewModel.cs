// Copyright 2015 Esri 
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Windows.Media;
using System.Xml;
using System.Xml.Serialization;
using Esri.ArcGISRuntime.Symbology.Specialized;
using MilitaryPlanner.Behavior;

namespace MilitaryPlanner.ViewModels
{
    public static class SymbolLoader
    {
        public static SymbolDictionary SymbolDictionary;

        public static ObservableCollection<SymbolViewModel> Symbols { get; private set; }
        private const int _imageSize = 48;

        public static SymbolViewModelWrapper LoadSymbolWrapper()
        {
            // Create a new SymbolDictionary instance 
            SymbolDictionary = new SymbolDictionary(SymbolDictionaryType.Mil2525c);

            var swRoot = new SymbolViewModelWrapper();
            swRoot = swRoot.Load(@".\data\oob\oobexample.xml");

            return swRoot;
        }

        public static SymbolViewModel Search(string searchString)
        {
            Dictionary<string, string> filters = new Dictionary<string, string>();

            // Perform the search applying any selected keywords and filters 
            IEnumerable<SymbolProperties> symbols = SymbolDictionary.FindSymbols(filters);

            if (!String.IsNullOrWhiteSpace(searchString))
            {
                foreach (var ss in searchString.Split(';', ','))
                {
                    if (!String.IsNullOrWhiteSpace(ss))
                    {
                        symbols = symbols.Where(s => s.Name.ToLower().Contains(ss.ToLower().Trim()) || s.Keywords.Count(kw => kw.ToLower().Contains(ss.ToLower().Trim())) > 0);
                    }
                }
            }

            var allSymbols = symbols.ToList();

            // Add symbols to UI collection
            return (from symbol in allSymbols select new SymbolViewModel(symbol, _imageSize)).FirstOrDefault();
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
            XmlSerializer x = new XmlSerializer(GetType());
            FileStream fs = new FileStream(filename, FileMode.Create);
            x.Serialize(fs, this);
            fs.Close();
        }

        internal SymbolViewModelWrapper Load(string filename)
        {
            XmlSerializer x = new XmlSerializer(GetType());
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
        bool _hasBeenDragged;
        readonly string _guid;

        public SymbolTreeViewModel(SymbolViewModelWrapper symbolWrapper)
            : this(symbolWrapper, null)
        {
        }

        private SymbolTreeViewModel(SymbolViewModelWrapper symbolWrapper, SymbolTreeViewModel parent)
        {
            _guid = Guid.NewGuid().ToString("D");
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
                return true;
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
            if (String.IsNullOrEmpty(text) || String.IsNullOrEmpty(Name))
                return false;

            return Name.IndexOf(text, StringComparison.InvariantCultureIgnoreCase) > -1;
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
                if (stvm != null) stvm.HasBeenDragged = true;
            }
        }
    }
}
