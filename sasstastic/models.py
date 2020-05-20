import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Pattern

import yaml
from pydantic import BaseModel, HttpUrl, ValidationError, validator
from pydantic.error_wrappers import display_errors

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

logger = logging.getLogger('sasstastic.models')


class SourceModel(BaseModel):
    url: HttpUrl
    extract: Optional[Dict[Pattern, Optional[Path]]] = None
    to: Optional[Path] = None

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
    wipe_output_dir: bool = False
    include_files: Pattern = re.compile(r'^[^_].+\.(?:css|sass|scss)$')
    exclude_files: Optional[Pattern] = None
    replace: Optional[Dict[Pattern, Dict[Pattern, str]]] = None
    file_hashes: bool = False
    dev: bool = False


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
        config = ConfigModel.parse_obj(data)
    except ValidationError as exc:
        logger.error('Error parsing %s:\n%s', config_file, display_errors(exc.errors()))
        raise SasstasticError('error parsing config file')
    config_dir = config_file.parent

    if not config.download.dir.is_absolute():
        config.download.dir = config_dir / config.download.dir

    if not config.build_dir.is_absolute():
        config.build_dir = config_dir / config.build_dir

    if not config.output_dir.is_absolute():
        config.output_dir = config_dir / config.output_dir
    return config


class SasstasticError(RuntimeError):
    pass


def is_file_path(p: Optional[Path]) -> bool:
    return p is not None and re.search(r'\.[a-zA-Z0-9]{1,5}$', p.name)
