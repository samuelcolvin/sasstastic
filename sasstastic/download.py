import asyncio
import logging
import zipfile
from io import BytesIO
from pathlib import Path

from httpx import AsyncClient

from .common import SasstasticError, is_file_path
from .config import DownloadModel, SourceModel

__all__ = ('download_sass',)
logger = logging.getLogger('sasstastic.download')


def download_sass(m: DownloadModel):
    asyncio.run(Downloader(m).download())


class Downloader:
    def __init__(self, m: DownloadModel):
        self._download_dir = m.dir
        self._sources = m.sources
        self._client = AsyncClient()

    async def download(self):
        logger.info('\ndownloading %d files to %s', len(self._sources), self._download_dir)
        try:
            await asyncio.gather(*[self._download_source(s) for s in self._sources])
        finally:
            await self._client.aclose()

    async def _download_source(self, s: SourceModel):
        logger.debug('%s: downloading...', s.url)
        r = await self._client.get(s.url)
        if r.status_code != 200:
            logger.error('Error downloading %r, unexpected status code: %s', s.url, r.status_code)
            raise SasstasticError(f'unexpected status code {r.status_code}')

        loop = asyncio.get_event_loop()
        if s.extract is None:
            path = await loop.run_in_executor(None, self._save_file, s.to, r.content)
            logger.info('  downloaded %s ➤ %s', s.url, path)
        else:
            count = await loop.run_in_executor(None, self._extract_zip, s, r.content)
            logger.info('  downloaded %s ➤ extract %d files', s.url, count)

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
                    self._save_file(file_path, zipf.read(filepath))
                    zcopied += 1
        return zcopied

    def _save_file(self, save_to: Path, content) -> Path:
        p = self._download_dir / save_to
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        return p
