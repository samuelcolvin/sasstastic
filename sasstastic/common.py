import re
from pathlib import Path
from typing import Optional

__all__ = ('SasstasticError', 'is_file_path')


class SasstasticError(RuntimeError):
    pass


def is_file_path(p: Optional[Path]) -> bool:
    return p is not None and re.search(r'\.[a-zA-Z0-9]{1,5}$', p.name)
