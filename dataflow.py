import logging
import requests
import uuid

from utils import get_verified_at
from dialogflowhandler import get_dialogflow_response, update_dialogflow_entity
from dblayer import update_db_entity

logging.basicConfig(level=logging.DEBUG)

def get_query_fields(incoming_msg):
    response = get_dialogflow_response(incoming_msg)
    query_fields = response.query_result.parameters.fields
    logging.debug("Response Parameters: {}".format(query_fields))
    return query_fields

def get_entity_location_from_query_fields(query_fields, entities, cities):
    location = query_fields['location'].string_value
    entity = query_fields['entity'].string_value
    
    req = entities.get(entity, '')
    loc = cities.get(location, '')

    return req, loc, entity, location

def get_unique_providers_from_ics(req, loc):
    ics_qry = "https://fierce-bayou-28865.herokuapp.com/api/v1/covid/?entity={}&city={}".format(req, loc)
    logging.debug (ics_qry)
    
    qry_res = requests.get(ics_qry)
    qry_res_data = qry_res.json()
    logging.debug (qry_res_data)
    
    qry_providers = qry_res_data["data"]["covid"]
    dedupe_providers = { each['provider_contact'] : each for each in qry_providers }.values()
    unique_providers = list(dedupe_providers)[::-1]
    return unique_providers

def get_provider_data(provider):
    name = provider.get("name", "")
    provider_name = provider.get("provider_name", "")
    provider_contact = provider.get("provider_contact", "Unavailable")
    quantity = provider.get("quantity", "Unavailable")
    filedAt = provider.get("filedAt", "")
    address = provider.get("provider_address", "Unavailable")
    provider = ""
    if name:
        provider = name
    elif provider_name:
        provider = provider_name
    elif name and provider_name:
        provider = name + " OR " + provider_name
    return provider, provider_contact.replace("\n", ""), filedAt, quantity, address

def get_provider_details(dbfiltereddata, unique_providers, entity, location):
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
            logging.error(e)
    
    provider_details = []
    for provider in providers_data:
        provider_name, provider_contact, filed_at, quantity, address = get_provider_data(provider)
        verified_at = get_verified_at(filed_at)
        provider_res = "Name: {}\nContact Number: {}\nAddress: {}\nQuantity: {}\nVerified At: {}\n\n".format(provider_name if provider_name else "Unavailable", provider_contact if provider_contact else "Unavailable", address if address else "Unavailable", quantity if quantity else "Unknown", verified_at)
        provider_details.append(provider_res.replace("-1", "Unknown"))
    return provider_details

def add_city(incoming_msg, coll):
    query_fields = get_query_fields(incoming_msg)
    city_name = query_fields['city'].string_value
    update_dialogflow_entity(city=city_name)
    update_db_entity(coll, city=city_name)
    return city_name

def add_entity(incoming_msg, coll):
    query_fields = get_query_fields(incoming_msg)
    entity_name = query_fields['entity'].string_value
    update_dialogflow_entity(entity=entity_name)
    update_db_entity(coll, entity=entity_name)
    return entity_name