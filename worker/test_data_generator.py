import random

from faker import Faker

from db import create_sanctions


fake = Faker([
    'en_US', 'en_CA', 'ru_RU', 'de_DE', 'ko_KR',
    'ja_JP', 'zh_CN', 'fa_IR',
])


def generate_sanctions(rows=100):
    entries = []
    for i in range(1, rows):
        entries.append(
            {
                'source': random.choice(['eu', 'unsc', 'ofac']),
                'source_id': fake.swift8(),
                'target_type': random.choice(['individual', 'vessel', 'aircraft', 'entity']),
                'names': [fake.name() for _ in range(random.randint(1, 4))],
                'positions': [fake.job() for _ in range(random.randint(0, 3))],
                'listed_on': fake.date(),
                'created_at': fake.date_time(),
                'remarks': fake.text(),
            }
        )

    create_sanctions(entries)


if __name__ == '__main__':
    generate_sanctions()
