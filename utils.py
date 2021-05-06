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