#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.scaleio_storage_pool import (
    _check_scaleio_storage_pool,
    discover_scaleio_storage_pool,
    DiskReadWrite,
    FilesystemStorageConversionError,
    FilesystemStoragePool,
    parse_scaleio_storage_pool,
    ScaleioStoragePoolSection,
    StoragePool,
)
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_PARAMS

SECTION = {
    "4e9a44c700000000": StoragePool(
        pool_id="4e9a44c700000000",
        name="pool01",
        filesystem_storage_pool=FilesystemStoragePool(
            total_capacity=29255270.4,
            free_capacity=16462643.2,
            failed_capacity=2311212.0,
        ),
        total_io=DiskReadWrite(
            read_throughput=33996.8,
            write_throughput=224870.4,
            read_operations=7.0,
            write_operations=63.0,
        ),
        rebalance_io=DiskReadWrite(
            read_throughput=0.0,
            write_throughput=0.0,
            read_operations=0.0,
            write_operations=0.0,
        ),
    )
}


ITEM = "4e9a44c700000000"

STRING_TABLE: StringTable = [
    ["STORAGE_POOL", "4e9a44c700000000:"],
    ["ID", "4e9a44c700000000"],
    ["NAME", "pool01"],
    ["MAX_CAPACITY_IN_KB", "27.9", "TB", "(28599", "GB)"],
    ["UNUSED_CAPACITY_IN_KB", "15.7", "TB", "(16105", "GB)"],
    ["FAILED_CAPACITY_IN_KB", "0", "Bytes"],
    ["TOTAL_READ_BWC", "7", "IOPS", "33.2", "KB", "(33996", "Bytes)", "per-second"],
    ["TOTAL_WRITE_BWC", "63", "IOPS", "219.6", "KB", "(224870", "Bytes)", "per-second"],
    ["REBALANCE_READ_BWC", "0", "IOPS", "0", "Bytes", "per-second"],
    ["REBALANCE_WRITE_BWC", "0", "IOPS", "0", "Bytes", "per-second"],
]

STRING_TABLE_WITH_UNKNOWN_FILESYSTEM_UNIT: StringTable = [
    ["STORAGE_POOL", "4e9a44c700000000:"],
    ["ID", "4e9a44c700000000"],
    ["NAME", "pool01"],
    ["MAX_CAPACITY_IN_KB", "27.9", "PB", "(28599", "GB)"],
    ["UNUSED_CAPACITY_IN_KB", "15.7", "PB", "(16105", "GB)"],
    ["FAILED_CAPACITY_IN_KB", "0", "Bytes"],
    ["TOTAL_READ_BWC", "7", "IOPS", "33.2", "KB", "(33996", "Bytes)", "per-second"],
    ["TOTAL_WRITE_BWC", "63", "IOPS", "219.6", "KB", "(224870", "Bytes)", "per-second"],
    ["REBALANCE_READ_BWC", "0", "IOPS", "0", "Bytes", "per-second"],
    ["REBALANCE_WRITE_BWC", "0", "IOPS", "0", "Bytes", "per-second"],
]


def test_parse_scaleio_id_and_name() -> None:

    scaleio_storage_pool = parse_scaleio_storage_pool(STRING_TABLE)["4e9a44c700000000"]
    assert scaleio_storage_pool.pool_id == "4e9a44c700000000"
    assert scaleio_storage_pool.name == "pool01"


def test_parse_scaleio_filesystem_data() -> None:
    assert isinstance(
        parse_scaleio_storage_pool(STRING_TABLE)["4e9a44c700000000"].filesystem_storage_pool,
        FilesystemStoragePool,
    )


def test_parse_scaleio_unknown_filesystem_unit() -> None:
    assert isinstance(
        parse_scaleio_storage_pool(STRING_TABLE_WITH_UNKNOWN_FILESYSTEM_UNIT)[
            "4e9a44c700000000"
        ].filesystem_storage_pool,
        FilesystemStorageConversionError,
    )


def test_parse_scaleio_total_io_data() -> None:
    storage_pool_total_io = parse_scaleio_storage_pool(STRING_TABLE)["4e9a44c700000000"].total_io
    assert storage_pool_total_io.read_throughput == 33996.8
    assert storage_pool_total_io.read_operations == 7.0
    assert storage_pool_total_io.write_throughput == 224870.4
    assert storage_pool_total_io.write_operations == 63.0


def test_parse_scaleio_rebalance_io_data() -> None:
    storage_pool_rebalance_io = parse_scaleio_storage_pool(STRING_TABLE)[
        "4e9a44c700000000"
    ].rebalance_io
    assert storage_pool_rebalance_io.read_throughput == 0.0
    assert storage_pool_rebalance_io.read_operations == 0.0
    assert storage_pool_rebalance_io.write_throughput == 0.0
    assert storage_pool_rebalance_io.write_operations == 0.0


def test_parse_scaleio_section_not_found() -> None:
    parse_result = parse_scaleio_storage_pool(
        [
            ["VOLUME", "4e9a44c700000000:"],
            ["ID", "4e9a44c700000000"],
            ["NAME", "pool01"],
        ]
    )
    assert parse_result == {}


@pytest.mark.parametrize(
    "parsed_section, discovered_services",
    [
        pytest.param(
            {
                "4e9a44c700000000": StoragePool(
                    pool_id="4e9a44c700000000",
                    name="pool01",
                    filesystem_storage_pool=FilesystemStoragePool(
                        total_capacity=29255270.4, free_capacity=16462643.2, failed_capacity=0.0
                    ),
                    total_io=DiskReadWrite(
                        read_throughput=33996.8,
                        write_throughput=224870.4,
                        read_operations=7.0,
                        write_operations=63.0,
                    ),
                    rebalance_io=DiskReadWrite(
                        read_throughput=0.0,
                        write_throughput=0.0,
                        read_operations=0.0,
                        write_operations=0.0,
                    ),
                )
            },
            [Service(item="4e9a44c700000000")],
            id="A service is created for each storage pool that is present in the parsed section",
        ),
        pytest.param(
            {},
            [],
            id="If no storage pool is present in the parsed section, no services are discovered",
        ),
    ],
)
def test_inventory_scaleio_storage_pool(
    parsed_section: ScaleioStoragePoolSection,
    discovered_services: Sequence[Service],
) -> None:
    assert list(discover_scaleio_storage_pool(parsed_section)) == discovered_services


def test_check_scaleio_storage_pool_with_failed_capacity() -> None:
    check_result = list(
        _check_scaleio_storage_pool(
            item=ITEM,
            params=FILESYSTEM_DEFAULT_PARAMS,
            section=SECTION,
            value_store={"4e9a44c700000000.delta": (1660684225.0453863, 12792627.2)},
        )
    )
    assert check_result[-1] == Result(state=State.CRIT, summary="Failed Capacity: 2.20 MiB")


def test_check_scaleio_storage_pool() -> None:
    check_result = list(
        _check_scaleio_storage_pool(
            item=ITEM,
            params=FILESYSTEM_DEFAULT_PARAMS,
            section=SECTION,
            value_store={"4e9a44c700000000.delta": (1660684225.0453863, 12792627.2)},
        )
    )
    assert check_result[3] == Result(state=State.OK, summary="Used: 43.73% - 12.2 TiB of 27.9 TiB")
