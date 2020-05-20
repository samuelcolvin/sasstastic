import logging
from pathlib import Path
from typing import Optional

from .build import build
from .download import download
from .models import load_config

logger = logging.getLogger('sasstastic.main')


def main(config_file: Path, alt_output_dir: Optional[Path], dev_mode: Optional[bool]):
    config = load_config(config_file)
    config.output_dir = alt_output_dir or config.output_dir
    if dev_mode is not None:
        config.dev_mode = dev_mode
    logger.info('building using %s config file, output directory: %s', config_file, config.output_dir)
    download(config.download)

    build(config)
