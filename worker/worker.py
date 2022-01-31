import argparse
import logging
import time

import schedule

from services import fetch_eu_data


def sync_data():
    logging.info('staring data sync')

    fetch_eu_data()


def start(once=False):
    if once:
        sync_data()
        return

    logging.info('staring worker')

    schedule.every().day.at('00:00').do(sync_data)

    while True:
        schedule.run_pending()
        time.sleep(1)