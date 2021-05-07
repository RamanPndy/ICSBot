# ICSBot
India Covid Support Whatsapp Chatbot

This is an Whatsapp chatbot and provides verified resources from IndiaCovidSupport APIs.

User sends query in whatsapp for eg *hospital in kanpur* and this query will be send to Dialogflow to find entity which is requested and for which city it is requested.
Once dialogflow provides entity and location then bot hits IndiaCovidSupport API to get relavant results and send it again back to whatsapp channel.

Bot is in BETA phase and We are working more to make it more useful and provide more useful resources to needy one.

One can also search verified resources at : https://indiacovidsupport.com/

Any suggesstions and comments are always welcome.

Backend is Python Based Flask framework integrated with Whatsapp via Twillio and Dialogflow for NLP and MongoDB for data storage.

To run the application following files are needed:
Firebase Private Key : icsbot-firebase.json<br>
Dialogflow Service Account Key : icsbotsa.json<br>

To build the application run <b>./build.sh</b> which will build the docker image of the application. <br>
To run the application run <b>./run.sh</b> which will run the deploy dockerized application on Heroku. Make sure to set config vars for the Heroku app.
heroku config:set PROJECTID=<dialogflow_project_id>
heroku config:set DBUSER=<mongodb_user>
heroku config:set DBPASS=<mongodb_pass>
heroku config:set PORT=<application_port>
heroku config:set GOOGLE_APPLICATION_CREDENTIALS=icsbotsa.json