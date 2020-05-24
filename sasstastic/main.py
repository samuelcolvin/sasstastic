import asyncio
import logging
from pathlib import Path
from typing import Optional

import watchgod

from .compile import compile_sass
from .config import ConfigModel, load_config
from .download import Downloader, download_sass

logger = logging.getLogger('sasstastic.main')
__all__ = 'download_and_compile', 'watch', 'awatch'


def download_and_compile(config: ConfigModel, alt_output_dir: Optional[Path] = None, dev_mode: Optional[bool] = None):
    logger.info('build path:  %s/', config.build_dir)
    logger.info('output path: %s/', alt_output_dir or config.output_dir)

    download_sass(config)
    compile_sass(config, alt_output_dir, dev_mode)


def watch(config: ConfigModel, alt_output_dir: Optional[Path] = None, dev_mode: Optional[bool] = None):
    try:
        asyncio.run(awatch(config, alt_output_dir, dev_mode))
    except KeyboardInterrupt:
        pass


async def awatch(config: ConfigModel, alt_output_dir: Optional[Path] = None, dev_mode: Optional[bool] = None):
    logger.info('build path:  %s/', config.build_dir)
    logger.info('output path: %s/', alt_output_dir or config.output_dir)

    await Downloader(config).download()
    compile_sass(config, alt_output_dir, dev_mode)

    config_file = str(config.config_file)
    async for changes in watch_multiple(config_file, config.build_dir):
        changed_paths = {c[1] for c in changes}
        if config_file in changed_paths:
            logger.info('changes detected in config file, downloading sources...')
            config = load_config(config.config_file)
            await Downloader(config).download()

        if changed_paths != {config_file}:
            logger.info('changes detected in the build directory, re-compiling...')
            compile_sass(config, alt_output_dir, dev_mode)


async def watch_multiple(*paths):
    watchers = [watchgod.awatch(p) for p in paths]
    while True:
        done, pending = await asyncio.wait([w.__anext__() for w in watchers], return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        for t in done:
            yield t.result()
