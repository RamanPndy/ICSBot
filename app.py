from flask import Flask, request
import requests, os, uuid
from twilio.twiml.messaging_response import MessagingResponse
import dialogflow
from google.api_core.exceptions import InvalidArgument
import pymongo
import urllib
from datetime import datetime

from utils import get_provider_data, current_milli_time, get_verified_at, get_data_from_field

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

entities = {"oxygen cylinder": "Oxygen%20Cylinder", "oxygen": "Oxygen", "oxygen refilling": "Oxygen%20Refilling", "icu": "ICU", "icu bed": "ICU%20Bed", "medicine": "Medicine", "plasma": "Plasma", "hospital bed": "Hospital%20Bed", "hospital": "Hospital", "food":"Homemade%20Food" , "fabiflu": "Fabiflu", "ambulance": "Ambulance"}
cities = {"kanpur": "Kanpur,%20Uttar%20Pradesh", "varanasi":"Varanasi,%20Uttar%20Pradesh", "banaras":"Varanasi,%20Uttar%20Pradesh", "lucknow": "Lucknow,%20Uttar%20Pradesh", "delhi": "New%20Delhi,%20Delhi", "mumbai": "Mumbai,%20Maharashtra"}

@app.route('/', methods=['GET'])
def welcome():
    return "Welcome to ICS Bot App"

def get_default_error_response():
    resp = MessagingResponse()
    msg = resp.message("No data found for your query.\n")
    msg.body("Please try with another query.\n")
    return str(resp)

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

    query_fields = response.query_result.parameters.fields
    print("Response Parameters:", query_fields)

    if not query_fields:
        return get_default_error_response()

    if 'feed' not in incoming_msg:
        location = query_fields['location'].string_value
        entity = query_fields['entity'].string_value

        req = entities.get(entity, '')
        loc = cities.get(location, '')

        if not req and not loc:
            return get_default_error_response()

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
            provider_dict = {"entity": entity, "location": location, "provider_name": provider_name, "provider_contact": provider_contact, "provider_address": address, "quantity": quantity if quantity else "Unknown", "filedAt": filed_at}
            try:
                collection.insert_one(provider_dict)
            except Exception as e:
                print (e)

        provider_details = []
        for provider in providers_data:
            provider_name, provider_contact, filed_at, quantity, address = get_provider_data(provider)
            verified_at = get_verified_at(filed_at)
            provider_res = "Name: {}\nContact Number: {}\nAddress: {}\nQuantity: {}\nVerified At: {}\n\n".format(provider_name if provider_name else "Unavailable", provider_contact if provider_contact else "Unavailable", address if address else "Unavailable", quantity if quantity else "Unknown", verified_at)
            provider_details.append(provider_res.replace("-1", "Unknown"))

        # print("Query text:", response.query_result.query_text)
        # print("Detected intent:", response.query_result.intent.display_name)
        # print("Detected intent confidence:", response.query_result.intent_detection_confidence)
        # print("Fulfillment text:", response.query_result.fulfillment_text)

        ics_resp = ''.join(provider_details[:10])
        print (ics_resp)

        resp = MessagingResponse()
        if ics_resp:
            msg = resp.message("Below are some resources we have found\n")
        else:
            msg = resp.message("No data found. Please try with different query.\n")
        msg.body(ics_resp)
        return str(resp)
    else:
        name = query_fields['name'].string_value
        location = query_fields['location'].string_value
        address = query_fields['address'].string_value
        entity = get_data_from_field(query_fields, 'entity')
        provider_contact = query_fields['contact'].string_value
        quantity = query_fields['quantity'].string_value
        verifiedby = query_fields['verifiedby'].string_value

        req = entities.get(entity, '').replace("%20", " ")
        loc = cities.get(location, '').replace("%20", " ")

        ics_qry = "https://fierce-bayou-28865.herokuapp.com/api/v1/covid/nootp"
        feed_data = {
                "name":name,
                "entity":req,
                "quantity":quantity if quantity else "Unknown",
                "city":loc,
                "provider_name":name,
                "provider_address":address if address else "Unavailable",
                "provider_contact":provider_contact if provider_contact else "Unavailable",
                "link":"",
                "filedAt":current_milli_time(),
                "location":"0,0"
            }

        success = True
        try:
            qry_res = requests.post(ics_qry, data = feed_data)
        except Exception as e:
            print (e)
            success = False

        qry_res_data = qry_res.json()
        print(qry_res_data)

        filed_at = datetime.utcfromtimestamp(feed_data["filedAt"]/1000).isoformat()

        provider_dict = {"entity": entity, "location": location, "provider_name": name, "provider_contact": provider_contact, "provider_address": address if address else loc, "quantity": quantity if quantity else "Unknown", "filedAt": filed_at, "verifiedby": verifiedby}
        try:
            collection.insert_one(provider_dict)
        except Exception as e:
            print(e)
            success = False

        resp = MessagingResponse()
        if success:
            msg = resp.message("Thanks for providing information\n")
            verified_at = get_verified_at(filed_at)
            provider_res = "Name: {}\nContact Number: {}\nAddress: {}\nQuantity: {}\nVerified At: {}\n\n".format(name, provider_contact, address if address else location, quantity if quantity else "Unknown", verified_at)
            msg.body(provider_res)
        else:
            msg = resp.message("There is some issue in data feed.\n")
        return str(resp)

@app.route('/fulfillment', methods=['POST'])
def fulfillment():
    return "working"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)