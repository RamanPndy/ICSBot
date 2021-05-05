from flask import Flask, request
import requests, os, uuid
from twilio.twiml.messaging_response import MessagingResponse
import dialogflow
from google.api_core.exceptions import InvalidArgument
from datetime import datetime
import pymongo
import urllib

from utils import get_provider_data

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'icsbotsa.json'

PROJECT_ID = os.environ.get('PROJECTID')
DIALOGFLOW_LANGUAGE_CODE = 'en'
SESSION_ID = 'me'

db_username = urllib.parse.quote_plus(os.environ.get('DBUSER'))
db_pass = urllib.parse.quote_plus(os.environ.get('DBPASS'))

client = pymongo.MongoClient("mongodb+srv://{}:{}@cluster0.bsugd.mongodb.net/icsdb?retryWrites=true&w=majority".format(db_username, db_pass))
db = client.icsdb
collection = db.ics

app = Flask(__name__)

entities = {"oxygen cylinder": "Oxygen%20Cylinder", "oxygen": "Oxygen", "icu": "ICU", "icu bed": "ICU%20Bed", "medicine": "Medicine", "plasma": "Plasma", "hospital bed": "Hospital%20Bed", "hospital": "Hospital", "food":"Homemade%20Food" }
cities = {"kanpur": "Kanpur,%20Uttar%20Pradesh", "varanasi":"Varanasi,%20Uttar%20Pradesh", "banaras":"Varanasi,%20Uttar%20Pradesh", "lucknow": "Lucknow,%20Uttar%20Pradesh", "delhi": "Delhi", "mumbai": "Mumbai"}

@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').lower()
    print(incoming_msg)

    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(PROJECT_ID, SESSION_ID)
    text_input = dialogflow.types.TextInput(text=incoming_msg, language_code=DIALOGFLOW_LANGUAGE_CODE)
    query_input = dialogflow.types.QueryInput(text=text_input)
    try:
        response = session_client.detect_intent(session=session, query_input=query_input)
    except InvalidArgument:
        raise

    print("Response Parameters:", response.query_result.parameters.fields)
    query_fields = response.query_result.parameters.fields
    location = query_fields['location'].string_value
    entity = query_fields['entity'].string_value

    req = entities.get(entity, '')
    loc = cities.get(location, '')

    ics_qry = "https://fierce-bayou-28865.herokuapp.com/api/v1/covid/?entity={}&city={}".format(req, loc)
    print (ics_qry)

    qry_res = requests.get(ics_qry)
    qry_res_data = qry_res.json()
    print (qry_res_data)

    qry_providers = qry_res_data["data"]["covid"]
    dedupe_providers = { each['provider_contact'] : each for each in qry_providers }.values()
    unique_providers = list(dedupe_providers)[::-1]

    dbresults = collection.find({
        '$and': [
            {'entity': entity},
            {'location': location}
        ]
    })
    dbfiltereddata = []
    for dbr in dbresults:
        dbfiltereddata.append(dbr)
    
    providers_data = []
    new_data_to_be_added_in_db = []
    if dbfiltereddata and not unique_providers:
        providers_data = dbfiltereddata
    elif unique_providers and not dbfiltereddata:
        providers_data = unique_providers
        new_data_to_be_added_in_db = unique_providers
    elif unique_providers and dbfiltereddata:
        providers_data = dbfiltereddata
        dbdatacontacts = [dbd.get('provider_contact') for dbd in dbfiltereddata]
        for pd in unique_providers:
            pdc = pd.get("provider_contact", "")
            if pdc not in dbdatacontacts:
                new_data_to_be_added_in_db.append(pd)
                providers_data.append(pd)
    
    for newdata in new_data_to_be_added_in_db:
        doc_id = str(uuid.uuid4())
        provider_name, provider_contact, filed_at, quantity, address = get_provider_data(newdata)
        provider_dict = {"entity": entity, "location": location, "provider_name": provider_name, "provider_contact": provider_contact, "provider_address": address, "quantity": quantity, "filedAt": filed_at}
        collection.insert_one(provider_dict)

    provider_details = []
    for provider in providers_data:
        provider_name, provider_contact, filed_at, quantity, address = get_provider_data(provider)
        if provider_name and provider_contact and filed_at:
            verifieddt = datetime.strptime(filed_at, '%Y-%m-%dT%H:%M:%S.%f%z')
            verified_at = f'{verifieddt:%d/%m/%Y %H:%M:%S}'
            provider_res = "Name: {}\nContact Number: {}\nAddress: {}\nQuantity: {}\nVerified At: {}\n\n".format(provider_name, provider_contact, address, quantity, verified_at)
            provider_details.append(provider_res)

    # print("Query text:", response.query_result.query_text)
    # print("Detected intent:", response.query_result.intent.display_name)
    # print("Detected intent confidence:", response.query_result.intent_detection_confidence)
    # print("Fulfillment text:", response.query_result.fulfillment_text)

    ics_resp = ''.join(provider_details[:10])
    print (ics_resp)

    resp = MessagingResponse()
    if ics_resp:
        msg = resp.message("Below are some resources we found\n")
    else:
        msg = resp.message("No data found")
    msg.body(ics_resp)
    return str(resp)

@app.route('/fulfillment', methods=['POST'])
def fulfillment():
    return "working"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)