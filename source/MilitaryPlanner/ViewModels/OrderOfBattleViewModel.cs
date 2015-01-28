using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Collections.ObjectModel;
//using ESRI.ArcGIS.Client;
//using ESRI.ArcGIS.Client.AdvancedSymbology;
using MilitaryPlanner.Helpers;
using System.Windows.Controls;
using System.Windows;
using Esri.ArcGISRuntime.Symbology.Specialized;

namespace MilitaryPlanner.ViewModels
{
    public class OrderOfBattleViewModel : BaseViewModel
    {
        public static SymbolDictionary _symbolDictionary;

        // Public members for data binding
        public ObservableCollection<SymbolViewModel> Symbols { get; private set; }
        public string SearchString { get; private set; }

        // commands
        public RelayCommand SearchCommand { get; set; }
        public RelayCommand SymbolChangedCommand { get; set; }
        public RelayCommand SymbolDragCommand { get; set; }

        private int _imageSize;

        // Currently selected symbol 
        SymbolViewModel _SelectedSymbol = null;
        public SymbolViewModel SelectedSymbol
        {
            get
            {
                return _SelectedSymbol;
            }

            set
            {
                _SelectedSymbol = value;

                RaisePropertyChanged(() => SelectedSymbol);

                Mediator.NotifyColleagues(Constants.ACTION_SELECTED_SYMBOL_CHANGED, value);
            }
        }

        public SymbolGroupViewModel GroupSymbol
        {
            get
            {
                return _groupSymbol;
            }
        }
        readonly SymbolGroupViewModel _groupSymbol;

        public OrderOfBattleViewModel()
        {
            Mediator.Register(Constants.ACTION_CANCEL, DoActionCancel);
            Mediator.Register(Constants.ACTION_ITEM_WITH_GUID_REMOVED, DoActionItemWithGuidRemoved);
            Mediator.Register(Constants.ACTION_ITEM_WITH_GUID_ADDED, DoActionItemWithGuidAdded);

            // Check the ArcGIS Runtime is initialized
            if (!Esri.ArcGISRuntime.ArcGISRuntimeEnvironment.IsInitialized)
            {
                Esri.ArcGISRuntime.ArcGISRuntimeEnvironment.Initialize();
            }

            // hook the commands
            SearchCommand = new RelayCommand(OnSearch);
            SymbolChangedCommand = new RelayCommand(OnSymbolChanged);

            // Create a new SymbolDictionary instance 
            _symbolDictionary = new SymbolDictionary(SymbolDictionaryType.Mil2525c);

            // Collection of view models for the displayed list of symbols
            Symbols = new ObservableCollection<SymbolViewModel>();

            // Collection of strings to hold the selected symbol dictionary keywords
            //SelectedKeywords = new ObservableCollection<string>();
            //_keywords = _symbolDictionary.Keywords;

            // Set the DataContext for binding
            //DataContext = this;

            //InitializeComponent();

            // Set the image size
            _imageSize = 96;

            // org tree view
            _groupSymbol = new SymbolGroupViewModel(SymbolLoader.LoadSymbolWrapper());

            ExpandGroupSymbol(_groupSymbol);
        }

        private void SetAllNodesToDraggable()
        {
            foreach (var sym in _groupSymbol.FirstGeneration)
            {
                SetAllLeavesToDraggable(sym);
            }
        }

        private void SetAllLeavesToDraggable(SymbolTreeViewModel stvm)
        {
            stvm.HasBeenDragged = false;

            if (stvm.Children != null && stvm.Children.Count > 0)
            {
                foreach (var stvm2 in stvm.Children)
                {
                    SetAllLeavesToDraggable(stvm2);
                }
            }
        }

        /// <summary>
        /// Method that handles the addition of a symbol to the map view
        /// Sets the property that controls the objects dragability
        /// </summary>
        /// <param name="obj"></param>
        private void DoActionItemWithGuidAdded(object obj)
        {
            var guid = obj as string;

            // object here is a guid
            if (guid == null)
            {
                return;
            }

            foreach (var sym in _groupSymbol.FirstGeneration)
            {
                var temp = FindChildWithGuid(sym, guid);

                if (temp != null)
                {
                    temp.HasBeenDragged = true;
                }
            }
        }

