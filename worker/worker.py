import logging
import time

import schedule

from db import create_sanctions, update_source_status
from services import SOURCES


def sync_data():
    logging.info('starting data sync')

    for name, fetch in SOURCES.items():
        try:
            create_sanctions(name, fetch())
            update_source_status(name)
        except Exception:
            logging.exception('%s sync failed', name)


def start(once=False):
    if once:
        sync_data()
        return

    logging.info('starting worker')

    schedule.every().day.at('00:00').do(sync_data)

    while True:
        schedule.run_pending()
        time.sleep(1)
