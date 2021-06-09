import requests
import json
import logging
import pandas as pd
import config


def connect_to_spotify():
    try:
        logging.info('Attempting to get access token...')
        client_id = config.client_id
        client_secret = config.client_secret

        auth_url = 'https://accounts.spotify.com/api/token'

        auth_response = requests.post(auth_url, {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
        })

        # convert the response to JSON
        auth_response_data = auth_response.json()

        # save the access token
        access_token = auth_response_data['access_token']

        return access_token
    except:
        logging.info('Failure to get access token...')

def get_spotify_songs():

    try:
        logging.info('Calling Spotify API Services...')
        access_token = connect_to_spotify()
        url = "https://api.spotify.com/v1/playlists/5CCLPEfMG0ejXwbOt0cbQB/tracks?market=US"

        payload = {}
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(access_token)
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        parse_json(response.text)
    except:
        logging.info('Spotify API GET Failure')

