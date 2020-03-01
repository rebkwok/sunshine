/*
  This file must be imported immediately-before the close-</body> tag,
  and after JQuery and Underscore.js are imported.
*/
/**
  The number of milliseconds to ignore clicks on the *same* like
  button, after a button *that was not ignored* was clicked. Used by
  `$(document).ready()`.
  Equal to <code>500</code>.
 */
const MILLS_TO_IGNORE = 500;

/**
   Executes a toggle click. Triggered by clicks on the regular student yes/no links.
 */

const processFailure = function(
   result, status, jqXHR)  {
  //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "'");
  if (result.responseText) {
    vNotify.error({text:result.responseText,title:'Error',position: 'bottomRight'});
  }
   };

const processToggleAttended = function()  {

   //In this scope, "this" is the button just clicked on.
   //The "this" in processResult is *not* the button just clicked
   //on.
   const $button_just_clicked_on = $(this);

   //The value of the "data-booking_id" attribute.
   const booking_id = $button_just_clicked_on.data('booking_id');
   const attendance = $button_just_clicked_on.data('attendance');

   const processResult = function(
       result, status, jqXHR)  {
      //console.log("sf result='" + result.attended + "', status='" + status + "', jqXHR='" + jqXHR + "', booking_id='" + booking_id + "'");

       if(result.attended === true) {
           $('#booking-attended-' + booking_id).addClass('btn-success').removeClass('btn-light');
           $('#booking-noshow-' + booking_id).addClass('btn-light').removeClass('btn-danger');
           $('#booking-row-' + booking_id).removeClass('expired');
           $('#booking-status-' + booking_id).html('OPEN');
       } else {
           $('#booking-row-' + booking_id).addClass('expired');
           $('#booking-attended-' + booking_id).addClass('btn-light').removeClass('btn-success');
           $('#booking-noshow-' + booking_id).addClass('btn-danger').removeClass('btn-light');
       }
       if(result.user_has_outstanding_fees === true) {
           var fee_url = '/instructor-admin/fees/' + result.user_id + '/';
           $('#fees-' + booking_id).html("<span class='fees-due'><a href='" + fee_url + "'>£" + result.outstanding_fees_total + " <i class='far fa-arrow-alt-circle-right'></a></span>");
       } else {
            $('#fees-' + booking_id).html("-");
       }
       $('#spaces-left').text(result.spaces_left);

       if (result.alert_msg) {
        vNotify.error({text:result.alert_msg, title:'Error', position: 'bottomRight'});
      }

   };

   var csrftoken = Cookies.get('csrftoken');

   $.ajax(
       {
          url: '/instructor-admin/registers/' + booking_id + '/toggle_attended/' ,
          data: {'attendance': attendance},
          headers: {'X-CSRFToken': csrftoken},
          type: "POST",
          dataType: 'json',
          success: processResult,
          error: processFailure
       }
    );
};


/**
   The Ajax "main" function. Attaches the listeners to the elements on
   page load, each of which only take effect every
   <link to MILLS_TO_IGNORE> seconds.

   This protection is only against a single user pressing buttons as fast
   as they can. This is in no way a protection against a real DDOS attack,
   of which almost 100% bypass the client (browser) (they instead
   directly attack the server). Hence client-side protection is pointless.

   - http://stackoverflow.com/questions/28309850/how-much-prevention-of-rapid-fire-form-submissions-should-be-on-the-client-side

   The protection is implemented via Underscore.js' debounce function:
  - http://underscorejs.org/#debounce

   Using this only requires importing underscore-min.js. underscore-min.map
   is not needed.
 */
$(document).ready(function()  {
  /*
    There are many buttons having the class

      td_regular_student_button

    This attaches a listener to *every one*. Calling this again
    would attach a *second* listener to every button, meaning each
    click would be processed twice.
   */
  $('.btn-attended').click(_.debounce(processToggleAttended, MILLS_TO_IGNORE, true));
  $('.btn-noshow').click(_.debounce(processToggleAttended, MILLS_TO_IGNORE, true));
});