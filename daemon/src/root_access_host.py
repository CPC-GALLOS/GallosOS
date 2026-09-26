"""Host service entry point for local root password changes."""

from .config import _load_local_recovery_hash
from .root_access import set_root_password


def main() -> None:
    set_root_password(_load_local_recovery_hash())


if __name__ == "__main__":
    main()
