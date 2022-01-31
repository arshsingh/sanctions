import os

import logging
import requests
import xmltodict

from db import create_sanctions


def _eu_entry_to_db_fields(entry):
    """
    Transform EU entry data to the dict representation of sanction DB row
    """
    target_types = {
        'person': 'individual',
        'enterprise': 'entity',
    }

    aliases = entry['nameAlias']
    if isinstance(aliases, dict):
        aliases = [aliases]

    return {
        'source': 'eu',
        'source_id': entry['@euReferenceNumber'],
        'target_type': target_types[entry['subjectType']['@code']],
        'names': list(filter(None, {a['@wholeName'] for a in aliases})),
        'positions': list(filter(None, {a['@function'] for a in aliases})),
        'listed_on': entry['regulation']['@publicationDate'],
        'remarks': entry.get('remark'),
    }


def fetch_eu_data():
    """
    Fetch data from EU Financial Sanctions File
    """
    token = os.getenv('EU_SERVICES_TOKEN', '')
    if not token:
        logging.error('EU services token not defined. Skipping EU FSF data fetch')
        return

    logging.info('starting EU data sync')

    r = requests.get(
        'https://webgate.ec.europa.eu/europeaid/fsd/fsf/public/files/'
        f'xmlFullSanctionsList_1_1/content?token={token}'
    )
    if r.status_code != 200:
        logging.error(f'EU data fetch failed with status: {r.status_code}')
        return

    entries = [
        _eu_entry_to_db_fields(e)
        for e in xmltodict.parse(r.text)['export']['sanctionEntity']
    ]
    create_sanctions(entries)