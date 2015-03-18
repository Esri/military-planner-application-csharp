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
using System.Windows.Media;
using Esri.ArcGISRuntime.Symbology.Specialized;

namespace MilitaryPlanner.ViewModels
{
    // Symbol view model. Primary role is to expose an image property to be used in data binding.
    public class SymbolViewModel : BaseViewModel
    {
        public string Category
        {
            get { return _model.Values["Category"]; }
        }

        public string SymbolID
        {
            get { return _model.Values["SymbolID"]; }
        }

        public SymbolProperties Model
        {
            get { return _model; }
        }

        private ImageSource _image;

        private int _imageSize;

        private readonly SymbolProperties _model;

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
