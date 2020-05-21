import hashlib
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path
from time import time
from typing import Optional, Union

import click
import sass

from .common import SasstasticError
from .config import ConfigModel

__all__ = ('compile_sass',)
logger = logging.getLogger('sasstastic.compile')
STARTS_DOWNLOAD = re.compile('^(?:DOWNLOAD|DL)/')
STARTS_SRC = re.compile('^SRC/')


def compile_sass(config: ConfigModel, alt_output_dir: Optional[Path] = None, dev_mode: Optional[bool] = None):
    return SassCompiler(config, alt_output_dir, dev_mode).build()


class SassCompiler:
    def __init__(self, config: ConfigModel, alt_output_dir: Optional[Path], dev_mode: Optional[bool]):
        self._config = config
        self._build_dir = config.build_dir
        self._out_dir = alt_output_dir or config.output_dir
        if dev_mode is None:
            self._dev_mode = config.dev_mode
        else:
            self._dev_mode = dev_mode
        self._src_dir = self._build_dir
        self._replace = config.replace or {}
        self._download_dir = config.download.dir
        self._importers = [(5, self._clever_imports)]

        dir_hash = hashlib.md5(str(self._build_dir).encode()).hexdigest()
        self._size_cache_file = Path(tempfile.gettempdir()) / 'grablib_cache.{}.json'.format(dir_hash)

        self._output_style = 'nested' if self._dev_mode else 'compressed'

        self._old_size_cache = {}
        self._new_size_cache = {}
        self._errors = 0
        self._files_generated = 0

    def build(self):
        start = time()

        mode = 'dev' if self._dev_mode else 'prod'
        logger.info('\ncompiling "%s/" to "%s/" (mode: %s)', self._build_dir, self._out_dir, mode)
        if self._config.wipe_output_dir and self._out_dir.exists():
            assert self._out_dir.is_dir(), 'output_dir must be a directory'
            logger.info('deleting %s/ prior to build', self._out_dir)
            shutil.rmtree(str(self._out_dir))

        self._out_dir.mkdir(parents=True, exist_ok=True)
        if self._dev_mode:
            self._src_dir = out_dir_src = self._out_dir / '.src'
            if out_dir_src.exists():
                logger.info('deleting %s/ prior to build', out_dir_src)
                shutil.rmtree(str(out_dir_src))

            shutil.copytree(str(self._build_dir), str(out_dir_src))
            files = sum(f.is_file() for f in out_dir_src.glob('**/*'))
            logger.info('>>  %28s/* ➤ %-30s %3d files', self._build_dir, out_dir_src, files)

            try:
                self._download_dir = out_dir_src / self._download_dir.relative_to(self._build_dir)
            except ValueError:
                # download dir is not inside the build dir, need to copy libs too
                out_dir_libs = self._out_dir / '.libs'
                shutil.copytree(str(self._download_dir), str(out_dir_libs))
                files = sum(f.is_file() for f in out_dir_libs.glob('**/*'))
                logger.info('%28s/* ➤ %-30s %3d files', self._download_dir, out_dir_libs, files)
                self._download_dir = out_dir_src

        if self._size_cache_file.exists():
            with self._size_cache_file.open() as f:
                self._old_size_cache = json.load(f)

        for path in self._src_dir.glob('**/*.*'):
            self.process_file(path)

        with self._size_cache_file.open('w') as f:
            json.dump(self._new_size_cache, f, indent=2)

        time_taken = (time() - start) * 1000
        if not self._errors:
            logger.info('%d css files generated in %0.0fms, 0 errors', self._files_generated, time_taken)
        else:
            logger.error(
                '%d css files generated in %0.0fms, %d errors', self._files_generated, time_taken, self._errors
            )
            raise SasstasticError('sass errors')

    def process_file(self, f: Path):
        if not f.is_file():
            return
        if not self._config.include_files.search(f.name):
            return
        if self._config.exclude_files and self._config.exclude_files.search(str(f)):
            return

        if is_relative_to(f, self._download_dir):
            return

        rel_path = f.relative_to(self._src_dir)
        css_path = (self._out_dir / rel_path).with_suffix('.css')

        map_path = css_path.with_name(css_path.name + '.map') if self._dev_mode else None

        try:
            css = sass.compile(
                filename=str(f),
                source_map_filename=map_path and str(map_path),
                output_style=self._output_style,
                precision=10,
                importers=self._importers,
            )
        except sass.CompileError as e:
            self._errors += 1
            logger.error('%s compile error:\n%s', f, e)
            return

        log_msg = None
        file_hashes = self._config.file_hashes
        try:
            css_path.parent.mkdir(parents=True, exist_ok=True)
            if self._dev_mode:
                css, css_map = css

                if file_hashes:
                    css_path = insert_hash(css_path, css)
                    map_path = insert_hash(map_path, css)
                    file_hashes = False

                # correct the link to map file in css
                css = re.sub(r'/\*# sourceMappingURL=\S+ \*/', f'/*# sourceMappingURL={map_path.name} */', css)
                map_path.write_text(css_map)
            css, log_msg = self._regex_modify(rel_path, css)
        finally:
            self._log_file_creation(rel_path, css_path, css)
            if log_msg:
                logger.debug(log_msg)

        if file_hashes:
            css_path = insert_hash(css_path, css)
        css_path.write_text(css)
        self._files_generated += 1

    def _regex_modify(self, rel_path, css):
        log_msg = None

        for path_regex, regex_map in self._replace.items():
            if re.search(path_regex, str(rel_path)):
                logger.debug('%s has regex replace matches for "%s"', rel_path, path_regex)
                for pattern, repl in regex_map.items():
                    hash1 = hash(css)
                    css = re.sub(pattern, repl, css)
                    if hash(css) == hash1:
                        log_msg = '  "{}" ➤ "{}" didn\'t modify the source'.format(pattern, repl)
                    else:
                        log_msg = '  "{}" ➤ "{}" modified the source'.format(pattern, repl)
        return css, log_msg

    def _log_file_creation(self, rel_path, css_path, css):
        src, dst = str(rel_path), str(css_path.relative_to(self._out_dir))

        size = len(css.encode())
        p = str(css_path)
        self._new_size_cache[p] = size
        old_size = self._old_size_cache.get(p)
        c = None
        if old_size:
            change_p = (size - old_size) / old_size * 100
            if abs(change_p) > 0.5:
                c = 'green' if change_p <= 0 else 'red'
                change_p = click.style('{:+0.0f}%'.format(change_p), fg=c)
                logger.info('>>  %30s ➤ %-30s %9s %s', src, dst, fmt_size(size), change_p)
        if c is None:
            logger.info('>>  %30s ➤ %-30s %9s', src, dst, fmt_size(size))

    def _clever_imports(self, src_path):
        _new_path = None
        if STARTS_SRC.match(src_path):
            _new_path = self._build_dir / STARTS_SRC.sub('', src_path)
        elif STARTS_DOWNLOAD.match(src_path):
            _new_path = self._download_dir / STARTS_DOWNLOAD.sub('', src_path)

        return _new_path and [(str(_new_path),)]


def insert_hash(path: Path, content: Union[str, bytes], *, hash_length=7):
    """
    Insert a hash based on the content into the path after the first dot.

    hash_length 7 matches git commit short references
    """
    if isinstance(content, str):
        content = content.encode()
    hash_ = hashlib.md5(content).hexdigest()[:hash_length]
    if '.' in path.name:
        new_name = re.sub(r'\.', f'.{hash_}.', path.name, count=1)
    else:
        new_name = f'{path.name}.{hash_}'
    return path.with_name(new_name)


KB, MB = 1024, 1024 ** 2


def fmt_size(num):
    if num <= KB:
        return f'{num:0.0f}B'
    elif num <= MB:
        return f'{num / KB:0.1f}KB'
    else:
        return f'{num / MB:0.1f}MB'


def is_relative_to(p1: Path, p2: Path) -> bool:
    try:
        p1.relative_to(p2)
    except ValueError:
        return False
    else:
        return True
