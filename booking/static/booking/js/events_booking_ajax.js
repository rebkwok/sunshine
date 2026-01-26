/*
  This file must be imported immediately-before the close-</body> tag,
  and after JQuery and Underscore.js are imported.
*/

var $jq = jQuery.noConflict();

/**
  The number of milliseconds to ignore clicks on the *same* like
  button, after a button *that was not ignored* was clicked. Used by
  `$(document).ready()`.
  Equal to <code>500</code>.
 */
var MILLS_TO_IGNORE = 500;


/**
   Executes a toggle click. Triggered by clicks on the book button.
 */
var toggleBooking = function()  {

    //In this scope, "this" is the button just clicked on.
    //The "this" in processResult is *not* the button just clicked
    //on.
    var $button_just_clicked_on = $jq(this);
    
    //The value of the "data-event_id" attribute.
    var event_id = $button_just_clicked_on.data('event_id');
    var event_str = $button_just_clicked_on.data('event_str');
    var ref = $button_just_clicked_on.data('ref');
    var show_warning = $button_just_clicked_on.data('show_warning');
    var cancellation_fee = $button_just_clicked_on.data('cancellation_fee');

    if (show_warning) {
        $jq('#confirm-dialog').dialog({
          height: "auto",
          width: 500,
          modal: true,
          closeOnEscape: true,
          dialogClass: "no-close",
          title: "Warning!",
          open: function() {
            const eventText = "<strong>" + event_str + "</strong><br/>";
            const contentText = "Please note that cancellation at this time will incur a cancellation fee of £" + cancellation_fee + " and your account will be locked for booking until your fees have been paid."

            $jq(this).html(eventText + contentText + "<br><br>Please confirm you want to continue.");
          },
          buttons: [
              {
                  text: "Continue",
                  click: function () {
                      doTheAjax();
                      $jq(this).dialog('close');
                  },
              },
              {
                  text: "Go back",
                  click: function () {
                      $jq(this).dialog('close');
                  },
              }
          ]
      })
    } else {
        doTheAjax()
  }

  function doTheAjax() {
    var processResult = function(
       result, status, jqXHR)  {
        if (result.redirect) {
            window.location = result.url;
          } 
        else {  
        //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "', user_id='" + user_id + "'");
        //  display the result with alerts only on the tab we're on
        $jq('#book_' + event_id).html(result.html);
        }
   };

    var updateOnComplete  = function() {
        if (ref == 'events') {
            $jq.ajax(
                {
                    url: '/booking/ajax-update-booking-count/' + event_id + '/',
                    dataType: 'json',
                    success: processBookingCount
                    //Should also have a "fail" call as well.
                }
            );
        }
        else if (ref == 'bookings') {
            $jq.ajax(
                {
                    url: '/booking/update-booking-details/' + event_id + '/',
                    dataType: 'json',
                    success: processBookingDetails
                    //Should also have a "fail" call as well.
                }
            );
        }
    };

    var processBookingCount = function(
       result, status, jqXHR)  {
      //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "'");
          $jq('#booking_count_' + event_id).html(result.booking_count);
            if (result.full === true) {
                $jq('#booking_count_' + event_id).removeClass('badge-green');
                $jq('#booking_count_' + event_id).addClass('badge-dark');
            }
            else {
                $jq('#booking_count_' + event_id).removeClass('badge-dark');
                $jq('#booking_count_' + event_id).addClass('badge-green');
            }

        if (result.booked == true) {
            $jq('#table-row-event-' + event_id).removeClass('table-light');
            $jq('#table-row-event-' + event_id).addClass('table-warning');
        }
        else {
            $jq('#table-row-event-' + event_id).removeClass('table-warning');
            $jq('#table-row-event-' + event_id).addClass('table-light');
        }
        $jq('#cart_item_menu_count').text(result.cart_item_menu_count);
        $jq('#cart_item_menu_count_xs').text(result.cart_item_menu_count);
   };


    var processBookingDetails = function(
       result, status, jqXHR)  {
      //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "'");
       console.log(result);
        $jq('#booked-' + event_id + '-' + 'status').html(result.display_status);
        $jq('#booked-' + event_id + '-' + 'paid').html(result.display_paid);
        $jq('#booked-' + event_id + '-' + 'membership').html(result.display_membership);
        if (result.status === 'OPEN' && result.no_show === false) {
            $jq('#booked-' + event_id + '-' + 'row').removeClass('expired');
        }
        else if (result.display_status === 'CANCELLED') {
            $jq('#booked-' + event_id + '-' + 'row').addClass('expired');
        }
        $jq('#cart_item_menu_count').text(result.cart_item_menu_count);
        $jq('#cart_item_menu_count_xs').text(result.cart_item_menu_count);
   };

    var processFailure = function(
       result, status, jqXHR)  {
      //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "'");
      if (result.responseText) {
        vNotify.error({text:result.responseText,title:'Error',position: 'bottomRight'});
      }
   };

   $jq.ajax(
       {
          url: '/booking/toggle-booking/' + event_id + '/?ref=' + ref,
          dataType: 'json',
          type: 'POST',
          success: processResult,
          //Should also have a "fail" call as well.
          complete: updateOnComplete,
          error: processFailure
       }
    );

  };

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

      td_ajax_book_button

    This attaches a listener to *every one*. Calling this again
    would attach a *second* listener to every button, meaning each
    click would be processed twice.
   */
  $jq('.td_ajax_book_btn').click(_.debounce(toggleBooking,
      MILLS_TO_IGNORE, true));

  /*
    Warning: Placing the true parameter outside of the debounce call:

    $jq('#color_search_text').keyup(_.debounce(processSearch,
        MILLS_TO_IGNORE_SEARCH), true);

    results in "TypeError: e.handler.apply is not a function".
   */
});