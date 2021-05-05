from datetime import datetime

def get_provider_data(provider):
    name = provider.get("name", "")
    provider_name = provider.get("provider_name", "")
    provider_contact = provider.get("provider_contact", "Unavailable")
    quantity = provider.get("quantity", "Unavailable")
    filedAt = provider.get("filedAt", "")
    verfiedAt = ""
    if filedAt:
        try:
            verifieddt = datetime.strptime(filedAt, '%Y-%m-%dT%H:%M:%S.%f%z')
            verfiedAt = f'{verifieddt:%d/%m/%Y %H:%M:%S}'
        except Exception:
            verfiedAt =  filedAt
    provider = ""
    if name:
        provider = name
    elif provider_name:
        provider = provider_name
    elif name and provider_name:
        provider = name + " OR " + provider_name
    return provider, provider_contact.replace("\n", ""), verfiedAt, quantity