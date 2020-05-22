import logging
from pathlib import Path
from typing import Optional

import typer

from .config import SasstasticError, load_config
from .logs import setup_logging
from .main import download_and_compile, watch
from .version import VERSION

cli = typer.Typer()
logger = logging.getLogger('sasstastic.cli')


def version_callback(value: bool):
    if value:
        print(f'sasstastic: v{VERSION}')
        raise typer.Exit()


OUTPUT_HELP = 'Custom directory to output css files, if omitted the "output_dir" field from the config file is used.'
DEV_MODE_HELP = 'Whether to compile in development or production mode, if omitted the value is taken from config.'
WATCH_HELP = 'Whether to watch the config file and build directory and re-compile on file changes.'
VERBOSE_HELP = 'Print more information to the console.'
VERSION_HELP = 'Show the version and exit.'


@cli.command()
def build(
    config_path: Path = typer.Argument('sasstastic.yml', exists=True, file_okay=True, dir_okay=True, readable=True),
    output_dir: Optional[Path] = typer.Option(
        None, '-o', '--output-dir', file_okay=False, dir_okay=True, readable=True, help=OUTPUT_HELP
    ),
    dev_mode: bool = typer.Option(None, '--dev/--prod', help=DEV_MODE_HELP),
    watch_mode: bool = typer.Option(False, '--watch/-dont-watch', help=WATCH_HELP),
    verbose: bool = typer.Option(False, help=VERBOSE_HELP),
    version: bool = typer.Option(None, '--version', callback=version_callback, is_eager=True, help=VERSION_HELP),
):
    """
    Fantastic SASS and SCSS compilation.

    Takes a single argument: a path to a sasstastic.yml config file, or a directory containing a sasstastic.yml file.
    """
    setup_logging('DEBUG' if verbose else 'INFO')
    if config_path.is_dir():
        config_path /= 'sasstastic.yml'
    logger.info('config path: %s', config_path)
    try:
        config = load_config(config_path)
        if watch_mode:
            watch(config, output_dir, dev_mode)
        else:
            download_and_compile(config, output_dir, dev_mode)
    except SasstasticError:
        raise typer.Exit(1)


if __name__ == '__main__':
    cli()
