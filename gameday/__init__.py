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
from read_xml import open_xml, get_xml_file, match_required_keywords


slack_client = SlackClient(SLACK_API_TOKEN)

if LOG_LEVEL is None:
    LOG_LEVEL = 'INFO'
if LOG_FORMAT is None:
    LOG_FORMAT = '%(name)s:%(levelname)s %(module)s:%(lineno)d %(asctime)s:  %(message)s'

logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)


def run_day(xml_url, seen_ids):
    highlights = open_xml(xml_url)
    if highlights is None:
        return False
    for media in highlights.findall('media'):
        if media.get('id') in seen_ids.keys():
            continue
        if not match_required_keywords(media):
            continue

        mp4_file = media.find("url[@playback-scenario='FLASH_1200K_640X360']")
        api_resp = slack_client.api_call(
            'chat.postMessage',
            channel=SLACK_CHANNEL,
            # higher quality version if it's there
            text='{}\n{}'.format(media.find('bigblurb').text, mp4_file.text.replace('1200K', '2500K')),
            username=SLACK_USERNAME,
            icon_emoji=SLACK_EMOJI
        )
        logging.info("Posted %s to %s with ts %s", media.get('id'), SLACK_CHANNEL, api_resp['ts'])
        seen_ids[media.get('id')] = api_resp


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

    days_to_check = [
        datetime.datetime.now()-datetime.timedelta(days=days_back)
        for days_back in range(NUM_DAYS_TO_CHECK-1, 0, -1)
    ]

    for dt in days_to_check: 
        if not gameday_state.has_key(dt.date().isoformat()):
            gameday_state[dt.date().isoformat()] = {}
        xml_url = get_xml_file(dt)
        run_day(xml_url, gameday_state[dt.date().isoformat()])

    gameday_state.close()
    logging.info("Done.  Time to run: %s", time.time() - start_time)


if __name__ == '__main__':
    main()
