window.onload = function() {
    var elements =  document.getElementsByTagName('form');
    if (elements.length > 0) {
        elements[0].classList.add("mock-bs-form");
    }
    
    var buttons = document.getElementsByTagName('button');
    if (buttons.length > 0) {
        buttons[0].classList = "btn btn-green tra-green-hover btn-sm"
    }
 }