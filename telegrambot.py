from datetime import datetime
from telegram import Update
from telegram.ext import Updater, CommandHandler

from dblayer import get_db_connection, get_db_results, entities, cities, update_feed_data_db, get_user_token
from dataflow import add_city, add_entity, get_query_fields, get_entity_location_from_query_fields, get_unique_providers_from_ics, get_provider_details, get_feed_params, post_data_to_ics
from dialogflowhandler import get_dialogflow_response, get_dialogflow_context_parameters
from utils import current_milli_time, get_verified_at, get_numbers_str, get_help_text, get_logger, sendCowinOTP, validateCowinOTP
from slotbooking import book_slot

logger = get_logger()

db = get_db_connection()
collection = db.ics

def get_incoming_msg(context):
    context_args = context.args
    incoming_query = " ".join(context_args)
    logger.debug("Telegram Query : {}".format(incoming_query))
    return incoming_query

def get_default_error_response(update, error_msg):
    update.message.reply_text(error_msg)
    return

def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi from ICSBot :-)')
    return

def add(update, context):
    """Add city/entity to dialogflow and db when the command /add is issued."""
    incoming_query = get_incoming_msg(context)
    incoming_msg = "add " + incoming_query
    logger.debug("Telegram incoming_msg : {}".format(incoming_msg))

    dialogflow_response = get_dialogflow_response(incoming_msg)
    if not dialogflow_response:
        update.message.reply_text("Invalid query.\nPlease try with another query.\n")
        return

    dialogflow_intent = dialogflow_response.query_result.intent.display_name

    if dialogflow_intent == "AddCity":
        city_name = add_city(incoming_msg, db.entitiesandcities)
        cities[city_name] = city_name.capitalize()
        update.message.reply_text("Success.\nCity {} has been added successfully.".format(city_name))
        return

    if dialogflow_intent == "AddEntity":
        entity_name = add_entity(incoming_msg, db.entitiesandcities)
        entities[entity_name] = entity_name.capitalize()
        update.message.reply_text("Success.\nEntity {} has been added successfully.".format(city_name))
        return

def feed(update, context):
    """Feed verified lead when /feed is issued."""
    incoming_query = get_incoming_msg(context)
    incoming_msg = "feed " + incoming_query
    logger.debug("Telegram incoming_msg : {}".format(incoming_msg))

    query_fields = get_query_fields(incoming_msg)

    if not query_fields:
        update.message.reply_text("No data found for your query.\nPlease try with another query.\n")
        return

    contact_number, entity, verifiedby, req, location, name, quantity, loc, address, price = get_feed_params(query_fields, entities, cities)
        
    if entity not in entities:
        return update.message.reply_text("Entity not found in system.\nPlease add entity.".format(entity))

    if location not in cities:
        return update.message.reply_text("City not found in system.\nPlease add city.".format(location))

    if not contact_number:
        update.message.reply_text("Invalid query.\nPlease provide contact number.\n")
        return

    if not entity:
        update.message.reply_text("Invalid query.\nPlease provide entity.\n")
        return

    if not verifiedby:
        update.message.reply_text("Invalid query.\nPlease provide verified by.\n")
        return

    if not req:
        update.message.reply_text("Invalid query.\nPlease provide entity.\n")
        return
    
    if not location:
        update.message.reply_text("Invalid query.\nPlease provide location.\n")
        return
    
    feed_data, success = post_data_to_ics(name, req, quantity, loc, address, contact_number)

    filed_at = datetime.utcfromtimestamp(feed_data["filedAt"]/1000).isoformat()

    success = update_feed_data_db(collection, entity, location, name, contact_number, address, loc, quantity, filed_at, verifiedby, price)

    if success:
        verified_at = get_verified_at(filed_at)
        provider_res = "Name: {}\nEntity: {}\nContact Number: {}\nAddress: {}\nQuantity: {}\nPrice: {}\nVerified At: {}\n\n".format(name, entity, contact_number, address if address else location, quantity if quantity else "Unknown", price, verified_at)
        update.message.reply_text("Thanks for providing information\n" + provider_res)
        return
    else:
        update.message.reply_text("There is some issue in data feed.\n")
        return

def query(update, context):
    """Send a message when the command /query is issued."""
    incoming_query = get_incoming_msg(context)

    query_fields = get_query_fields(incoming_query)

    if not query_fields:
        return get_default_error_response(update, "No data found for your query.\n", "Please try with another query.\n")

    req, loc, entity, location = get_entity_location_from_query_fields(query_fields, entities, cities)

    if not req and not loc:
        return get_default_error_response(update, "No data found for your query.\n", "Please try with another query.\n")

    unique_providers = get_unique_providers_from_ics(req, loc)

    dbfiltereddata = get_db_results(collection, entity, location)

    provider_details = get_provider_details(dbfiltereddata, unique_providers, entity, location)

    ics_resp = ''.join(provider_details)

    update.message.reply_text('User response for query :-)\n {}'.format(ics_resp))
    return

