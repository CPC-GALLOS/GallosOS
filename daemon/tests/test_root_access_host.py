"""Host helper reads the trusted local recovery hash."""

from unittest.mock import patch

from daemon.src.root_access_host import main


def test_host_helper_applies_local_hash_only():
    with (
        patch("daemon.src.root_access_host._load_local_recovery_hash", return_value="$6$abc$def"),
        patch("daemon.src.root_access_host.set_root_password") as apply_hash,
    ):
        main()
    apply_hash.assert_called_once_with("$6$abc$def")
