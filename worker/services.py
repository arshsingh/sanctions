import logging
import os
from typing import Callable

import requests
import xmltodict
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from db import Sanction


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
    before_sleep=before_sleep_log(logging.getLogger(), logging.WARNING),
)
def _fetch(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r


def _eu_entry_to_db_fields(entry) -> Sanction:
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
        'source_id': entry['@euReferenceNumber'],
        'target_type': target_types[entry['subjectType']['@code']],
        'names': list(filter(None, {a['@wholeName'] for a in aliases})),
        'positions': list(filter(None, {a['@function'] for a in aliases})),
        'listed_on': entry['regulation']['@publicationDate'],
        'remarks': entry.get('remark'),
    }


def _unsc_entry_to_db_fields(entry, target_type) -> Sanction:
    """
    Transform UNSC entry data to the dict representation of sanction DB row
    """
    assert target_type in ('individual', 'entity')

    # get all the names
    names = [entry.get('NAME_ORIGINAL_SCRIPT')]
    names.append(' '.join(
        filter(None, (
            entry.get('FIRST_NAME'), entry.get('SECOND_NAME'),
            entry.get('THIRD_NAME'), entry.get('FOURTH_NAME')
        ))
    ))

    aliases = entry.get(f'{target_type.upper()}_ALIAS', [])
    if isinstance(aliases, dict):  # xmltodict returns dict if there is only one alias
        aliases = [aliases]

    for alias in aliases:
        names.append(alias['ALIAS_NAME'])

    names = list(filter(None, names))

    # positions
    positions = entry.get('DESIGNATION', [])
    if isinstance(positions, dict):
        positions = [positions]

    positions = [p['VALUE'] for p in positions]

    return {
        'source_id': entry['REFERENCE_NUMBER'],
        'target_type': target_type,
        'names': names,
        'positions': positions,
        'remarks': entry.get('COMMENTS1'),
        'listed_on': entry.get('LISTED_ON')[:10],
    }


def _ofac_entry_to_db_fields(entry) -> Sanction:
    """
    Transform OFAC entry data to the dict representation of sanction DB row
    """
    names = []
    aliases = entry.get('akaList', {}).get('aka', [])
    if isinstance(aliases, dict):
        aliases = [aliases]

    # get names from aliases as well as the primary name from entry
    for alias in (aliases + [entry]):
        names.append(' '.join(
            filter(None, (alias.get('firstName'), alias.get('lastName')))
        ))

    return {
        'source_id': entry['uid'],
        'target_type': entry['sdnType'].lower(),
        'names': names,
        'positions': list(filter(None, map(str.strip, entry.get('title', '').split(';')))),
        'remarks': entry.get('remarks'),
        'listed_on': None,
    }


def fetch_eu_data() -> list[Sanction]:
    """Fetch data from EU Financial Sanctions File."""
    token = os.getenv('EU_SERVICES_TOKEN', '')
    if not token:
        raise RuntimeError('EU_SERVICES_TOKEN is not set')

    logging.info('starting EU data sync')

    r = _fetch(
        'https://webgate.ec.europa.eu/fsd/fsf/public/files/'
        f'xmlFullSanctionsList_1_1/content?token={token}'
    )
    return [
        _eu_entry_to_db_fields(e)
        for e in xmltodict.parse(r.text)['export']['sanctionEntity']
    ]


def fetch_unsc_data() -> list[Sanction]:
    logging.info('starting UNSC data sync')

    r = _fetch('https://scsanctions.un.org/resources/xml/en/consolidated.xml')

    data = xmltodict.parse(r.text)['CONSOLIDATED_LIST']

    rows = [_unsc_entry_to_db_fields(e, 'individual') for e in data['INDIVIDUALS']['INDIVIDUAL']]
    rows += [_unsc_entry_to_db_fields(e, 'entity') for e in data['ENTITIES']['ENTITY']]
    return rows


def fetch_ofac_data() -> list[Sanction]:
    logging.info('starting OFAC data sync')

    r = _fetch(
        'https://sanctionslistservice.ofac.treas.gov/api/publicationpreview/exports/sdn.xml'
    )

    data = xmltodict.parse(r.text)['sdnList']
    return [_ofac_entry_to_db_fields(e) for e in data['sdnEntry']]


SOURCES: dict[str, Callable[[], list[Sanction]]] = {
    'ofac': fetch_ofac_data,
    'unsc': fetch_unsc_data,
    'eu':   fetch_eu_data,
}
