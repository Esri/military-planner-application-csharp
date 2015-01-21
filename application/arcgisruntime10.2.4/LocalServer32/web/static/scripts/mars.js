
Mars = {}

var i = location.pathname.indexOf("/arcgis");

Mars.root = location.pathname.substring(0, i);
Mars.rest = Mars.root + "/arcgis/rest/";
Mars.services = Mars.rest + "services/";
Mars.admin = Mars.rest + "admin/";

Mars.pageUrlWithTrailingForwardSlash = location.pathname;
if (location.pathname.charAt(location.pathname.length - 1) != '/') {
  Mars.pageUrlWithoutTrailingForwardSlash = Mars.pageUrlWithTrailingForwardSlash;
  Mars.pageUrlWithTrailingForwardSlash += '/';
}
else {
  Mars.pageUrlWithoutTrailingForwardSlash =
    Mars.pageUrlWithTrailingForwardSlash.substring(0, Mars.pageUrlWithTrailingForwardSlash.length - 2);
}

//extract service name and type from UR
Mars.end = location.pathname.substring(Mars.rest.length, location.pathname.length);
if (Mars.end == "")
  Mars.urlBits = []
else {
  Mars.urlBits = Mars.end.split('/');
  if (Mars.urlBits.length > 1)
    Mars.serviceName = Mars.urlBits[1];
  if (Mars.urlBits.length > 2)
    Mars.serviceType = Mars.urlBits[2];
}

Mars.setTitle = function (tplt) {
  Mars.pageTitle = $.tmpl(tplt, pageData).text();
  document.title = Mars.pageTitle;
};

function urlJoin(url, leaf) {
  if (url.charAt(url.length - 1) == '/')
    return url + leaf;
  return url + '/' + leaf;
}

function getBreadcrumbLinks() {
  Mars.links = []

  var url = Mars.rest;

  Mars.links.push({ label: "Home", url: url});

  var tokens = Mars.urlBits;

  // processing the service name bit of the URL
  var atServiceName = false;

  // gone past service name and type
  var inService = false;
  var serviceUrlDepth = 0;
  
  while (tokens.length > 0) {

    var token = tokens.shift();
    url = urlJoin(url, token);

    if (inService && Mars.serviceType == "GPServer") {
      
      if (serviceUrlDepth == 1) {
        Mars.GPTaskName = unescape(token);
        Mars.GPTaskResourceUrl = url; 
        Mars.links.push({ label: Mars.GPTaskName, url: url });
      }
      else if (serviceUrlDepth == 2) {
        if (token == "jobs") {
          Mars.GPJobId = tokens.shift();
          url = urlJoin(url, Mars.GPJobId);
          Mars.links.push({ label: Mars.GPJobId, url: url });
        }
        else if (token == "submitJob") {
          url = urlJoin(url, token);
          Mars.links.push({ label: token, url: url });
        }
        else if (token == "execute") {
          url = urlJoin(url, token);
          Mars.links.push({ label: token, url: url });
        }
      }
      else if (serviceUrlDepth == 3 && (token == "results" || token == "inputs")) {
        token = tokens.shift();
        url = urlJoin(url, token);
        Mars.links.push({ label: token, url: url });
      }
    }
    else if (atServiceName) {
      // service name doesnt appear in breadcrumb list - name and type get stuck together.
      Mars.serviceType = tokens.shift();
      url = urlJoin(url, Mars.serviceType);
      Mars.links.push({ label: token + " (" + Mars.serviceType + ")", url: url });
      Mars.serviceUrl = url;
      atServiceName = false;
      inService = true;
    }
    else
      Mars.links.push({ label: token, url: url });

    if (inService)
      serviceUrlDepth++;
    
    if (token == 'services')
      atServiceName = true;
  }
}

var headerHtml =
'<div class="header">ArcGISRuntime REST Services Directory</div>' +
'<div class="breadcrumbs">' +
'  <div class="breadcrumblinks">' +
'  </div>' +
'</div>' +
'<div id="jsonLink" class="jsonLink">' +
'<a href="?f=pjson">&raquo;JSON</a>' +
'</div>' +
'<div id="htmlLink" class="jsonLink">' +
'<a href="?f=html">&raquo;HTML</a>' +
'</div>' +
'<div style="margin-left: 42px;" id="jsondoc">'
'<pre class="jsondoc"></pre>' +
'</div>';

