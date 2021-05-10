import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters

from utils import get_db_connection, get_entities_and_cities
from dataflow import get_query_fields, get_entity_location_from_query_fields, get_unique_providers_from_ics, get_provider_details, get_db_results

logging.basicConfig(level=logging.DEBUG)

db = get_db_connection()
collection = db.ics

entities, cities = get_entities_and_cities(db.entitiesandcities)

def get_default_error_response(update, error_msg):
    update.message.reply_text(error_msg)
    return

def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi from ICSBot :-)')

def query(update, context):
    """Send a message when the command /query is issued."""
    context_args = context.args
    incoming_query = " ".join(context_args)
    logging.debug("Telegram Query : {}".format(incoming_query))

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

def help(update, context):
    """Send a message when the command /help is issued."""
    help_text = "Type /query <query> for example: /query hospital in kanpur to get relavant results. Type /feed <query> to feed data."
    update.message.reply_text(help_text)

def error(update, context):
    """Log Errors caused by Updates."""
    update.message.reply_text('Update "%s" caused error "%s"', update, context.error)

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

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
