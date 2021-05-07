import time
from datetime import datetime

def current_milli_time():
    return round(time.time() * 1000)

def get_verified_at(filed_at):
    try:
        verifieddt = datetime.strptime(filed_at, '%Y-%m-%dT%H:%M:%S.%f%z')
    except Exception as e:
        print (e)
        verifieddt = datetime.strptime(filed_at, '%Y-%m-%dT%H:%M:%S.%f')
    verified_at = f'{verifieddt:%d/%m/%Y %H:%M:%S}'
    return verified_at

def get_data_from_field(query_fields, field):
    entity = query_fields[field].string_value
    if not entity:
        entity = query_fields[field].list_value.values[0].string_value
    return entity
     
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

def get_entities_and_cities():
    entities = {
        "oxygen cylinder": "Oxygen%20Cylinder", "oxygen": "Oxygen", "oxygen concentrator": "Oxygen Concentrator", 
         "oxygen refilling": "Oxygen%20Refilling",  "oxygen cylinder refilling": "Oxygen%20Refilling", 
         "oxygen bed": "Oxygen Bed", "icu": "ICU", "icu bed": "ICU%20Bed", "medicine": "Medicine", "plasma": "Plasma", 
         "hospital bed": "Hospital%20Bed", "hospital": "Hospital", "food":"Homemade%20Food" , 
         "fabiflu": "Fabiflu", "ambulance": "Ambulance", "cab": "cab"}

    cities = {"kanpur": "Kanpur,%20Uttar%20Pradesh", "varanasi":"Varanasi,%20Uttar%20Pradesh", 
        "banaras":"Varanasi,%20Uttar%20Pradesh", "lucknow": "Lucknow,%20Uttar%20Pradesh", 
        "delhi": "New%20Delhi,%20Delhi", "mumbai": "Mumbai,%20Maharashtra", "bangalore": "Bangalore", 
        "bengaluru": "Bangalore", "kolkata": "Kolkata", "hyderabad": "Hyderabad"}
    return entities, cities