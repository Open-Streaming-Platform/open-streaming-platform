// Lazy Load Selector
var lazyLoadInstance = new LazyLoad({
  elements_selector: ".lazy"
});

// Toggles Theme Dark Mode On & Off
function toggleDarkMode() {
    var lightModeActive = getCookie('ospLightMode');
    lightModeActive = !lightModeActive;
    if (lightModeActive ===  true) {
        setLightMode();
    } else {
        setDarkMode();
    }
}

function setLightMode() {
    darkModeIcon = document.getElementById('darkModeIcon');
    darkModeIcon.className = 'textShadow bi bi-brightness-alt-high-fill bs-icon';
    document.documentElement.setAttribute("data-theme", 'light');
    setCookie('ospLightMode', true);
}

function setDarkMode() {
    darkModeIcon = document.getElementById('darkModeIcon');
    darkModeIcon.className = 'textShadow bi bi-brightness-alt-low bs-icon';
    document.documentElement.setAttribute("data-theme", 'dark');
    setCookie('ospLightMode', false);
}

// Opens the User Navigation Bar
function showUserNav() {
    try {
        document.getElementById("userMenuDropdown").classList.toggle('show');
    } catch {
        console.log("Error: Unable to Detect User Menu");
    }
}

function getRandomInt(min, max) {
    min = Math.ceil(min);
    max = Math.floor(max);
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function CopyDiv(divVal) {
    var copyText = document.getElementById(divVal);
    copyText.select();
    document.execCommand("copy");
}

function hideDiv(divID) {
  $('#' + divID).removeClass("show");
  $('#' + divID).addClass("hide");
}

function toggleDiv(divID) {
  var x = document.getElementById(divID);
  $(x).slideToggle();
}

function openModal(modalID) {
    $('#' + modalID).modal('show')
}

function map(arrayLike, fn) {
    var ret = [], i = -1, len = arrayLike.length;
    while (++i < len) ret[i] = fn(arrayLike[i]);
    return ret;
}

function getNodeIds(node) {
    if (node.nodeType === 1) return node.id;
    var txt = '';
    if (node = node.firstChild) do {
        txt += getText(node);
    } while (node = node.nextSibling);
    return txt;
}

// Creates a Bootstrap Alert
function createNewBSAlert(message,category) {
  var randomID = getRandomInt(1,9000);
  $('#toastDiv').append('<div class="toast fade show" id="toast-' + randomID + '" role="alert" aria-live="assertive" aria-atomic="true" data-autohide="true" data-delay="30000" style="width:250px;">' +
          '<div class="toast-header"><strong class="mr-auto"><span class="toast-box"> </span><span style="margin-left:5px;">' + category + '</span> </strong>' +
          '<div class="float-end"><button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="hideDiv(\'toast-' + randomID + '\')"></button></div></div><div class="toast-body">' + message + '</div></div>')
}

function clearSearch() {
    document.getElementById('systemSearchInput').value = '';
    document.getElementById('searchClearIcon').style.display = 'none';
    document.getElementById("searchResults").style.display = 'none';
    var ul = document.getElementById("searchResultsList-Channels");
    ul.innerHTML = '';
    var ul = document.getElementById("searchResultsList-Videos");
    ul.innerHTML = '';
    var ul = document.getElementById("searchResultsList-Clips");
    ul.innerHTML = '';
    var ul = document.getElementById("searchResultsList-Users");
    ul.innerHTML = '';
}

// Watches the Mouse Target Location Opens User Navigation Bar
$(document).click(function(event) {
    var target = event.target.parentNode;
    if (document.getElementById('userMenuDropdown') != null) {
        if (target.id != 'userMenuDropdown' && target.id != 'userDropDownButton' && document.getElementById('userMenuDropdown').classList.contains('show')) {
            document.getElementById("userMenuDropdown").classList.toggle('show');
        }
    }
});


// Event Handlers

// Stream Card png to gif Handler
$(document).ready(function()
  {
      $(".gif").hover(
          function()
          {
            var src = $(this).attr("src");
            $(this).attr("src", src.replace(/\.png$/i, ".gif"));
          },
          function()
          {
            var src = $(this).attr("src");
            $(this).attr("src", src.replace(/\.gif$/i, ".png"));
          });
});

// Stream Card png to gif Handler
$(document).ready(function()
  {
      $(".gifhover").hover(
          function()
          {
            var src = $(this).find('img').attr("src");
            $(this).find('img').attr("src", src.replace(/\.png$/i, ".gif"));
          },
          function()
          {
            var src = $(this).find('img').attr("src");
            $(this).find('img').attr("src", src.replace(/\.gif$/i, ".png"));
          });
});

// Handler for Setting Light/Dark Mode
document.addEventListener("DOMContentLoaded", function(event) {
  document.documentElement.setAttribute("data-theme", "dark");

  var lightModeActive = getCookie('ospLightMode');
  if (lightModeActive === null) {
    setCookie('ospLightMode', false);
    lightModeActive = 'false';
  }

  lightModeActive = (lightModeActive === 'true');

  if (lightModeActive === true) {
    setLightMode();
  } else if (lightModeActive === false) {
    setDarkMode()
  }
});

$("#systemSearchInput").on('change keydown paste input', function(){
    var searchInput = document.getElementById('systemSearchInput').value;
    var searchClearButton = document.getElementById('searchClearIcon')

    // Show and Hide Search Clear Button
    if (searchInput.length >= 1) {
        searchClearButton.style.display = 'initial';
    } else {
        searchClearButton.style.display = 'none';
    }

    resultsContainerDiv = document.getElementById("searchResults");

    if (searchInput.length >= 3) {
        resultsContainerDiv.style.display = 'none';

        document.getElementById("searchResults");
        var ul = document.getElementById("searchResultsList-Channels");
        ul.innerHTML = '';
        var ul = document.getElementById("searchResultsList-Videos");
        ul.innerHTML = '';
        var ul = document.getElementById("searchResultsList-Clips");
        ul.innerHTML = '';
        var ul = document.getElementById("searchResultsList-Users");
        ul.innerHTML = '';

        $.post('/apiv1/channel/search', {term: searchInput}, function (data, textStatus) {
            var channelResults = data['results'];
            var ulGroup = document.getElementById("searchResultsGroup-Channels");
            var groupShowMore = document.getElementById('searchResults-Channels-ShowMore');
            ul = document.getElementById("searchResultsList-Channels");
            ul.innerHTML = '';

            groupShowMore.style.display = 'none';
            groupShowMore.className = '';

            var chanlimit = 3;

            if (channelResults.length === 0) {
                ulGroup.style.display = 'none';
            } else {
                ulGroup.style.display = 'block';
                for (var ic = 0; ic < channelResults.length; ic++) {
                    if (ic < chanlimit) {
                        var channelImage = channelResults[ic][4];
                        if (channelImage === null) {
                            channelImage = '/static/img/video-placeholder.jpg';
                        } else {
                            channelImage = '/images/' + channelResults[ic][4];
                        }

                        var li = document.createElement("li");
                        li.classList = "list-group-item";
                        li.innerHTML = '<a href="/channel/' + channelResults[ic][0] + '/"><img class="small-channel-thumb boxShadow me-2" src="' + channelImage + '">' + channelResults[ic][1] + '</a>'
                        ul.appendChild(li);
                    }
                }
            }
            if (channelResults.length > chanlimit) {
                groupShowMore.style.display = 'block';
                groupShowMore.className = 'd-flex';
            }
        }, "json");

        $.post('/apiv1/stream/search', {term: searchInput}, function (data, textStatus) {
            var streamResults = data['results'];
            var ulGroup = document.getElementById("searchResultsGroup-Streams");
            var groupShowMore = document.getElementById('searchResults-Streams-ShowMore');
            ul = document.getElementById("searchResultsList-Streams");
            ul.innerHTML = '';

            groupShowMore.style.display = 'none';
            groupShowMore.className = '';

            var streamlimit = 5;

            if (streamResults.length === 0) {
                ulGroup.style.display = 'none';
            } else {
                ulGroup.style.display = 'block';
                for (var is = 0; is < streamResults.length; is++) {
                    if (is < streamlimit) {

                        var videoImage = streamResults[is][3];
                        if (videoImage === null) {
                            videoImage = '/static/img/video-locked.jpg';
                        } else {
                            if (data['adaptive'] === true) {
                                videoImage = '/stream-thumb-adapt/' + streamResults[is][2] + '.png';
                            } else {
                                videoImage = '/stream-thumb/' + streamResults[is][2] + '.png';
                            }
                        }
                        var li = document.createElement("li");
                        li.classList = "list-group-item";
                        li.innerHTML = '<a href="/play/' + streamResults[is][0] + '"><img class="small-thumb boxShadow me-2" src="' + videoImage + '">' + streamResults[is][1] + '</a>'
                        ul.appendChild(li);
                    }
                }
            }
            if (streamResults.length > streamlimit) {
                groupShowMore.style.display = 'block';
                groupShowMore.className = 'd-flex';
            }
        }, "json");

        $.post('/apiv1/video/search', {term: searchInput}, function (data, textStatus) {
            var videoResults = data['results'];
            var ulGroup = document.getElementById("searchResultsGroup-Videos");
            var groupShowMore = document.getElementById('searchResults-Videos-ShowMore');
            ul = document.getElementById("searchResultsList-Videos");
            ul.innerHTML = '';

            groupShowMore.style.display = 'none';
            groupShowMore.className = '';

            var vidlimit = 5;

            if (videoResults.length === 0) {
                ulGroup.style.display = 'none';
            } else {
                ulGroup.style.display = 'block';
                for (var iv = 0; iv < videoResults.length; iv++) {
                    if (iv < vidlimit) {

                        var videoImage = videoResults[iv][3];
                        if (videoImage === null) {
                            videoImage = '/static/img/video-locked.jpg';
                        } else {
                            videoImage = '/videos/' + videoResults[iv][3];
                        }
                        var li = document.createElement("li");
                        li.classList = "list-group-item";
                        li.innerHTML = '<a href="/play/' + videoResults[iv][0] + '"><img class="small-thumb boxShadow me-2" src="' + videoImage + '">' + videoResults[iv][1] + '</a>'
                        ul.appendChild(li);
                    }
                }
            }
            if (videoResults.length > vidlimit) {
                groupShowMore.style.display = 'block';
                groupShowMore.className = 'd-flex';
            }
        }, "json");

        $.post('/apiv1/clip/search', {term: searchInput}, function (data, textStatus) {
            var clipResults = data['results'];
            var ulGroup = document.getElementById("searchResultsGroup-Clips");
            var groupShowMore = document.getElementById('searchResults-Clips-ShowMore');
            ul = document.getElementById("searchResultsList-Clips");
            ul.innerHTML = '';

            groupShowMore.style.display = 'none';
            groupShowMore.className = '';

            var cliplimit = 5;

            if (clipResults.length === 0) {
                ulGroup.style.display = 'none';
            } else {
                ulGroup.style.display = 'block';
                for (var icl = 0; icl < clipResults.length; icl++) {
                    if (icl < cliplimit) {
                        var videoImage = clipResults[icl][3];
                        if (videoImage === null) {
                            videoImage = '/static/img/video-placeholder.jpg';
                        } else {
                            videoImage = '/videos/' + clipResults[icl][3];
                        }

                        var li = document.createElement("li");
                        li.classList = "list-group-item";
                        li.innerHTML = '<a href="/clip/' + clipResults[icl][0] + '"><img class="small-thumb boxShadow me-2" src="' + videoImage + '">' + clipResults[icl][1] + '</a>'
                        ul.appendChild(li);
                    }
                }

            }
            if (clipResults.length > cliplimit) {
                groupShowMore.style.display = 'block';
                groupShowMore.className = 'd-flex';
            }
        }, "json");

        $.post('/apiv1/user/search', {term: searchInput}, function (data, textStatus) {
            var userResults = data['results'];
            var ulGroup = document.getElementById("searchResultsGroup-Users");
            var groupShowMore = document.getElementById('searchResults-Clips-ShowMore');
            ul = document.getElementById("searchResultsList-Users");
            ul.innerHTML = '';

            groupShowMore.style.display = 'none';
            groupShowMore.className = '';

            var userlimit = 4;

            if (userResults.length === 0) {
                ulGroup.style.display = 'none';
            } else {
                ulGroup.style.display = 'block';
                for (var iu = 0; iu < userResults.length; iu++) {
                    if (iu < userlimit) {
                        var li = document.createElement("li");
                        li.classList = "list-group-item";
                        var userImage = userResults[iu][3];
                        if (userImage === null) {
                            userImage = '/static/img/user2.png';
                        } else {
                            userImage = '/images/' + userResults[iu][3];
                        }
                        li.innerHTML = '<a href="/profile/' + userResults[iu][1] + '"><img src="' + userImage + '" class="avatar-small boxShadow me-2">' + userResults[iu][1] + '</a>'
                        ul.appendChild(li);
                    }
                }
            }
            if (userResults.length > userlimit) {
                groupShowMore.style.display = 'block';
                groupShowMore.className = 'd-flex';
            }
        }, "json");

        resultsContainerDiv.style.display = 'block';

    } else {
        resultsContainerDiv.style.display = 'none';
        var ul = document.getElementById("searchResultsList-Channels");
        ul.innerHTML = '';
        var ul = document.getElementById("searchResultsList-Videos");
        ul.innerHTML = '';
        var ul = document.getElementById("searchResultsList-Clips");
        ul.innerHTML = '';
        var ul = document.getElementById("searchResultsList-Users");
        ul.innerHTML = '';
    }
});

