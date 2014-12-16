using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;

namespace MilitaryPlanner.ViewModels
{
    public class SymbolGroupViewModel
    {
        readonly IReadOnlyCollection<SymbolTreeViewModel> _firstGeneration;
        readonly SymbolTreeViewModel _rootSymbol;

        public SymbolGroupViewModel(SymbolViewModelWrapper rootSymbol)
        {
            _rootSymbol = new SymbolTreeViewModel(rootSymbol);

            _firstGeneration = new ReadOnlyCollection<SymbolTreeViewModel>(
                new SymbolTreeViewModel[]
                {
                    _rootSymbol
                });
        }

        public IReadOnlyCollection<SymbolTreeViewModel> FirstGeneration
        {
            get { return _firstGeneration; }
        }

    }
}
