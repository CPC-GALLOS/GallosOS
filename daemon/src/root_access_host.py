"""Host service entry point for local root password changes."""

import sys

from .config import _load_local_recovery_hash
from .root_access import set_root_password


def main() -> None:
    set_root_password(_load_local_recovery_hash())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(130)
