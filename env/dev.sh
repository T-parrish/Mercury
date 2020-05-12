#!/bin/bash
export API_SERVICE_NAME='gmail'
export API_VERSION='v1'
export SCOPES='https://www.googleapis.com/auth/gmail.readonly'
export SESSION_SECRET='bananapuuuudding'
export DATABASE_URL="postgresql://postgres:rofl-copters@localhost/hermes"
export REDIS_URL='redis://localhost'
export ACCESS_TOKEN_NAME="jwtToken"
export CLIENT_SECRETS_FILE="app/config/client_secret.json"
export JWT_SECRET="SupaSekretSauce"
export BCRYPT_SALT="Salty-Snax"

export ENV_NAME='dev'

python -m app
