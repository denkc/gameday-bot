import datetime
import logging
import shelve
import time

from slackclient import SlackClient

from config import (
    TEAM, KEYWORDS_REQUIRED, NUM_DAYS_TO_CHECK, MESSAGE_AGE_THRESHOLD_DAYS,
    SLACK_API_TOKEN, SLACK_USERNAME, SLACK_EMOJI, SLACK_CHANNEL,
    STATE_FILE, LOG_LEVEL, LOG_FORMAT
)
from read_json import get_videos

slack_client = SlackClient(SLACK_API_TOKEN)

if LOG_LEVEL is None:
    LOG_LEVEL = 'INFO'
if LOG_FORMAT is None:
    LOG_FORMAT = '%(name)s:%(levelname)s %(module)s:%(lineno)d %(asctime)s:  %(message)s'

logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)


def run_day(dt, seen_ids):
    videos = get_videos(dt)

    for video_id, video_link, video_desc in videos:
        if video_id in seen_ids.keys():
            continue

        api_resp = slack_client.api_call(
            'chat.postMessage',
            channel=SLACK_CHANNEL,
            # higher quality version if it's there
            text='{}\n{}'.format(video_desc.encode('utf-8'), video_link),
            username=SLACK_USERNAME,
            icon_emoji=SLACK_EMOJI
        )
        logging.info("Posted %s to %s with ts %s", video_id, SLACK_CHANNEL, api_resp['ts'])
        seen_ids[video_id] = api_resp


def main():
    gameday_state = shelve.open(STATE_FILE, writeback=True)

    # cleanup
    for seen_id_date, seen_ids in gameday_state.items():
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=MESSAGE_AGE_THRESHOLD_DAYS)
        if datetime.datetime.strptime(seen_id_date, '%Y-%m-%d') < cutoff_date:
            for seen_id, api_resp in seen_ids.items():
                slack_client.api_call(
                    'chat.delete',
                    channel=api_resp['channel'],
                    ts=api_resp['ts']
                )
            del gameday_state[seen_id_date]

    start_time = time.time()
    start_date = datetime.datetime.now()
    # start_date = datetime.datetime(2019, 7, 12)

    days_to_check = [
        start_date-datetime.timedelta(days=days_back-1)
        for days_back in range(NUM_DAYS_TO_CHECK, 0, -1)
    ]

    for dt in days_to_check: 
        if not gameday_state.has_key(dt.date().isoformat()):
            gameday_state[dt.date().isoformat()] = {}
        run_day(dt, gameday_state[dt.date().isoformat()])

    gameday_state.close()
    logging.info("Done.  Time to run: %s", time.time() - start_time)


if __name__ == '__main__':
    main()
