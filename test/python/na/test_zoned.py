# Copyright (c) 2023 - 2026 Chair for Design Automation, TUM
# Copyright (c) 2025 - 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: MIT
#
# Licensed under the MIT License

"""Test MQT QMAP's Zoned Neutral Atom Compiler."""

from __future__ import annotations

from pathlib import Path

import pytest
from mqt.core import load
from mqt.core.ir import QuantumComputation

from mqt.qmap.na.zoned import AllocOp, RoutingAgnosticCompiler, RoutingAwareCompiler, ZonedNeutralAtomArchitecture


def operation_signature(op: object) -> tuple[type, tuple[tuple[str, object], ...]]:
    """Compare typed operation values across independent compiler calls."""
    fields = ("atom_id", "position", "angle", "theta", "phi", "lambda_", "atom_ids", "targets")
    return type(op), tuple((name, getattr(op, name)) for name in fields if hasattr(op, name))


# get the circuit directory of the project
circ_dir = Path(__file__).resolve().parent.parent.parent / "na" / "zoned" / "circuits"
# make list of contained .qasm files
circuits = list(circ_dir.glob("*.qasm"))

architecture_specification = """{
    "name": "compiler_architecture",
    "storage_zones": [{
        "zone_id": 0,
        "slms": [{"id": 0, "site_separation": [3, 3], "r": 20, "c": 20, "location": [0, 0]}],
        "offset": [0, 0],
        "dimension": [60, 60]
    }],
    "entanglement_zones": [{
        "zone_id": 0,
        "slms": [
            {"id": 1, "site_separation": [12, 10], "r": 4, "c": 4, "location": [5, 70]},
            {"id": 2, "site_separation": [12, 10], "r": 4, "c": 4, "location": [7, 70]}
        ],
        "offset": [5, 70],
        "dimension": [50, 40]
    }],
    "aods":[{"id": 0, "site_separation": 2, "r": 20, "c": 20}],
    "rydberg_range": [[[5, 70], [55, 110]]]
}"""


def test_architecture_to_namachine_string() -> None:
    """Test the Zoned Neutral Atom Architecture to namachine string conversion."""
    architecture = ZonedNeutralAtomArchitecture.from_json_string(architecture_specification)
    namachine_string = architecture.to_namachine_string()
    assert isinstance(namachine_string, str)
    assert len(namachine_string) > 0


@pytest.fixture
def compiler() -> RoutingAwareCompiler:
    """Return an MQT QMAP's Zoned Neutral Atom Compiler initialized with the above architecture and settings."""
    architecture = ZonedNeutralAtomArchitecture.from_json_string(architecture_specification)
    return RoutingAwareCompiler(architecture, window_min_width=4, window_ratio=1.5, deepening_factor=0.6)


@pytest.mark.parametrize("circuit_filename", circuits)
def test_na_routing_aware_compiler(compiler: RoutingAwareCompiler, circuit_filename: str) -> None:
    """Test the MQT QMAP's Zoned Neutral Atom Compiler."""
    qc = load(circuit_filename)
    result = compiler.compile(qc)
    assert result is not None
    assert isinstance(result, list)
    if result:
        assert isinstance(result[0], AllocOp)
    stats = compiler.stats()
    assert "totalTime" in stats
    assert stats["totalTime"] > 0


def test_get_final_placement_seeds_a_later_compile_call() -> None:
    """A compile() call's ending atom placement can seed a later, independent compile() call.

    This is the API a caller uses to compile a circuit in separate,
    barrier-delimited chunks without having to synthesize a bridging move
    themselves between chunks.
    """
    architecture = ZonedNeutralAtomArchitecture.from_json_string(architecture_specification)
    first_compiler = RoutingAwareCompiler(architecture)
    first_chunk = QuantumComputation(4)
    first_chunk.cz(0, 1)
    assert first_compiler.compile(first_chunk) is not None

    final_placement = first_compiler.get_final_placement()
    assert len(final_placement) == 4
    for site in final_placement.values():
        assert len(site) == 3

    second_compiler = RoutingAwareCompiler(architecture)
    second_chunk = QuantumComputation(4)
    second_chunk.cz(2, 3)
    assert second_compiler.compile(second_chunk, final_placement) is not None


def test_segmented_compile_preserves_empty_barrier_segments(compiler: RoutingAwareCompiler) -> None:
    """Full barriers delimit execution even when a segment has no gates."""
    qc = QuantumComputation(2)
    qc.barrier()
    qc.rz(0.5, 0)
    qc.barrier()
    qc.barrier()

    allocations, segments = compiler.compile_segmented(qc)
    assert len(allocations) == 2
    assert [len(segment) for segment in segments] == [0, 1, 0, 0]
    assert [operation_signature(op) for op in allocations + [op for segment in segments for op in segment]] == [
        operation_signature(op) for op in compiler.compile(qc)
    ]


@pytest.mark.parametrize("compiler_type", [RoutingAwareCompiler, RoutingAgnosticCompiler])
def test_segmented_compile_matches_flat_program_with_scoped_barrier(compiler_type: type) -> None:
    """Scoped fences preserve one segment; physical operations and placement stay flat-identical."""
    architecture = ZonedNeutralAtomArchitecture.from_json_string(architecture_specification)
    compiler = compiler_type(architecture)
    qc = QuantumComputation(4)
    qc.rz(0.25, 0)
    qc.cz(0, 1)
    qc.barrier([2])
    qc.cz(2, 3)
    qc.barrier()
    qc.rz(0.5, 1)

    allocations, segments = compiler.compile_segmented(qc)
    flat = compiler.compile(qc)

    assert len(segments) == 2
    assert [operation_signature(op) for op in allocations + [op for segment in segments for op in segment]] == [
        operation_signature(op) for op in flat
    ]
