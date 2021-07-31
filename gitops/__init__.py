import os
import sys
from pathlib import Path

from .utils.cli import success, warning

__version__ = "0.7.0"


# Checking gitops version matches cluster repo version.
versions_path = Path(os.environ.get("GITOPS_APPS_DIRECTORY", "apps")).parent / "setup.cfg"
if versions_path.exists():
    import configparser

    from pkg_resources.extern.packaging.version import parse as parse_version

    config = configparser.RawConfigParser()
    config.read(versions_path)
    min_gitops_version = config.get("gitops.versions", "gitops")
    if parse_version(__version__) < parse_version(min_gitops_version):
        print(warning("Please upgrade Gitops."), file=sys.stderr)
        print(
            f"Your current version {success(__version__)} is less than the clusters minimum"
            f" requirement {success(min_gitops_version)}.",
            file=sys.stderr,
        )
