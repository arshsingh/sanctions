import random
from collections import defaultdict

from faker import Faker

from db import Sanction, create_sanctions


fake = Faker([
    'en_US', 'en_CA', 'ru_RU', 'de_DE', 'ko_KR',
    'ja_JP', 'zh_CN', 'fa_IR',
])


def generate_sanctions(rows=100):
    by_source: dict[str, list[Sanction]] = defaultdict(list)

    for _ in range(rows):
        source = random.choice(['eu', 'unsc', 'ofac'])
        by_source[source].append({
            'source_id': fake.swift8(),
            'target_type': random.choice(['individual', 'vessel', 'aircraft', 'entity']),
            'names': [fake.name() for _ in range(random.randint(1, 4))],
            'positions': [fake.job() for _ in range(random.randint(0, 3))],
            'listed_on': fake.date(),
            'remarks': fake.text(),
        })

    for source, entries in by_source.items():
        create_sanctions(source, entries)


if __name__ == '__main__':
    generate_sanctions()
