import logging
from pathlib import Path
from typing import Optional

from .download import download
from .models import load_config

logger = logging.getLogger('sasstastic.main')


def main(config_file: Path, alt_output_dir: Optional[Path]):
    config = load_config(config_file)
    output_dir = alt_output_dir or config.output_dir
    logger.info('building using %s config file, output directory: %s', config_file, output_dir)
    download(config.download.dir, config.download.sources)
