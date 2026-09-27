from __future__ import annotations

import errno
import logging
import os
from pathlib import Path
import shutil

_LOGGER = logging.getLogger(__name__)

_PACKAGED_CATALOG = Path(__file__).with_name("catalog") / "merged_catalog.v1.json"
_RUNTIME_CATALOG = Path(".storage") / "cook4me" / "runtime_catalog" / "merged_catalog.v1.json"


def _is_repository_checkout(path: Path) -> bool:
    """Keep tracked source files intact when Cook4Me runs from a git checkout."""
    for parent in path.parents:
        if parent.name != "custom_components":
            continue
        root = parent.parent
        return (root / ".git").exists() and (root / "hacs.json").exists()
    return False


def runtime_catalog_path(config_dir: str | Path) -> Path:
    """Return the persistent catalog path outside the HACS-managed component."""
    return Path(config_dir) / _RUNTIME_CATALOG


def prepare_release_catalog_storage(
    config_dir: str | Path,
    *,
    packaged_path: str | Path | None = None,
    allow_source_checkout: bool = False,
) -> Path:
    """Promote the packaged catalog to persistent runtime storage.

    HACS backs up the complete installed custom-component directory before every
    update. The release catalog is by far Cook4Me's largest file, so keeping it
    under custom_components makes each update copy and delete tens of megabytes
    that do not need to participate in the code rollback.

    The catalog remains part of every installation archive for fully offline
    first install/update behavior. On the following Home Assistant start it is
    atomically moved to .storage. Future HACS backups therefore cover the small
    code/UI tree only. A newly installed catalog replaces the persistent copy on
    the next restart.

    Source checkouts are deliberately left untouched.
    """
    source = Path(packaged_path) if packaged_path is not None else _PACKAGED_CATALOG
    target = runtime_catalog_path(config_dir)

    if not source.exists():
        return target if target.exists() else source
    if not allow_source_checkout and _is_repository_checkout(source):
        return source

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(source, target)
        except OSError as err:
            if err.errno != errno.EXDEV:
                raise
            # Defensive fallback for unusual split-mount configurations.
            temporary = target.with_name(target.name + ".tmp")
            shutil.copyfile(source, temporary)
            os.replace(temporary, target)
            source.unlink()
        return target
    except OSError:
        # Installation correctness wins over the optimization. If promotion
        # fails, keep using the packaged file exactly as before.
        _LOGGER.exception(
            "Could not move Cook4Me release catalog to persistent runtime storage"
        )
        return source
