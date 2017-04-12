import datetime
import logging
import posixpath
import shelve
import time
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from slackclient import SlackClient
import requests

from config import (
    TEAM, KEYWORDS_REQUIRED, MESSAGE_AGE_THRESHOLD_DAYS,
    SLACK_API_TOKEN, SLACK_USERNAME, SLACK_EMOJI, SLACK_CHANNEL,
    STATE_FILE, LOG_LEVEL, LOG_FORMAT
)

xml_root = 'http://gd2.mlb.com/components/game/mlb/year_{year}/month_{month:02d}/day_{day:02d}/'
xml_file = '{gameday_folder}media/mobile.xml'

slack_client = SlackClient(SLACK_API_TOKEN)

if LOG_LEVEL is None:
    LOG_LEVEL = 'INFO'
if LOG_FORMAT is None:
    LOG_FORMAT = '%(name)s:%(levelname)s %(module)s:%(lineno)d %(asctime)s:  %(message)s'

logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)


def get_xml_file(date=None):
    if date is None:
        date = datetime.datetime.now()

    day_folder = xml_root.format(year=date.year, month=date.month, day=date.day)
    resp = requests.get(day_folder)
    page_content = BeautifulSoup(resp.content, 'html.parser')

    for anchor in page_content.find_all('a'):
        link = anchor.get('href')
        if link.startswith('gid') and TEAM in link:
            game = link
            break
    else:
        return None

    return posixpath.join(day_folder, xml_file.format(gameday_folder=game))


def open_xml(xml_url):
    xml = requests.get(xml_url)
    if xml.status_code == 404:
        logging.info("Game XML not found; game has no highlights yet")
        return None
    return ElementTree.fromstring(xml.content)


def match_required_keywords(media):
    # provide the root media XML element
    if not KEYWORDS_REQUIRED:
        return True

    keywords = media.find('keywords')
    for keyword_type, keyword_value in KEYWORDS_REQUIRED.items():
        type = keywords.find("keyword[@type='{keyword_type}']".format(
            keyword_type=keyword_type,
        ))
        if type is None or type.get('value') != keyword_value:
            return False

    return True


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
    if not gameday_state:
        gameday_state = {}

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

    if not gameday_state.has_key(datetime.date.today().isoformat()):
        gameday_state[datetime.date.today().isoformat()] = {}

    start_time = time.time()

    xml_url = get_xml_file()
    run_day(xml_url, gameday_state[datetime.date.today().isoformat()])
    logging.info("Done.  Time to run: %s", time.time() - start_time)


if __name__ == '__main__':
    main()