        /// <summary>
        /// Method handles the removal of a symbol from the entire mission
        /// Reset HasBeenDragged property in OOB Tree so that it can be dragged/dropped again
        /// </summary>
        /// <param name="obj"></param>
        private void DoActionItemWithGuidRemoved(object obj)
        {
            var guid = obj as string;

            // object here is a guid
            if (guid == null)
            {
                return;
            }

            foreach (var sym in _groupSymbol.FirstGeneration)
            {
                var temp = FindChildWithGuid(sym, guid);

                if (temp != null)
                {
                    temp.HasBeenDragged = false;
                }
            }
        }

        /// <summary>
        /// Method finds the first child node with the given GUID
        /// </summary>
        /// <param name="stvm"></param>
        /// <param name="guid"></param>
        /// <returns>Tree Symbol object with the given GUID</returns>
        private SymbolTreeViewModel FindChildWithGuid(SymbolTreeViewModel stvm, string guid)
        {
            if (stvm == null)
            {
                return null;
            }

            if (stvm.GUID.CompareTo(guid) == 0)
            {
                return stvm;
            }
            else
            {
                foreach (var stvm2 in stvm.Children)
                {
                    var result = FindChildWithGuid(stvm2, guid);

                    if(result != null)
                    {
                        return result;
                    }
                }
            }

            return null;
        }

        private void ExpandGroupSymbol(SymbolGroupViewModel _groupSymbol)
        {
            foreach (var svm in _groupSymbol.FirstGeneration)
            {
                ExpandSymbolTreeViewModelRecursive(svm);
            }
        }

        private void ExpandSymbolTreeViewModelRecursive(SymbolTreeViewModel svm)
        {
            svm.IsExpanded = true;

            foreach (var item in svm.Children)
            {
                ExpandSymbolTreeViewModelRecursive(item);
            }
        }

        private void DoActionCancel(object obj)
        {
            
        }

        /// <summary>
        /// Handler for when a selection of a symbol has changed
        /// </summary>
        /// <param name="param"></param>
        private void OnSymbolChanged(object param)
        {
            var e = param as SelectionChangedEventArgs;
            if (e == null)
            {
                return;
            }
            if (e.AddedItems.Count != 1)
                return;
            if (e.AddedItems[0].GetType() != typeof(SymbolViewModel))
                return;

            SelectedSymbol = e.AddedItems[0] as SymbolViewModel;
        }

        private void OnSearch(object parameter)
        {
            Dictionary<string, string> filters = new Dictionary<string, string>();

            //if (cmbStyleFile.SelectedValue != null && !cmbStyleFile.SelectedValue.Equals(""))
            //    filters["StyleFile"] = cmbStyleFile.SelectedValue.ToString();

            //if (cmbCategory.SelectedValue != null && !cmbCategory.SelectedValue.Equals(""))
            //    filters["Category"] = cmbCategory.SelectedValue.ToString();

            //foreach (var item in cmbGeometryType.SelectedItems)
            //{
            //    if (item.ToString() != null && !item.ToString().Equals(""))
            //        filters["GeometryType"] = item.ToString();
            //}

            // Clear the current Symbols collection
            Symbols.Clear();

            // Perform the search applying any selected keywords and filters 
            IEnumerable<SymbolProperties> symbols = _symbolDictionary.FindSymbols(filters);

            if (!String.IsNullOrWhiteSpace(SearchString))
            {
                foreach (var ss in SearchString.Split(new char[] {';',','}))
                {
                    if (!String.IsNullOrWhiteSpace(ss))
                    {
                        symbols = symbols.Where(s => s.Name.ToLower().Contains(ss.ToLower().Trim()) || s.Keywords.Where(kw => kw.ToLower().Contains(ss.ToLower().Trim())).Count() > 0);
                    }
                }
            }

            var allSymbols = symbols.ToList();

            // Update the list of applicable keywords (excluding any keywords that are not on the current result set)
            //if (SelectedKeywords == null || SelectedKeywords.Count == 0)
            //{
            //    _keywords = _symbolDictionary.Keywords.Where(k => !IsSymbolId(k)).ToList();
            //}
            //else
            //{
            //    IEnumerable<string> allSymbolKeywords = allSymbols.SelectMany(s => s.Keywords);
            //    _keywords = allSymbolKeywords.Distinct().Except(SelectedKeywords).Where(k => !IsSymbolId(k)).ToList();
            //}
            //FirePropertyChanged("Keywords");

            // Add symbols to UI collection
            foreach (var s in from symbol in allSymbols select new SymbolViewModel(symbol, _imageSize))
            {
                Symbols.Add(s);
            }
        }
    }
}
