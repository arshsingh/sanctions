import logging
import sys

import click

import test_data_generator
import worker


@click.group()
@click.option(
    '--log-level', help='Log level', default='INFO',
    type=click.Choice(logging._nameToLevel.keys(), case_sensitive=False),
)
def cli(log_level):
    logging.basicConfig(stream=sys.stdout, level=logging._nameToLevel[log_level])


@cli.command()
@click.option('--rows', default=100, type=int, help='Number of test data rows to generate')
def generate_test_data(rows):
    click.echo(f'Generating test data: {rows} rows')
    test_data_generator.generate_sanctions(rows)


@cli.command()
@click.option('--once', is_flag=True, help='Run the worker once')
def start(once):
    worker.start(once)


if __name__ == '__main__':
    cli()
