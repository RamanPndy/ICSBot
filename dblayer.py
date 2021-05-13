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