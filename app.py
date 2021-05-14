from flask import Flask, request
import os
from twilio.twiml.messaging_response import MessagingResponse
import logging
import threading
from datetime import datetime
from fpdf import FPDF
from google.cloud import storage

from utils import current_milli_time, get_verified_at, get_numbers_str, get_help_text
from dataflow import add_city, add_entity, get_query_fields, get_entity_location_from_query_fields, get_unique_providers_from_ics, get_provider_details, get_feed_params,  post_data_to_ics
from dialogflowhandler import get_dialogflow_response
from dblayer import get_db_connection, get_entities_and_cities, get_db_results, entities, cities, update_feed_data_db
from telegrambot import main

APPPORT = os.environ.get('PORT')

db = get_db_connection()
collection = db.ics

app = Flask(__name__)

google_storage_client = storage.Client.from_service_account_json(json_credentials_path='icsstoragesa.json')
bucket = google_storage_client.get_bucket('icsbot')

logging.basicConfig(level=logging.DEBUG)

TELEGRAM_API_TOKEN = os.environ.get("TOKEN")

@app.route('/', methods=['GET'])
def welcome():
    return "Welcome to ICS Bot App"

def get_default_error_response(msg, body):
    resp = MessagingResponse()
    msg = resp.message(msg)
    msg.body(body)
    return str(resp)

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').lower()
    logging.debug(incoming_msg)

    if incoming_msg == "help":
        help_text = get_help_text()
        return get_default_error_response("Welcome to ICS Bot.\n", help_text)

    dialogflow_response = get_dialogflow_response(incoming_msg)
    if not dialogflow_response:
        help_text = get_help_text()
        return get_default_error_response("Invalid query.\n", "Please try with another query.\n" + help_text)

    dialogflow_intent = dialogflow_response.query_result.intent.display_name

    if dialogflow_intent == "AddCity":
        city_name = add_city(incoming_msg,db.entitiesandcities)
        cities[city_name] = city_name.capitalize()
        return get_default_error_response("Success.\n", "City {} has been added successfully.".format(city_name))

    if dialogflow_intent == "AddEntity":
        entity_name = add_entity(incoming_msg, db.entitiesandcities)
        entities[entity_name] = entity_name.capitalize()
        return get_default_error_response("Success.\n", "Entity {} has been added successfully.".format(entity_name))

    query_fields = get_query_fields(incoming_msg)

    if not query_fields:
        return get_default_error_response("No data found for your query.\n", "Please try with another query.\n")

    if 'feed' not in incoming_msg:
        req, loc, entity, location = get_entity_location_from_query_fields(query_fields, entities, cities)

        if not req and not loc:
            return get_default_error_response("No data found for your query.\n", "Please try with another query.\n")

        unique_providers = get_unique_providers_from_ics(req, loc)

        dbfiltereddata = get_db_results(collection, entity, location)
        
        provider_details = get_provider_details(dbfiltereddata, unique_providers, entity, location)

        # print("Query text:", response.query_result.query_text)
        # print("Detected intent:", response.query_result.intent.display_name)
        # print("Detected intent confidence:", response.query_result.intent_detection_confidence)
        # print("Fulfillment text:", response.query_result.fulfillment_text)
        media_type = False
        if len(provider_details) < 5:
            ics_resp = ''.join(provider_details)
            logging.debug (ics_resp)
        else:
            pdf_name = "{}_{}.pdf".format(entity.replace(" ", "_"), location.replace(" ", "_"))
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size = 15)
            pdf.cell(200, 10, txt = "{}\n\n".format(incoming_msg), ln = 1, align = 'C')
            for msg in provider_details:
                msg_data = [x for x in msg.split("\n") if x]
                name, contact_num, address, qty, verifiedAt = msg_data
                pdf.cell(200, 5, txt = name, ln=1)
                pdf.cell(200, 5, txt = contact_num, ln=1)
                pdf.cell(200, 5, txt = address, ln=1)
                pdf.cell(200, 5, txt = qty, ln=1)
                pdf.cell(200, 5, txt = verifiedAt, ln=1)
                pdf.cell(200, 5, txt = "-----------------------------------------------------------------------", ln=1)
                pdf.cell(200, 5, txt = "-----------------------------------------------------------------------", ln=1)
            pdf.output(pdf_name)

            object_name_in_gcs_bucket = bucket.blob(pdf_name)
            object_name_in_gcs_bucket.upload_from_filename(pdf_name)
            object_name_in_gcs_bucket.make_public()
            upload_res = object_name_in_gcs_bucket.public_url
            if upload_res:
                ics_resp = upload_res
                logging.debug (ics_resp)
                media_type = True
                os.remove(pdf_name)

        resp = MessagingResponse()
        if ics_resp:
            msg = resp.message("Below are some resources we have found\n")
        else:
            msg = resp.message("No data found. Please try with different query.\n")
        if media_type:
            msg.media(ics_resp)
        else:
            msg.body(ics_resp)
        return str(resp)
    else:
        contact_number, entity, verifiedby, req, location, name, quantity, loc, address, price = get_feed_params(query_fields, entities, cities)
        
        if entity not in entities:
            return get_default_error_response("Entity not found in system.\n".format(entity), "Please add entity.\n")

        if location not in cities:
            return get_default_error_response("City not found in system.\n".format(location), "Please add city.\n")

        if not contact_number:
            return get_default_error_response("Invalid query.\n", "Please provide contact number.\n")

        if not entity:
            return get_default_error_response("Invalid query.\n", "Please provide entity.\n")
        
        if not verifiedby:
            return get_default_error_response("Invalid query.\n", "Please provide verified by.\n")

        if not req:
            return get_default_error_response("Invalid query.\n", "Please provide entity.\n")
        
        if not location:
            return get_default_error_response("Invalid query.\n", "Please provide location.\n")

        feed_data, success = post_data_to_ics(name, req, quantity, loc, address, contact_number)

        filed_at = datetime.utcfromtimestamp(feed_data["filedAt"]/1000).isoformat()

        success = update_feed_data_db(collection, entity, location, name, contact_number, address, loc, quantity, filed_at, verifiedby, price)

        resp = MessagingResponse()
        if success:
            msg = resp.message("Thanks for providing information\n")
            verified_at = get_verified_at(filed_at)
            provider_res = "Name: {}\nEntity: {}\nContact Number: {}\nAddress: {}\nQuantity: {}\nPrice: {}\nVerified At: {}\n\n".format(name, entity, contact_number, address if address else location, quantity if quantity else "Unknown", price, verified_at)
            msg.body(provider_res)
        else:
            msg = resp.message("There is some issue in data feed.\n")
        return str(resp)

@app.route('/fulfillment', methods=['POST'])
def fulfillment():
    return "working"

if __name__ == '__main__':
    telegram_bot_thread = threading.Thread(target=main, args=(TELEGRAM_API_TOKEN,))
    telegram_bot_thread.start()
    app.run(host='0.0.0.0', port=int(APPPORT), threaded=True)