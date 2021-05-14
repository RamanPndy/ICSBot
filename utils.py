import time
import re
from datetime import datetime

def get_help_text(is_telegram=False):
    if is_telegram:
        help_text = "Type /query <query> for example: /query hospital in kanpur to get relavant results.\n\nType /feed <query> to feed data. eg; /feed 10 oxygen bed provided by smart care hospital available at swaroop nagar kanpur contact at <provider-contact-number> verified by <verifier-contact-number>.\n\nType /add <message> to add city or entity eg; /add city kanpur\n\n\nDeveloped by : Raman Pandey"
    else:
        help_text = "Type <query> for example: hospital in kanpur to get relavant results.\n\nType <query> to feed data. just put feed before your query. eg; feed 10 oxygen bed provided by smart care hospital available at swaroop nagar kanpur contact at <provider-contact-number> verified by <verifier-contact-number>.\n\nType add <message> to add city or entity eg; add city kanpur\n\n\nDeveloped by : Raman Pandey"
    return help_text

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
     
def get_numbers_str(mixed_str):
    temp = re.findall(r'\d+', mixed_str)
    return ",".join(temp)