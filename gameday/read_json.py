import datetime
import logging
import json
import requests

from config import (
    TEAM, LOG_LEVEL, LOG_FORMAT
)

if LOG_LEVEL is None:
    LOG_LEVEL = 'INFO'
if LOG_FORMAT is None:
    LOG_FORMAT = '%(name)s:%(levelname)s %(module)s:%(lineno)d %(asctime)s:  %(message)s'

logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)


def get_game_ids(dt):
    # https://statsapi.mlb.com/api/v1/schedule?language=en&sportId=1&date=04/07/2019
    games_url = "https://statsapi.mlb.com/api/v1/schedule?language=en&sportId=1&date={}"
    resp = requests.get(games_url.format(dt.strftime("%m/%d/%Y")))
    games = json.loads(resp.content)

    game_ids = []
    for game in games['dates'][0]['games']:
        if game['teams']['away']['team']['id'] == TEAM or game['teams']['home']['team']['id'] == TEAM:
            game_ids.append(game['gamePk'])
            continue

    return game_ids

def get_game_highlights(game_id):
    # rather than hit the schedule endpoint asking it to hydrate a bunch of games we don't care about
    # hit the endpoint for the specific game id we want
    game_url = "https://statsapi.mlb.com/api/v1/game/{}/content"

    game_data = json.loads(requests.get(game_url.format(game_id)).content)

    highlights = []

    for highlight in game_data['highlights']['highlights']['items']:
        if highlight['type'] != "video":
            continue
        for highlight_playback in highlight['playbacks']:
            if highlight_playback['name'] == 'mp4Avc':
                highlights.append((highlight['mediaPlaybackId'], highlight_playback['url'], highlight['description']))
                break

    return highlights

def get_videos(dt):
    game_ids = get_game_ids(dt)
    if not game_ids:
        return []

    logging.info("Reading %s", game_ids)

    videos = []

    for game_id in game_ids:
        videos += get_game_highlights(game_id)

    return videos
