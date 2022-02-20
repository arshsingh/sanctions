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


def _unsc_entry_to_db_fields(entry, target_type):
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
        'source': 'unsc',
        'source_id': entry['REFERENCE_NUMBER'],
        'target_type': target_type,
        'names': names,
        'positions': positions,
        'remarks': entry.get('COMMENTS1'),
        'listed_on': entry.get('LISTED_ON')[:10],
    }


def _ofac_entry_to_db_fields(entry):
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
        'source': 'ofac',
        'source_id': entry['uid'],
        'target_type': entry['sdnType'].lower(),
        'names': names,
        'positions': list(filter(None, map(str.strip, entry.get('title', '').split(';')))),
        'remarks': entry.get('remarks'),
        'listed_on': None,
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


def fetch_unsc_data():
    logging.info('starting UNSC data sync')

    r = requests.get('https://scsanctions.un.org/resources/xml/en/consolidated.xml')
    if r.status_code != 200:
        logging.error(f'UNSC data fetch failed with status: {r.status_code}')
        return

    data = xmltodict.parse(r.text)['CONSOLIDATED_LIST']

    individuals = [_unsc_entry_to_db_fields(e, 'individual') for e in data['INDIVIDUALS']['INDIVIDUAL']]
    create_sanctions(individuals)

    entities = [_unsc_entry_to_db_fields(e, 'entity') for e in data['ENTITIES']['ENTITY']]
    create_sanctions(entities)


def fetch_ofac_data():
    logging.info('starting OFAC data sync')

    r = requests.get('https://www.treasury.gov/ofac/downloads/sdn.xml')
    if r.status_code != 200:
        logging.error(f'OFAC data fetch failed with status: {r.status_code}')
        return

    data = xmltodict.parse(r.text)['sdnList']

    entities = [_ofac_entry_to_db_fields(e) for e in data['sdnEntry']]
    create_sanctions(entities)
