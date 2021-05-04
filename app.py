from flask import Flask, request
import requests, os
from datetime import datetime
from twilio.twiml.messaging_response import MessagingResponse
import dialogflow
from google.api_core.exceptions import InvalidArgument

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'icsbotsa.json'

DIALOGFLOW_PROJECT_ID = 'icsbot-xweo'
DIALOGFLOW_LANGUAGE_CODE = 'en'
SESSION_ID = 'me'

app = Flask(__name__)

entities = {"oxygen cylinder": "Oxygen%20Cylinder", "oxygen": "Oxygen", "icu": "ICU", "icu bed": "ICU%20Bed", "medicine": "Medicine", "plasma": "Plasma", "hospital bed": "Hospital%20Bed", "hospital": "Hospital"}
cities = {"kanpur": "Kanpur,%20Uttar%20Pradesh", "varanasi":"Varanasi,%20Uttar%20Pradesh", "banaras":"Varanasi,%20Uttar%20Pradesh", "lucknow": "Lucknow,%20Uttar%20Pradesh", "delhi": "Delhi", "mumbai": "Mumbai"}


@app.route('/bot', methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').lower()
    print(incoming_msg)

    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(DIALOGFLOW_PROJECT_ID, SESSION_ID)
    text_input = dialogflow.types.TextInput(text=incoming_msg, language_code=DIALOGFLOW_LANGUAGE_CODE)
    query_input = dialogflow.types.QueryInput(text=text_input)
    try:
        response = session_client.detect_intent(session=session, query_input=query_input)
    except InvalidArgument:
        raise

    # import ipdb; ipdb.set_trace()
    print("Response Parameters:", response.query_result.parameters.fields)
    query_fields = response.query_result.parameters.fields
    location = query_fields['location'].string_value
    entity = query_fields['entity'].string_value

    req = entities.get(entity, '')
    loc = cities.get(location, 'All%20India')

    ics_qry = "https://fierce-bayou-28865.herokuapp.com/api/v1/covid/?entity={}&city={}".format(req, loc)
    print (ics_qry)

    qry_res = requests.get(ics_qry)
    qry_res_data = qry_res.json()
    print (qry_res_data)

    providers = qry_res_data["data"]["covid"]
    provider_details = []
    for provider in providers:
        name = provider.get("name", "Unavailable")
        provider_name = provider.get("provider_name", "Unavailable")
        provider_contact = provider.get("provider_contact", "Unavailable")
        quantity = provider.get("quantity", "Unavailable")
        filedAt = provider.get("filedAt", "")
        verfiedAt = ""
        if filedAt:
            verifieddt = datetime.strptime(filedAt, '%Y-%m-%dT%H:%M:%S.%f%z')
            verfiedAt = f'{verifieddt:%d/%m/%Y %H:%M:%S}'
        provider = ""
        if name:
            provider = name
        elif provider_name:
            provider = provider_name
        elif name and provider_name:
            provider = name + " OR " + provider_name
        if provider and provider_contact and verfiedAt:
            provider_res = "Name: {}\nProvider Contact Number: {}\nQuantity: {}\nVerified At: {}\n\n".format(provider, provider_contact, quantity, verfiedAt)
            provider_details.append(provider_res)

    # print("Query text:", response.query_result.query_text)
    # print("Detected intent:", response.query_result.intent.display_name)
    # print("Detected intent confidence:", response.query_result.intent_detection_confidence)
    # print("Fulfillment text:", response.query_result.fulfillment_text)

    ics_resp = ''.join(provider_details[::-1][:5])
    print (ics_resp)

    resp = MessagingResponse()
    if ics_resp:
        msg = resp.message(ics_resp)
    else:
        msg = resp.message("No data found")
    msg.body(ics_resp)
    return str(resp)

@app.route('/fulfillment', methods=['POST'])
def fulfillment():
    
    return "wroking"

if __name__ == '__main__':
    app.run()