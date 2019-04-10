import datetime
import logging
import posixpath
from xml.etree import ElementTree

from bs4 import BeautifulSoup
import requests

from config import (
    TEAM, KEYWORDS_REQUIRED, LOG_LEVEL, LOG_FORMAT
)

xml_root = 'http://gd2.mlb.com/components/game/mlb/year_{year}/month_{month:02d}/day_{day:02d}/'
xml_file = '{gameday_folder}media/mobile.xml'

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


def get_videos(dt):
    xml_url = get_xml_file(dt)
    if xml_url is None:
        return

    logging.info("Reading %s", xml_url)

    highlights = open_xml(xml_url)
    if highlights is None:
        return False

    videos = []

    for media in highlights.findall('media'):
        if not match_required_keywords(media):
            continue

        mp4_file = media.find("url[@playback-scenario='FLASH_1200K_640X360']").text.replace('1200K', '2500K')
        description = media.find('bigblurb').text

        videos.append((media.get('id'), mp4_file, description))

    return videos