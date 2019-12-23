from unittest.mock import patch
import pytest
from secret_santa import config


def test_no_config_file():
    with pytest.raises(SystemExit):
        config.read_config("/fake/foo.json")
