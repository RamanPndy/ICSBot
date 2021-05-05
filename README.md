# ICSBot
India Covid Support Whatsapp Chatbot

This is an Whatsapp chatbot and provides verified resources from IndiaCovidSupport APIs.

User sends query in whatsapp for eg *hospital in kanpur* and this query will be send to Dialogflow to find entity which is requested and for which city it is requested.
Once dialogflow provides entity and location then bot hits IndiaCovidSupport API to get relavant results and send it again back to whatsapp channel.

Bot is in BETA phase and We are working more to make it more useful and provide more useful resources to needy one.

One can also search verified resources at : https://indiacovidsupport.com/

Any suggesstions and comments are always welcome.

Backend is Python Based Flask framework integrated with Whatsapp via Twillio and Dialogflow for NLP and Firestore for data storage.
