import logging
from pathlib import Path
from typing import Optional

from .compile import compile_sass
from .config import load_config
from .download import download_sass

logger = logging.getLogger('sasstastic.main')


def download_and_compile(config_file: Path, alt_output_dir: Optional[Path], dev_mode: Optional[bool]):
    config = load_config(config_file)
    config.output_dir = alt_output_dir or config.output_dir
    if dev_mode is not None:
        config.dev_mode = dev_mode
    logger.info('building using %s config file, output directory: %s', config_file, config.output_dir)
    download_sass(config.download)

    compile_sass(config)
