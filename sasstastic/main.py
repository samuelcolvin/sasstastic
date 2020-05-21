import logging
from pathlib import Path
from typing import Optional

from .compile import compile_sass
from .config import ConfigModel
from .download import download_sass

logger = logging.getLogger('sasstastic.main')


def download_and_compile(config: ConfigModel, alt_output_dir: Optional[Path] = None, dev_mode: Optional[bool] = None):
    logger.info('build path:  %s/', config.build_dir)
    logger.info('output path: %s/', alt_output_dir or config.output_dir)

    download_sass(config)
    compile_sass(config, alt_output_dir, dev_mode)
