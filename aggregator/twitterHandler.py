import json
import twitter
import asyncio
from pprint import pprint
from .Twit import Twit
from .config import c_key, c_secret, at_key, at_secret, update_delay
from .databaseManager import Session, engine, subs_table
from logging import getLogger

logger = getLogger("aggregator.twitterHandler")
# Credentials are stored in the config file
api = twitter.Api(consumer_key=c_key, consumer_secret=c_secret, access_token_key=at_key, access_token_secret=at_secret)
session = Session()

def strip_status(status: twitter.models.Status):
    stat_d = status.AsDict()
    return (
        stat_d['id'],
        stat_d['created_at'],
        stat_d['user']['screen_name'],
        stat_d['text']
    )

def get_timeline(users):
    global_timeline = []

    for name in users:
        try:
            new_timeline = api.GetUserTimeline(screen_name=name)
            global_timeline.extend(new_timeline)
        except twitter.error.TwitterError as e:
            try:
                if e.args[0][0]['code'] == 34:
                    logger.error("No such user!!!")
            except Exception as e:
                logger.exception(e)

    global_timeline.sort(key=lambda x: x.created_at_in_seconds)
    # status.created_at_in_seconds - returns utc timestamp
    logger.debug("Global timeline %s" % global_timeline)
    global_timeline = [Twit(strip_status(status)) for status in global_timeline]
    return global_timeline

async def update_db(users):
    timeline = get_timeline(users)
    logger.debug("Twit list %s" % timeline)
    for twit in timeline:
        old_tw = session.query(Twit).filter(Twit.id == twit.id).one_or_none()
        if not old_tw:
            logger.debug("New twit")
            session.add(twit)
        else:
            logger.debug("Duplicate twit")
    session.commit()

async def keep_twits_updated():
    while True:
        subs = [res[0] for res in engine.execute(subs_table.select()).fetchall()]
        logger.debug("Tracking %s" % str(subs))
        logger.info("New update")
        await update_db(subs)
        logger.info("Waiting %d seconds" % update_delay)
        await asyncio.sleep(update_delay)

if __name__ == '__main__':
    pprint(get_timeline(""))
