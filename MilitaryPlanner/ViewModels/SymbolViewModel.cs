using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Windows.Media;
//using ESRI.ArcGIS.Client.AdvancedSymbology;
using Esri.ArcGISRuntime.Symbology.Specialized;

namespace MilitaryPlanner.ViewModels
{
    // Symbol view model. Primary role is to expose an image property to be used in data binding.
    public class SymbolViewModel : BaseViewModel
    {
        public string Category
        {
            get { return _model.Values["Category"].ToString(); }
        }

        public string SymbolID
        {
            get { return _model.Values["SymbolID"].ToString(); }
        }

        //public string StyleFile
        //{
        //    get { return _model.Values["StyleFile"].ToString(); }
        //}

        public SymbolProperties Model
        {
            get { return _model; }
        }

        private ImageSource _image;

        private int _imageSize;

        private SymbolProperties _model;

        public SymbolViewModel(SymbolProperties model, int imageSize)
        {
            _model = model;
            _imageSize = imageSize;
        }

        public string Name { get { return _model.Name; } }

        public int ImageSize { get { return _imageSize; } }

        public string Keywords { get { return string.Join(", ", _model.Keywords); } }

        public ImageSource Thumbnail
        {
            get
            {
                if (_image == null)
                {
                    try
                    {
                        _image = _model.GetImage(_imageSize, _imageSize);
                    }
                    catch (Exception)
                    {
                        return null;
                    }
                }
                return _image;
            }
        }

        public void InvalidateImage(int imageSize)
        {
            _imageSize = imageSize;
            if (_image != null)
            {
                _image = null;
                RaisePropertyChanged(() => Thumbnail);
            }

            RaisePropertyChanged(() => ImageSize);
        }
    }
}
