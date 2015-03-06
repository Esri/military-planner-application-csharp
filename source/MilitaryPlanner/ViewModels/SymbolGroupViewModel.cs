using System.Collections.Generic;
using System.Collections.ObjectModel;

namespace MilitaryPlanner.ViewModels
{
    public class SymbolGroupViewModel
    {
        readonly IReadOnlyCollection<SymbolTreeViewModel> _firstGeneration;

        public SymbolGroupViewModel(SymbolViewModelWrapper rootSymbol)
        {
            var rootSymbol1 = new SymbolTreeViewModel(rootSymbol);

            _firstGeneration = new ReadOnlyCollection<SymbolTreeViewModel>(
                new[]
                {
                    rootSymbol1
                });
        }

        public IReadOnlyCollection<SymbolTreeViewModel> FirstGeneration
        {
            get { return _firstGeneration; }
        }

    }
}
