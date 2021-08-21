// UI Variables
let root = document.documentElement;
let navbar_width = root.style.getPropertyValue('--navbar-width');
let navbar_fontsize = root.style.getPropertyValue('--navbar-icon-fontsize');

var navbar_pin = true;

// UI Class Setup
var uploadmde = new EasyMDE({ autoDownloadFontAwesome: false, spellChecker: false, element: document.getElementById("videoDescription") });
var lazyLoadInstance = new LazyLoad({
      elements_selector: ".lazy"
    });

function toggle_navbar_pin() {
    var elem = document.getElementById('navbar_pin_button');
    if (navbar_pin === true) {
        navbar_pin = false;
        setCookie('cookieNavbarState','closed', 365);
        elem.className = "far fa-dot-circle"
    } else {
        navbar_pin = true;
        setCookie('cookieNavbarState','open', 365);
        elem.className = "fas fa-dot-circle"
    }
}

function showNav(){
    root.style.setProperty('--navbar-width', navbar_width);
    root.style.setProperty('--navbar-icon-fontsize', navbar_fontsize);
}

function hideNav(){
    if (navbar_pin === false) {
        root.style.setProperty('--navbar-width', "66px");
    }
}

function showSpinner() {
    disableScrolling();
    loader = document.getElementById('loading-spinner');
    loader.style.display = 'flex';
    loader.hide();
    loader.fadeIn();
}

function hideSpinner() {
    enableScrolling();
    loader = document.getElementById('loading-spinner');
    loader.fadeOut();
}

function disableScrolling(){
    var x=window.scrollX;
    var y=window.scrollY;
    window.onscroll=function(){window.scrollTo(x, y);};
}

function enableScrolling(){
    window.onscroll=function(){};
}

function getRandomInt(min, max) {
    min = Math.ceil(min);
    max = Math.floor(max);
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function hideDiv(divID) {
    $('#' + divID).removeClass("show");
    $('#' + divID).addClass("hide");
}

function createNewBSAlert(message,category) {
    var randomID = getRandomInt(1,9000);
    $('#toastDiv').append('<div class="toast fade show" id="toast-' + randomID + '" role="alert" aria-live="assertive" aria-atomic="true" data-autohide="true" data-delay="30000" style="width:250px;">' +
          '<div class="toast-header"><strong class="mr-auto"><span class="toast-box"> </span><span style="margin-left:5px;">' + category + '</span> </strong>' +
          '<button type="button" class="ml-2 mb-1 close" onclick="hideDiv(\'toast-' + randomID + '\')" data-dismiss="toast" aria-label="Close"><span aria-hidden="true">&times;</span></button></div><div class="toast-body">' + message + '</div></div>')
}

function setCookie(name,value,days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days*24*60*60*1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=/; SameSite=Lax";
}

function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}

function eraseCookie(name) {
    document.cookie = name + '=; Max-Age=-99999999;';
}

// Triggers

// Enable Bootstrap Tooltips
$(function () {
  $('[data-toggle="tooltip"]').tooltip()
})

// Show Any Pending Toasts and Reset Upload Form
$(document).ready(function () {
  $('.toast').toast('show');
  document.getElementById("uploadform").reset();
});

// Thumbnail GIF Playback
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

// Save Navbar State
$(document).ready(function() {
    var cookieNavbarState = getCookie('cookieNavbarState');
    if (!(cookieNavbarState == null)) {
        if (cookieNavbarState === 'closed') {
            navbar_pin = false;
            var elem = document.getElementById('navbar_pin_button');
            elem.className = "far fa-dot-circle"
            hideNav();
        }
    }
});


