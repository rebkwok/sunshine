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
var MILLS_TO_IGNORE = 1000;


var processRemoveMembership = function()  {

    //In this scope, "this" is the button just clicked on.
    //The "this" in processResult is *not* the button just clicked
    //on.
    var $button_just_clicked_on = $jq(this);

    //The value of the "data-event_id" attribute.
    var user_membership_id = $button_just_clicked_on.data('user_membership_id');

    var processResult = function(
       result, status, jqXHR)  {
      //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "'");
    if (result.redirect) {
          window.location = result.url;
      } else {
        $jq('#cart-row-membership-' + user_membership_id).html("");
        $jq('#cart_item_menu_count').text(result.cart_item_menu_count);
        $jq('#total').text(result.cart_total);
        $jq('#checkout-btn').data('total', result.cart_total);
    }
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
          url: '/booking/ajax-cart-item-delete/',
          dataType: 'json',
          type: 'POST',
          data: {csrfmiddlewaretoken: window.CSRF_TOKEN, item_type: "membership", item_id: user_membership_id},
          success: processResult,
          //Should also have a "fail" call as well.
          error: processFailure
       }
    );

};


var processRemoveBooking = function()  {

    //In this scope, "this" is the button just clicked on.
    //The "this" in processResult is *not* the button just clicked
    //on.
    var $button_just_clicked_on = $jq(this);

    //The value of the "data-event_id" attribute.
    var booking_id = $button_just_clicked_on.data('booking_id');

    var processResult = function(
       result, status, jqXHR)  {
      //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "'");
    $jq('#cart-row-booking-' + booking_id).html("");
    $jq('#cart_item_menu_count').text(result.cart_item_menu_count);
    $jq('#total').text(result.cart_total);
    $jq('#checkout-btn').data('total', result.cart_total);
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
          url: '/booking/ajax-cart-item-delete/',
          dataType: 'json',
          type: 'POST',
          data: {csrfmiddlewaretoken: window.CSRF_TOKEN, item_type: "booking", item_id: booking_id},
          success: processResult,
          //Should also have a "fail" call as well.
          error: processFailure
       }
    );

};


var processRemoveGiftVoucher = function()  {

    //In this scope, "this" is the button just clicked on.
    //The "this" in processResult is *not* the button just clicked
    //on.
    var $jqbutton_just_clicked_on = $jq(this);

    //The value of the "data-event_id" attribute.
    var gift_voucher_id = $jqbutton_just_clicked_on.data('gift_voucher_id');

    var processResult = function(
       result, status, jqXHR)  {
      //console.log("sf result='" + result + "', status='" + status + "', jqXHR='" + jqXHR + "'");
    $jq('#cart-row-gift-voucher-' + gift_voucher_id).html("");
    $jq('#cart_item_menu_count').text(result.cart_item_menu_count);
    $jq('#total').text(result.cart_total);
    $jq('#checkout-btn').data('total', result.cart_total);
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
          url: '/booking/ajax-cart-item-delete/',
          dataType: 'json',
          type: 'POST',
          data: {csrfmiddlewaretoken: window.CSRF_TOKEN, item_type: "gift_voucher", item_id: gift_voucher_id},
          success: processResult,
          //Should also have a "fail" call as well.
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

      td_ajax_book_button

    This attaches a listener to *every one*. Calling this again
    would attach a *second* listener to every button, meaning each
    click would be processed twice.
   */
  $jq('.remove-membership').click(_.debounce(processRemoveMembership, MILLS_TO_IGNORE, true));
  $jq('.remove-booking').click(_.debounce(processRemoveBooking, MILLS_TO_IGNORE, true));
  $jq('.remove-gift-voucher').click(_.debounce(processRemoveGiftVoucher, MILLS_TO_IGNORE, true));
  /*
    Warning: Placing the true parameter outside of the debounce call:

    $jq('#color_search_text').keyup(_.debounce(processSearch,
        MILLS_TO_IGNORE_SEARCH), true);

    results in "TypeError: e.handler.apply is not a function".
   */

});