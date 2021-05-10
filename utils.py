import time
import re
import os
import pymongo
import urllib
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
     
def get_entities_and_cities(collection):
    dbresults = collection.find_one({}, {"_id":0})
    entities = dbresults.get('entities')
    cities = dbresults.get('cities')
    return entities, cities

def get_numbers_str(mixed_str):
    temp = re.findall(r'\d+', mixed_str)
    return ",".join(temp)

def get_db_connection():
    db_username = urllib.parse.quote_plus(os.environ.get('DBUSER'))
    db_pass = urllib.parse.quote_plus(os.environ.get('DBPASS'))
    
    client = pymongo.MongoClient("mongodb+srv://{}:{}@cluster0.bsugd.mongodb.net/icsdb?retryWrites=true&w=majority".format(db_username, db_pass))
    db = client.icsdb
    return db