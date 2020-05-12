#!/bin/bash
export API_SERVICE_NAME='gmail'
export API_VERSION='v1'
export SCOPES='https://www.googleapis.com/auth/gmail.readonly'
export SESSION_SECRET='bananapuuuudding'

export ENV_NAME='debug'


python -m app
