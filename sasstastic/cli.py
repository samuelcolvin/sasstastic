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
DEV_MODE_HELP = 'whether in development mode or production mode, if omitted the value is taken from config'
VERBOSE_HELP = 'Print more details on download and build'
VERSION_HELP = 'Show the version and exit.'


@cli.command()
def build(
    config_path: Path = typer.Argument('sasstastic.yml', exists=True, file_okay=True, dir_okay=True, readable=True),
    output_dir: Optional[Path] = typer.Option(None, file_okay=False, dir_okay=True, readable=True, help=OUTPUT_HELP),
    dev_mode: bool = typer.Option(None, '--dev/--prod', help=DEV_MODE_HELP),
    verbose: bool = typer.Option(False, help=VERBOSE_HELP),
    version: bool = typer.Option(None, '--version', callback=version_callback, is_eager=True, help=VERSION_HELP),
):
    """
    Build sass/scss files to css based on a config file.
    """
    setup_logging('DEBUG' if verbose else 'INFO')
    if config_path.is_dir():
        config_path /= 'sasstastic.yml'
    try:
        main(config_path, output_dir, dev_mode)
    except SasstasticError:
        raise typer.Exit(1)


if __name__ == '__main__':
    cli()