def book(update, context):
    """Send a message when the command /query is issued."""
    incoming_query = get_incoming_msg(context)
    incoming_msg = "book " + incoming_query
    logger.debug("Telegram incoming_msg : {}".format(incoming_msg))

    dialogflow_response = get_dialogflow_response(incoming_msg)
    if not dialogflow_response:
        update.message.reply_text("Invalid query.\nPlease try with another query.\n")
        return

    dialogflow_intent = dialogflow_response.query_result.intent.display_name
    logger.debug("Dialogflow Response : ".format(dialogflow_response))

    if dialogflow_intent in ["VaccineSlotBooking", "ResendCowinOTP"]:
        outCnt = get_dialogflow_context_parameters(dialogflow_response.query_result, "userprovidesmobilenumber")
        if not outCnt:
            update.message.reply_text("Internal context issue.Please try sending the query again.\n")
            return
        mobile_number = outCnt.get('mobile_number')
        mobile = get_numbers_str(mobile_number)
        if not mobile:
            update.message.reply_text("Please provide valid mobile number.\n")
            return
        txnID = sendCowinOTP(mobile)
        if not txnID:
            update.message.reply_text("Internal issue sending Cowin OTP.\n")
            return
        otp_dict = {"mobile": mobile, "transactionid": txnID, "createdAt": current_milli_time()}
        db.otp.update_one({"mobile": mobile}, {"$set": otp_dict}, upsert=True)
        fulfillment_text = dialogflow_response.query_result.fulfillment_text
        update.message.reply_text(fulfillment_text)
        return

    if dialogflow_intent == "VaccineOTPVerification":
        outCnt = get_dialogflow_context_parameters(dialogflow_response.query_result, "userprovidesmobilenumber")
        if not outCnt:
            update.message.reply_text("Internal context issue.Please try sending the query again.\n")
            return
        mobile_number = outCnt.get('mobile_number')
        mobile = get_numbers_str(mobile_number)
        if not mobile_number:
            update.message.reply_text("Please provide valid mobile number.\n")
            return
        otp = outCnt.get('otp')
        if not otp:
            update.message.reply_text("Please provide valid CoWIN OTP.\n")
            return
        token, error = validateCowinOTP(db.otp, mobile, otp)
        if token:
            db.otp.update_one({"mobile": mobile}, {"$set": {"token": token, "updatedAt": current_milli_time()}}, upsert=True)
            fulfillment_text = dialogflow_response.query_result.fulfillment_text
            update.message.reply_text(fulfillment_text)
            return
        else:
            update.message.reply_text("Please provide state and district name")
            return
    
    if dialogflow_intent == "VaccineStateAndDistrict":
        outCnt = get_dialogflow_context_parameters(dialogflow_response.query_result, "userprovidesmobilenumber")
        if not outCnt:
            update.message.reply_text("Internal context issue.Please try sending the query again.\n")
            return
        mobile_number = outCnt.get('mobile_number') if outCnt else None
        if not mobile_number:
            update.message.reply_text("Please provide valid mobile number.\n")
            return
        mobile = get_numbers_str(mobile_number)
        state = outCnt.get('state')
        district = outCnt.get('district')
        if not state:
            update.message.reply_text("Please provide State Name.\n")
            return
        if not district:
            update.message.reply_text("Please provide District Name.\n")
            return
        token = get_user_token(db.otp, mobile)
        status, error = book_slot(mobile, token, state, district)
        if status:
            update.message.reply_text("Trying Slot Booking for mobile number {}, state {} and district {}.\n".format(mobile, state, district) + "If slot booling didn't happen. Try again in 2 min.\n")
            return
        else:
            update.message.reply_text("Slot Booking Response.\n" + error)
            return
    
    update.message.reply_text("Internal Issue for slot booking")
    return

def help(update, context):
    """Send a message when the command /help is issued."""
    help_text = get_help_text(is_telegram=True)
    update.message.reply_text(help_text)
    return

def error(update, context):
    """Log Errors caused by Updates."""
    if update:
        update.message.reply_text('Update "%s" caused error "%s"', update, context.error)
    return

def main(api_token):
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(api_token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("query", query))
    dp.add_handler(CommandHandler("add", add))
    dp.add_handler(CommandHandler("feed", feed))
    dp.add_handler(CommandHandler("book", book))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    # updater.idle()
