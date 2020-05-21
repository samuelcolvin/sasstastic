import asyncio
import hashlib
import json
import logging
import zipfile
from io import BytesIO
from itertools import chain
from pathlib import Path
from typing import Dict, List, Set, Tuple

from httpx import AsyncClient

from .common import SasstasticError, is_file_path
from .config import ConfigModel, SourceModel

__all__ = ('download_sass',)
logger = logging.getLogger('sasstastic.download')


def download_sass(config: ConfigModel):
    asyncio.run(Downloader(config).download())


class Downloader:
    def __init__(self, config: ConfigModel):
        self._download_dir = config.download.dir
        self._sources = config.download.sources
        self._client = AsyncClient()
        self._lock_check = LockCheck(self._download_dir, config.lock_file)

    async def download(self):
        if not self._sources:
            logger.info('\nno files to download')
            return

        to_download = [s for s in self._sources if self._lock_check.should_download(s)]
        if to_download:
            logger.info(
                '\ndownloading %d files to %s, %d up-to-date',
                len(to_download),
                self._download_dir,
                len(self._sources) - len(to_download),
            )
            try:
                await asyncio.gather(*[self._download_source(s) for s in to_download])
            finally:
                await self._client.aclose()
            self._lock_check.save()
        else:
            logger.info('\nno new files to download, %d up-to-date', len(self._sources))
        self._lock_check.delete_stale()

    async def _download_source(self, s: SourceModel):
        logger.debug('%s: downloading...', s.url)
        r = await self._client.get(s.url)
        if r.status_code != 200:
            logger.error('Error downloading %r, unexpected status code: %s', s.url, r.status_code)
            raise SasstasticError(f'unexpected status code {r.status_code}')

        loop = asyncio.get_event_loop()
        if s.extract is None:
            path = await loop.run_in_executor(None, self._save_file, s.to, r.content)
            self._lock_check.record(s, s.to, r.content)
            logger.info('>>  downloaded %s ➤ %s', s.url, path)
        else:
            count = await loop.run_in_executor(None, self._extract_zip, s, r.content)
            logger.info('>>  downloaded %s ➤ extract %d files', s.url, count)

    def _extract_zip(self, s: SourceModel, content: bytes):
        zcopied = 0
        with zipfile.ZipFile(BytesIO(content)) as zipf:
            logger.debug('%s: %d files in zip archive', s.url, len(zipf.namelist()))

            for filepath in zipf.namelist():
                if filepath.endswith('/'):
                    continue
                regex_pattern, match, file_path = None, None, None
                for r, t in s.extract.items():
                    match = r.match(filepath)
                    if match:
                        regex_pattern, file_path = r, t
                        break
                if regex_pattern is None:
                    logger.debug('%s: "%s" no target found', s.url, filepath)
                elif file_path is None:
                    logger.debug('%s: "%s" skipping (regex: "%s")', s.url, filepath, regex_pattern)
                else:
                    if not is_file_path(file_path):
                        file_name = match.groupdict().get('filename') or match.groups()[-1]
                        file_path = file_path / file_name
                    logger.debug('%s: "%s" ➤ "%s" (regex: "%s")', s.url, filepath, file_path, regex_pattern)
                    content = zipf.read(filepath)
                    self._lock_check.record(s, file_path, content)
                    self._save_file(file_path, content)
                    zcopied += 1
        return zcopied

    def _save_file(self, save_to: Path, content) -> Path:
        p = self._download_dir / save_to
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        return p


class LockCheck:
    """
    Avoid downloading unchanged files by consulting a "lock file" cache.
    """

    def __init__(self, root_dir: Path, lock_file: Path):
        self._root_dir = root_dir
        self._lock_file = lock_file
        if lock_file.is_file():
            with lock_file.open() as f:
                self._cache = json.load(f)
        else:
            self._cache: Dict[str, List[Tuple[str, str]]] = {}
        self._active: Set[str] = set()

    def should_download(self, s: SourceModel) -> bool:
        k = self._hash_source(s)
        files = self._cache.get(k)
        if files is None:
            return True
        else:
            self._active.add(k)
            return not any(self._file_unchanged(*v) for v in files)

    def record(self, s: SourceModel, path: Path, content: bytes):
        k = self._hash_source(s)
        r = str(path), hashlib.md5(content).hexdigest()
        self._active.add(k)
        files = self._cache.get(k)
        if files is None:
            self._cache[k] = [r]
        else:
            files.append(r)

    def save(self):
        lines = ',\n'.join(f'  "{k}": {json.dumps(v)}' for k, v in self._cache.items() if k in self._active)
        self._lock_file.write_text(f'{{\n{lines}\n}}')

    def delete_stale(self):
        d_files = set(chain.from_iterable((p for p, _ in f) for u, f in self._cache.items() if u in self._active))
        for p in self._root_dir.glob('**/*'):
            rel_path = str(p.relative_to(self._root_dir))
            if rel_path not in d_files and p.is_file():
                p.unlink()
                logger.info('>>  %s stale and deleted', rel_path)

    def _file_unchanged(self, path: str, file_hash: str) -> bool:
        p = self._root_dir / path
        return p.is_file() and hashlib.md5(p.read_bytes()).hexdigest() == file_hash

    @staticmethod
    def _hash_source(s: SourceModel):
        j = str(s.url), None if s.extract is None else {str(k): str(v) for k, v in s.extract.items()}, str(s.to)
        return hashlib.md5(json.dumps(j).encode()).hexdigest()
