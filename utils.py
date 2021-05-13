import time
import re
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
     
def get_numbers_str(mixed_str):
    temp = re.findall(r'\d+', mixed_str)
    return ",".join(temp)