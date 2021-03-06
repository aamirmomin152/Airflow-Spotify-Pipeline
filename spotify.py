import requests
import json
import logging
import pandas as pd
import config

# The Snowflake Connector library.
import snowflake.connector as snow
from snowflake.connector.pandas_tools import write_pandas

#Airflow dependencies
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.contrib.operators.snowflake_operator import SnowflakeOperator
from airflow import DAG



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

def parse_json(text):

    try:
        spotify_data = json.loads(text)

        data = []
        for item in spotify_data["items"]:
            current_row = []
            current_row.append(item["added_at"])
            current_row.append(item["track"]["album"].get("name"))
            current_row.append(item["track"].get("name"))
            current_row.append(item["track"].get("duration_ms"))

            artist = ''
            for artist in item["track"]["album"]["artists"]:
                artist = artist["name"] + ''
            current_row.append(artist)
            data.append(current_row)

        df = pd.DataFrame(
            data, columns=['ADDED_AT', 'ALBUM_NAME', 'SONG_NAME', 'DURATION_MILLISECONDS', 'ARTISTS'])

        write_to_snowflake(df)
    except:
        logging.info('Failure parsing through API JSON response')

def write_to_snowflake(df):
    try:
        logging.info('Attemping to connect and write to Snowflake')
        conn = snow.connect(user=config.user,
                            password=config.password,
                            account=config.account,
                            warehouse=config.warehouse,
                            database=config.database,
                            schema=config.schema)

        write_pandas(conn, df, "SPOTIFYPLAYLIST")

        cur = conn.cursor()

        # Execute a statement that will turn the warehouse off.
        sql = "ALTER WAREHOUSE COMPUTE_WH SUSPEND"
        cur.execute(sql)

        # Close your cursor and your connection.
        cur.close()
        conn.close()
    except:
        logging.info('Failure connecting to or writing to Snowflake')

default_args = {
    'owner': 'me',
    'start_date': dt.datetime(2017, 6, 1),
    'retries': 0,
    'retry_delay': dt.timedelta(minutes=5),
}


with DAG('spotify-pipeline',
         default_args=default_args,
         schedule_interval=None,
         ) as dag:
    # Get songs and data, parse through it, write to snowflake, then run a snowflake operator to take data to transformaed schema using Airflow DAG
    sqlstring = 'CREATE OR REPLACE TABLE "DEMO_DB"."PUBLIC"."TRANSFORMEDSPOTIFYPLAYLIST" AS SELECT TO_DATE(ADDED_AT) AS ADDED_DATE, SONG_NAME, CAST(DURATION_MILLISECONDS AS int) / 60000 AS DURATION_MINUTES, ARTISTS FROM "DEMO_DB"."PUBLIC"."SPOTIFYPLAYLIST"'
    curate_snowflake_data = SnowflakeOperator(
        task_id='curate_snowflake_data',
        sql=sqlstring,
        snowflake_conn_id="snowflake_conn"
    )

    get_spotify_songs = PythonOperator(task_id='get_spotify_songs',
                                       python_callable=get_spotify_songs)

    sleep = BashOperator(task_id='sleep',
                         bash_command='sleep 5')

get_spotify_songs >> sleep >> curate_snowflake_data