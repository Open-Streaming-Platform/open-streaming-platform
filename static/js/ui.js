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
    darkModeIcon.className = 'textShadow bi bi-brightness-alt-high-fill';
    document.documentElement.setAttribute("data-theme", 'light');
    setCookie('ospLightMode', true);
}

function setDarkMode() {
    darkModeIcon = document.getElementById('darkModeIcon');
    darkModeIcon.className = 'textShadow bi bi-brightness-alt-low';
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

// Watches the Mouse Target Location Opens User Navigation Bar
$(document).click(function(event) {
    var target = event.target.parentNode;
    if (document.getElementById('userMenuDropdown') != null) {
        if (target.id != 'userMenuDropdown' && target.id != 'userDropDownButton' && document.getElementById('userMenuDropdown').classList.contains('show')) {
            document.getElementById("userMenuDropdown").classList.toggle('show');
        }
    }
});

// Initialize all select options with Select2
$(document).ready(function() {
    $('.select2').select2();
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
