
<!-- Custom JavaScript for the sidebar Menu Toggle on the timetable page -->
$(document).ready(function () {

    $('#id_date_of_birth').datetimepicker({
        format:'d-M-Y',
        formatDate:'d-M-Y',
        timepicker: false,
        defaultDate:'01-Jan-1990',
        closeOnDateSelect: true,
        scrollMonth: false,
        scrollTime: false,
        scrollInput: false
    });

});
