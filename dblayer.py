import os
import pymongo
import urllib

def get_db_connection():
    db_username = urllib.parse.quote_plus(os.environ.get('DBUSER'))
    db_pass = urllib.parse.quote_plus(os.environ.get('DBPASS'))
    
    client = pymongo.MongoClient("mongodb+srv://{}:{}@cluster0.bsugd.mongodb.net/icsdb?retryWrites=true&w=majority".format(db_username, db_pass))
    db = client.icsdb
    return db

def get_entities_and_cities(collection):
    dbresults = collection.find_one({}, {"_id":0})
    entities = dbresults.get('entities')
    cities = dbresults.get('cities')
    return entities, cities

def get_db_results(ics_collection, entity, location):
    dbresults = ics_collection.find({
        '$and': [
            {'entity': entity},
            {'location': location}
        ]
    })
    dbfiltereddata = []
    for dbr in dbresults:
        dbfiltereddata.append(dbr)
    return dbfiltereddata

def update_db_entity(col, city="", entity=""):
    if city:
        key = "cities.{}".format(city)
        value = city.capitalize()
    else:
        key = "entities.{}".format(entity)
        value = entity.capitalize()
    col.update({'name': "entitiesandcities"}, {'$set': {key: value}})

def update_feed_data_db(coll, entity, location, name, contact_number, address, loc, quantity, filed_at, verifiedby, price):
    provider_dict = {"entity": entity, "location": location, "provider_name": name, "provider_contact": contact_number, "contact": contact_number, "provider_address": address if address else loc, "quantity": quantity if quantity else "Unknown", "filedAt": filed_at, "verifiedby": verifiedby}
    if price:
        provider_dict["price"] = price
    try:
        coll.update_one({"provider_contact": contact_number}, {"$set": provider_dict}, upsert=True)
        success = True
    except Exception as e:
        print(e)
        success = False
    return success

def get_otp_txnid(collection, mobile):
    dbresult = collection.find_one({"mobile": mobile}, {"_id":0})
    return dbresult.get('transactionid')

def get_user_token(collection, mobile):
    dbresult = collection.find_one({"mobile": mobile}, {"_id":0})
    return dbresult.get('token')

db_conn = get_db_connection()
entities, cities = get_entities_and_cities(db_conn.entitiesandcities)