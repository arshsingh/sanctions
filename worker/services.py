import logging
import os
from itertools import product
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


def _seco_as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _seco_xml_text(value):
    if isinstance(value, dict):
        return value.get('#text')
    return value


def _seco_name_to_strings(name) -> list[str]:
    """Build complete names from SECO name parts and spelling variants."""
    parts = _seco_as_list(name['name-part'])
    parts = [
        part for _, part in sorted(
            enumerate(parts),
            key=lambda item: int(item[1].get('@order', item[0] + 1)),
        )
    ]

    names = [
        ' '.join(filter(None, (_seco_xml_text(p.get('value')) for p in parts)))
    ]

    variant_keys = []
    for part in parts:
        for variant in _seco_as_list(part.get('spelling-variant')):
            key = (variant.get('@lang'), variant.get('@script'))
            if key not in variant_keys:
                variant_keys.append(key)

    for key in variant_keys:
        values_by_part = []
        for part in parts:
            variants = [
                _seco_xml_text(variant)
                for variant in _seco_as_list(part.get('spelling-variant'))
                if (variant.get('@lang'), variant.get('@script')) == key
            ]
            values_by_part.append(
                list(filter(None, variants))
                or [_seco_xml_text(part.get('value'))]
            )

        names.extend(
            ' '.join(filter(None, values))
            for values in product(*values_by_part)
        )

    return list(filter(None, dict.fromkeys(names)))


def _seco_entry_to_db_fields(entry) -> Sanction:
    if 'individual' in entry:
        target_type = 'individual'
        target = entry['individual']
    elif 'entity' in entry:
        target_type = 'entity'
        target = entry['entity']
    else:
        target = entry['object']
        target_type = target['@object-type']
        if target_type not in ('aircraft', 'vessel'):
            raise ValueError(f'unsupported SECO object type: {target_type}')

    names = []
    for identity in _seco_as_list(target['identity']):
        for name in _seco_as_list(identity['name']):
            names.extend(_seco_name_to_strings(name))

    remarks = []
    for field in ('justification', 'other-information'):
        remarks.extend(
            filter(None, map(_seco_xml_text, _seco_as_list(target.get(field))))
        )

    modifications = _seco_as_list(entry.get('modification'))
    listed = next(
        (m for m in modifications if m['@modification-type'] == 'listed'),
        {},
    )

    return {
        'source_id': entry['@ssid'],
        'target_type': target_type,
        'names': list(dict.fromkeys(names)),
        'positions': [],
        'remarks': '\n'.join(dict.fromkeys(remarks)) or None,
        'listed_on': (
            listed.get('@effective-date')
            or listed.get('@publication-date')
            or listed.get('@enactment-date')
        ),
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


def fetch_seco_data() -> list[Sanction]:
    """Fetch the Swiss SECO consolidated sanctions list."""
    logging.info('starting SECO data sync')

    r = _fetch(
        'https://www.sesam.search.admin.ch/sesam-search-web/pages/'
        'downloadXmlGesamtliste.xhtml?lang=en&action=downloadXmlGesamtlisteAction'
    )

    data = xmltodict.parse(r.text)['swiss-sanctions-list']
    if data.get('@list-type') != 'whole-list':
        raise ValueError('SECO response is not a consolidated whole list')

    targets = _seco_as_list(data.get('target'))
    if not targets:
        raise ValueError('SECO response contains no targets')

    return [
        _seco_entry_to_db_fields(target)
        for target in targets
        if not any(
            modification['@modification-type'] == 'de-listed'
            for modification in _seco_as_list(target.get('modification'))
        )
    ]


SOURCES: dict[str, Callable[[], list[Sanction]]] = {
    'ofac': fetch_ofac_data,
    'unsc': fetch_unsc_data,
    'eu':   fetch_eu_data,
    'seco': fetch_seco_data,
}