function insertHeader(jsonData) {
  getBreadcrumbLinks();
  $("#header").html(headerHtml);

  if (jsonData) {

    if (isObject(jsonData)) {
      // Load formatted json into hidden pre
      var jsonString = JSON.stringify(jsonData, null, '  ');
      $("#jsondoc").html("<pre class='jsondoc'>" + jsonString + "</pre><br/>");

      // Set up link click to show the pre
      $("#jsonLink").click(function (obj) {
        $("#jsonLink").hide();
        $("#htmlLink").show();
        $("#jsondoc").slideDown();
        $("#content").slideUp();
        return false;
      });

      // Set up link click to show the pre
      $("#htmlLink").click(function (obj) {
        $("#jsonLink").show();
        $("#htmlLink").hide();
        $("#jsondoc").slideUp();
        $("#content").slideDown();
        return false;
      });
    }
    else {
      // leave it as a link
    }

  }
  else {
    $("#jsonLink").hide();
  }

  $("#htmlLink").hide();
  $("#jsondoc").hide();

  createBreadcrumbTrail($(".breadcrumblinks"));
}

// Generate the breadcrumb trail of links.
function createBreadcrumbTrail(html) {

  var s = $("<span/>");
  html.prepend(s);

  var links = Mars.links;
  var last = links.pop();
  
  $.each(links, function (idx, link) {
    s.append("<a href='" + link.url + "'>" + unescape(link.label) + "</a> <span class='crumbchevron'>&raquo;</span> ");
  });

  s.append(unescape(last.label));
}

function IsArray(a) {
  return Object.prototype.toString.call(a) === '[object Array]';
}

function isObject(obj) {
  return typeof (obj) == "object";
}

function jsonValToHtml(v) {

  if (_.isString(v))
    return $("<span class='json_string'>" + v + "</span>");
  else if (_.isNumber(v))
    return $("<span class='json_number'>" + v + "</span>");
  else if (_.isBoolean(v))
    return $("<span class='json_boolean'>" + v + "</span>");
  else if (_.isNull(v))
    return $("<span class='json_null'>null</span>");
}

function arrayToHtml(obj, html, nesting) {

  if (obj.length == 0) {
    return;
  }

  $.each(obj, function (k, v) {

    var val = $("<div class='val'/>");

    if (IsArray(v)) {
      arrayToHtml(v, val, nesting + 1);
    }
    else if (isObject(v))
      objectToHtml(v, val, nesting + 1);
    else
      val.append(jsonValToHtml(v));

    html.append(val);
  });
}

// Debug write out prettyjson
function objectToHtml(obj, html, nesting) {

  var tbl = $("<table class='obj nest_" + nesting + " jsontable'>");

  var k;
  for (k in obj) {

    var v = obj[k];

      var row = $("<tr/>");
      tbl.append(row);

      var key = $("<td class='jsonkey'><span>" + k + "</span></td>");
      $(row).append(key);

      var val = $("<td class='val'/>");
      row.append(val);

      if (IsArray(v)) {
        key.append("[" + v.length + "]");
        arrayToHtml(v, val, nesting + 1);
      }
      else if (isObject(v))
        objectToHtml(v, val, nesting + 1);
      else
        val.append(jsonValToHtml(v));

  }

  html.append(tbl);

}

function myGetJson(url, succ, err) {
  $.ajax({
    cache: false,
    url: url,
    dataType: "json",
    success: function (dataJson, textStatus, jqXHR) {
      var data = dataJson;// $.parseJSON(dataJson);
      succ(data);
    },
    error: function (jqXHR, textStatus, errorThrown) {
      err(jqXHR, textStatus, errorThrown);
    }
  });
}

function BuildPage(title, includeJsonLink) {
  Mars.pageDataStringified = JSON.stringify(pageData, null, '  ');
  insertHeader(includeJsonLink);
  Mars.setTitle(title);
  $("#tcontent").tmpl(pageData).appendTo("#content");
}

function UpdateContent(includeJsonLink) {
  Mars.pageDataStringified = JSON.stringify(pageData, null, '  ');
  $("#jsondoc").html("<pre class='jsondoc'>" + Mars.pageDataStringified + "</pre><br/>");
  $("#tcontent").tmpl(pageData).appendTo("#content");
}