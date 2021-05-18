import dialogflow
import os
import json
from google.api_core.exceptions import InvalidArgument
from google.protobuf.json_format import MessageToJson

PROJECT_ID = os.environ.get('PROJECTID')
LOCATION_ENTITY_UUID = os.environ.get('LOCATION_ENTITY_UUID')
MEDREQ_ENTITY_UUID = os.environ.get('MEDREQ_ENTITY_UUID')
DIALOGFLOW_LANGUAGE_CODE = 'en'
SESSION_ID = 'me'

def get_dialogflow_response(incoming_msg):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(PROJECT_ID, SESSION_ID)
    text_input = dialogflow.types.TextInput(text=incoming_msg, language_code=DIALOGFLOW_LANGUAGE_CODE)
    query_input = dialogflow.types.QueryInput(text=text_input)
    try:
        response = session_client.detect_intent(session=session, query_input=query_input)
    except InvalidArgument:
        raise
    return response

def update_dialogflow_entity(city="", entity=""):
    entity_type_client = dialogflow.EntityTypesClient()
    if city:
        entity_parent = entity_type_client.entity_type_path(PROJECT_ID, LOCATION_ENTITY_UUID)
        entity_to_update = dialogflow.types.EntityType.Entity(
            value = city,
            synonyms = [city]
        )
        response = entity_type_client.batch_update_entities(entity_parent, [entity_to_update])
    else:
        entity_parent = entity_type_client.entity_type_path(PROJECT_ID, MEDREQ_ENTITY_UUID)
        entity_to_update = dialogflow.types.EntityType.Entity(
            value = entity,
            synonyms = [entity]
        )
        response = entity_type_client.batch_update_entities(entity_parent, [entity_to_update])

def get_dialogflow_context_parameters(query_result, context_name):
    query_parameters = {}
    for context in query_result.output_contexts:
        if context_name in context.name:
            query_parameters = context.parameters
            break
    if query_parameters:
        context_params = json.loads(MessageToJson(query_parameters))
        return context_params