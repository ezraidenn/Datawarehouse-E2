import pytest

from src import scian


@pytest.mark.parametrize(
    "code, group",
    [
        ("461110", "retail"),
        ("722513", "service"),
        ("811111", "service"),
        ("611111", "service"),
        ("431110", "other"),   # wholesale is not retail
        ("311830", "other"),   # manufacturing
        ("931210", "other"),   # government is excluded from services
        ("484111", "other"),
    ],
)
def test_sector_group(code, group):
    assert scian.sector_group(code) == group


def test_manufacturing_codes_share_one_name():
    assert scian.sector_name("311830") == scian.sector_name("326110") == scian.sector_name("332320")


def test_every_service_and_retail_sector_is_named():
    for sector in scian.RETAIL_SECTORS | scian.SERVICE_SECTORS:
        assert sector in scian.SECTOR_NAMES


def test_unknown_sector():
    assert scian.sector_name("990000") == "Unknown"
    assert scian.sector_group("990000") == "other"
