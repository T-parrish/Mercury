# Mercury
### What is this?
This project spins up a Sanic webserver and exposes endpoints for interacting with Gmail data. Most notably, it enables you to scrape your entire Gmail history and store it in your very own Postgres container with some NLP magic already baked in.

### Who is this for?
* People interested in analyzing their email communication history
* Anybody who wants to generate a large, clean NLP dataset to mess around with
* Somebody who is tired of spam in their inbox, and is interested in a novel approach to filter it out

### Is this production ready?
No! But it could be with some extra help.

## Setup:
#### Spin up Postgres with Docker
```
docker-compose build
docker-compose up
```

Once the docker container is up and running, you can shell into it with the following:

``` 
docker ps -a  # gets the list of active docker containers
docker exec -it <pg_container_id> bash 
```

To interact with the Postgres data once you have a bash shell:
```
psql -U postgres
\l  # lists databases
\c  # connects to database
\dt  # lists database tables
```

#### Fire up Sanic
From the project root:
``` make run-dev ``` will spin an instance of a Sanic webserver into existence with default dev config. If this doesn't work, you might need to ``` chmod +x env/dev.sh ``` to make the startup shell script executable and properly set environment variables.


#### Get your Gcloud credentials and secrets
[Go to your google cloud console](https://console.cloud.google.com/home/dashboard?project=hermes-275017)

From the sidebar, select "APIs & Services", then credentials. There should be an option towards the top to "+Create Credentials". Click on this and select the option to generate an "Oauth Client ID". 

From the menu to create an OAuth Client ID, select 'Web Application', give it a name, and set the restrictions to the following:
##### Authorized Javascript Origins:
```
http://localhost:5000
http://localhost
http://127.0.0.1:5000
https://localhost:5000
```

##### Authorized redirect URIs
```
http://localhost:5000
http://localhost:5000/oauth2callback
https://localhost:5000/oauth2callback
```

This should take you back to the Credentials page where you'll have a new entry under OAuth 2.0 Client IDs. Go ahead and mouse over it and click the download button to grab a json file with your secrets and credentials for interacting with Google APIs.

Before Sanic is able to do much of anything, make sure to save that client_secret.json file you just downloaded to the app/config folder of this project. 



#### Modifying or updating the Table Schemas
This project uses Alembic and is configured for auto-generating migrations. Sometimes this doesn't work; if your migrations get borked to beyond recognition, make sure to save the ```app/migrations/env.py``` file before wiping the folder. There was a lot of trial and error in getting Alembic to play with Sanic and AsyncPG; that env file is what I've gotten to work most consistently.

If you do find it necessary to wipe the migrations folder, (no shame, I've had to do it a bunch), copy the ```app/migrations/env.py``` file someplace safe, wipe the directory, then swap the copied version back in once you've re-initialized Alembic with ```alembic --init```. You may need to do some cleanup of the DB in Postgres before Alembic stops complaining about DB migration state, but I'll leave that exercise to the reader.

Under most normal circumstances, Alembic should work quite well:
```
make alembic-revisions  # auto-generates migration file
make migrate  # migrates DB to most recent revision
make downgrade  # reverts DB to previous revision
```

## Basic Usage
Once you've saved the client_secret.json file into app/config, you should be able to authenticate with Google and retrieve your OAuth credentials.

```http://localhost:5000/authorize``` will take you through the Oauth2 flow and save the credentials in a Redis Session which will then allow you to make requests to the Gmail api. The app was originally configured to accept a JWT minted by a separate service, so many of the routes are currently being re-worked to use a more encapsulated authentication strategy and are in various states of (dis)functionality.

## Wish List / ToDo
- [ ] Roll basic encapsulated auth strategy (in progress)
- [ ] Add hooks for other auth strategies
- [ ] Refactor the comm_node -> graph_node process
- [ ] Template routes to serve pages with D3.js
- [ ] Better launch script
- [ ] Containerized Sanic
