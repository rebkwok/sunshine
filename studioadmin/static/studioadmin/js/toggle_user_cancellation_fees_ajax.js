/*
  This file must be imported immediately-before the close-</body> tag,
  and after JQuery and Underscore.js are imported.
*/
var $jq = jQuery.noConflict();

/**
  The number of milliseconds to ignore clicks on the *same* like
  button, after a button *that was not ignored* was clicked. Used by
  `$jq(document).ready()`.
  Equal to <code>500</code>.
 */
var MILLS_TO_IGNORE = 500;


/**
   Executes a toggle click. Triggered by clicks on the waiting list button.
 */
var toggleFeePaid = function()  {

    //In this scope, "this" is the button just clicked on.
    //The "this" in processResult is *not* the button just clicked
    //on.
    var $button_just_clicked_on = $jq(this);

    //The value of the "data-booking_id" attribute.
    var booking_id = $button_just_clicked_on.data('booking_id');
    var user_id = $button_just_clicked_on.data('user_id');

    var updateFeeTotal = function(result, status, jqXHR)  {
        $jq('#total-fees').text(result.total_fees);
    };

    var updatePaymentButton = function(result, status, jqXHR)  {
      //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "', user_id='" + user_id + "'");
      //update the booking fee payment status
        $jq('#fee_' + booking_id).html(result);

        // update the total
        $jq.ajax(
            {
                url: '/instructor-admin/fees/ajax-user-total-fees/' + user_id + '/',
                dataType: 'json',
                headers: {'X-CSRFToken': csrftoken},
                type: "POST",
                success: updateFeeTotal
                //Should also have a "fail" call as well.
            }
        );
    };

    var csrftoken = Cookies.get('csrftoken');

    $jq.ajax(
        {
          url: '/instructor-admin/fees/ajax-toggle-cancellation-fee-payment/' + booking_id + '/',
          headers: {'X-CSRFToken': csrftoken},
          type: "POST",
          dataType: 'html',
          success: updatePaymentButton
          //Should also have a "fail" call as well.
        }
    );
};


const processFailure = function(
   result, status, jqXHR)  {
  //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "'");
  if (result.responseText) {
    vNotify.error({text:result.responseText, title:'Error', position: 'bottomRight'});
  }
   };


var toggleRemoveFee = function()  {

    //In this scope, "this" is the button just clicked on.
    //The "this" in processResult is *not* the button just clicked
    //on.
    var $button_just_clicked_on = $jq(this);

    //The value of the "data-event_id" attribute.
    var booking_id = $button_just_clicked_on.data('booking_id');

    var updatePaymentButton = function(result, status, jqXHR)  {
      //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "', user_id='" + user_id + "'");
      //update the booking fee payment status
        $jq('#fee_' + booking_id).html(result);
    };

    var csrftoken = Cookies.get('csrftoken');

    var processRemoveFeeResult = function(result, status, jqXHR)  {
        // update the button
        if (result.fee_status === "removed") {
            $jq('#remove_fee_btn_' + booking_id).text('Add fee');
        }
        else {
            $jq('#remove_fee_btn_' + booking_id).text('Remove fee');
        }
        // update the total
        $jq('#total-fees').text(result.total_fees);

        // update the booking fee payment status
        $jq.ajax(
            {
                url: '/instructor-admin/fees/ajax-update-cancellation-fee-payment-status/' + booking_id + '/',
                dataType: 'html',
                headers: {'X-CSRFToken': csrftoken},
                type: "POST",
                success: updatePaymentButton
                //Should also have a "fail" call as well.
            }
        );
    };

   $jq.ajax(
       {
           url: '/instructor-admin/fees/ajax-toggle-remove-cancellation-fee/' + booking_id + '/',
           headers: {'X-CSRFToken': csrftoken},
           type: "POST",
           dataType: 'json',
           success: processRemoveFeeResult,
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
$jq(document).ready(function()  {
  /*
    There are many buttons having the class

      td_ajax_fee_btn

    This attaches a listener to *every one*. Calling this again
    would attach a *second* listener to every button, meaning each
    click would be processed twice.
   */
  $jq('.td_ajax_fee_btn').click(_.debounce(toggleFeePaid,
      MILLS_TO_IGNORE, true));
  $jq('.td_ajax_remove_fee_btn').click(_.debounce(toggleRemoveFee,
      MILLS_TO_IGNORE, true));

  /*
    Warning: Placing the true parameter outside of the debounce call:

    $jq('#color_search_text').keyup(_.debounce(processSearch,
        MILLS_TO_IGNORE_SEARCH), true);

    results in "TypeError: e.handler.apply is not a function".
   */
});