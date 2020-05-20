import logging
from pathlib import Path
from typing import Optional

import typer

from .logs import setup_logging
from .main import main
from .models import SasstasticError
from .version import VERSION

cli = typer.Typer()
logger = logging.getLogger('sasstastic.cli')


def version_callback(value: bool):
    if value:
        print(f'sasstastic: v{VERSION}')
        raise typer.Exit()


OUTPUT_HELP = 'Custom directory to output css files, if omitted the "output_dir" field from the config file is used.'
VERSION_HELP = 'Show the version and exit.'


@cli.command()
def build(
    config_path: Path = typer.Argument('sasstastic.yml', exists=True, file_okay=True, dir_okay=True, readable=True),
    output_dir: Optional[Path] = typer.Option(None, file_okay=False, dir_okay=True, readable=True, help=OUTPUT_HELP),
    version: bool = typer.Option(None, '--version', callback=version_callback, is_eager=True, help=VERSION_HELP),
):
    """
    Build sass/scss files to css based on a config file.
    """
    setup_logging('INFO')
    if config_path.is_dir():
        config_path /= 'sasstastic.yml'

    try:
        main(config_path, output_dir)
    except SasstasticError:
        raise typer.Exit(1)


if __name__ == '__main__':
    cli()
