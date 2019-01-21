//http://xdsoft.net/jqplugins/datetimepicker/
Date.parseDate = function( input, format ){
  return moment(input,format).toDate();
};
Date.prototype.dateFormat = function( format ){
  return moment(this).format(format);
};

var $jq = jQuery.noConflict();


$jq(document).ready(function () {

    $jq('form.dirty-check').areYouSure();

    $jq('#datepicker_startdate').datetimepicker({
        format:'ddd DD MMM YYYY',
        formatTime:'HH:mm',
        timepicker: false,
        minDate: 0,
        closeOnDateSelect: true,
        scrollMonth: false,
        scrollTime: false,
        scrollInput: false,
    });

        $jq('#datepicker_enddate').datetimepicker({
        format:'ddd DD MMM YYYY',
        formatTime:'HH:mm',
        timepicker: false,
        minDate: 0,
        closeOnDateSelect: true,
        scrollMonth: false,
        scrollTime: false,
        scrollInput: false,
    });


    $jq('#select-all').click(function (event) {  //on click
        if (this.checked) { // check select status
            $jq('.select-checkbox').each(function () { //loop through each checkbox
                this.checked = true;  //select all checkboxes with class "select-checkbox"
            });
        } else {
            $jq('.select-checkbox').each(function () { //loop through each checkbox
                this.checked = false; //deselect all checkboxes with class "select-checkbox"
            });
        }
    });


});
