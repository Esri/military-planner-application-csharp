
function Clone(obj) {
  return jQuery.extend(true, {}, obj);
}

// Process a task metadata, adding inputs, outputs, isSynchronous properties.
function GetEnhancedTaskMetadata(taskMetadata) {
  var enhancedMetadata = {};
  enhancedMetadata.inputs = [];
  enhancedMetadata.outputs = [];
  enhancedMetadata.isSynchronous = taskMetadata.executionType == "esriExecutionTypeSynchronous";

  // For each parameter, tack on a stringified version of its defaultValue.
  $.each(taskMetadata.parameters, function (idx, p) {
    // Deep copy
    var parameter = Clone(p);

    parameter.defaultValueJSON = JSON.stringify(parameter.defaultValue, null, '  ');
    parameter.isRequired = parameter.parameterType == "esriGPParameterTypeRequired";

    if (parameter.direction == "esriGPParameterDirectionInput")
      enhancedMetadata.inputs.push(parameter);
    else
      enhancedMetadata.outputs.push(parameter);
  });
  return enhancedMetadata;
}

function BuildOverloadsPerParameter(taskMetadata) {
  
  // lookup table from parameter name to array of arrays of parameter types
  var methodParams = [];

  $.each(taskMetadata.inputs, function (idx, p) {

    var overloads = [];

    switch (p.dataType) {
      case "GPBoolean":
        methodParams.push([[{name: p.name, type: "bool"}]]);
        break;

      case "GPString":
        methodParams.push([[{name: p.name, type: "string"}]]);
        break;

      case "GPDouble":
        methodParams.push([[{name: p.name, type: "double"}]]);
        break;

      case "GPFeatureRecordSetLayer":
        methodParams.push([[{name: p.name, type: "FeatureSet"}], [{name: p.name, type: "Geometry"}]]);
        break;

      case "GPLinearUnit":
        methodParams.push([[{name: p.name + "Units", type: "esriUnits"}, {name: p.name + "Distance", type: "double"}]]);
        break;

      default:
        break;
    }
  });
  return methodParams;
}

function AddLastProperty(arr) {
  $.each(arr, function (idx, val) {
    val.last = idx == arr.length - 1;
  });
}

function BuildOverloadsList(taskMetadata) {
  var overloadsPerParameter = BuildOverloadsPerParameter(taskMetadata);
  return BuildOverloadsListInternal(overloadsPerParameter);
}

// Return an array of arrays of params (param == object with name and type)
function BuildOverloadsListInternal(overloadsPerParameter) {

  var overloads = [];

  if (overloadsPerParameter.length == 0)
    return overloads;

  // get overloads for first parameter.
  // This is an array of arrays of parameter names/types.
  var firstParameter = overloadsPerParameter.shift();

  var subsequentParameters = BuildOverloadsListInternal(overloadsPerParameter);

  $.each(firstParameter, function (idx, params) {

    var paramList = [];

    paramList.push(params);

    if (subsequentParameters.length > 0) {
      // iterate over array of arrays of subsequent params, prepending with each possible overload for this param.
      $.each(subsequentParameters, function (idx, parms) {

        $.each(parms, function (idx, parm) {
          var pl = paramList.slice(0);
          pl.push(parm);
          pl = _.flatten(pl);
          AddLastProperty(pl);
          overloads.push(pl);
        });
      });
    }
    else {
      AddLastProperty(paramList);
      overloads.push(paramList);
    }
  });

  return overloads;
}