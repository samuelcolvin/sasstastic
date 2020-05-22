import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern

import yaml
from pydantic import BaseModel, HttpUrl, ValidationError, validator
from pydantic.error_wrappers import display_errors

from .common import SasstasticError, is_file_path

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

__all__ = 'SourceModel', 'DownloadModel', 'ConfigModel', 'load_config'
logger = logging.getLogger('sasstastic.config')


class SourceModel(BaseModel):
    url: HttpUrl
    extract: Optional[Dict[Pattern, Optional[Path]]] = None
    to: Optional[Path] = None

    @validator('url', pre=True)
    def remove_spaces_from_url(cls, v):
        return v and v.replace(' ', '')

    @validator('extract', each_item=True)
    def check_extract_path(cls, v):
        if v is not None and v.is_absolute():
            raise ValueError('extract path may not be absolute, remove the leading slash')
        return v

    @validator('to', always=True)
    def check_to(cls, v, values):
        if values.get('extract'):
            # extracting, to can be None
            return v
        elif is_file_path(v):
            # to is already a valid path
            return v
        elif v is not None and v.is_absolute():
            raise ValueError('path may not be absolute, remove the leading slash')

        try:
            url: HttpUrl = values['url']
        except KeyError:
            return v
        else:
            filename = (url.path or '/').rsplit('/', 1)[1]
            if not filename.endswith(('.css', '.sass', '.scss')):
                raise ValueError(f'no filename found in url "{url}" and file path not given via "to"')
            return (v or Path('.')) / filename


class DownloadModel(BaseModel):
    dir: Path
    sources: List[SourceModel]


class ConfigModel(BaseModel):
    download: Optional[DownloadModel] = None
    build_dir: Path
    output_dir: Path
    lock_file: Path = Path('.sasstastic.lock')
    wipe_output_dir: bool = False
    include_files: Pattern = re.compile(r'^[^_].+\.(?:css|sass|scss)$')
    exclude_files: Optional[Pattern] = None
    replace: Optional[Dict[Pattern, Dict[Pattern, str]]] = None
    file_hashes: bool = False
    dev_mode: bool = True
    config_file: Path

    @classmethod
    def parse_obj(cls, config_file: Path, obj: Dict[str, Any]) -> 'ConfigModel':
        if isinstance(obj, dict):
            obj['config_file'] = config_file
        m: ConfigModel = super().parse_obj(obj)

        config_directory = config_file.parent
        if not m.download.dir.is_absolute():
            m.download.dir = config_directory / m.download.dir

        if not m.build_dir.is_absolute():
            m.build_dir = config_directory / m.build_dir

        if not m.output_dir.is_absolute():
            m.output_dir = config_directory / m.output_dir

        if not m.lock_file.is_absolute():
            m.lock_file = config_directory / m.lock_file
        return m


def load_config(config_file: Path) -> ConfigModel:
    if not config_file.is_file():
        logger.error('%s does not exist', config_file)
        raise SasstasticError('config files does not exist')
    try:
        with config_file.open('r') as f:
            data = yaml.load(f, Loader=Loader)
    except yaml.YAMLError as e:
        logger.error('invalid YAML file %s:\n%s', config_file, e)
        raise SasstasticError('invalid YAML file')

    try:
        return ConfigModel.parse_obj(config_file, data)
    except ValidationError as exc:
        logger.error('Error parsing %s:\n%s', config_file, display_errors(exc.errors()))
        raise SasstasticError('error parsing config file')
