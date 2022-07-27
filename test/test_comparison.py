from gtirb_test_helpers import create_test_module
from gtirb_types import (
    GtirbTypes,
    GTIRBLattice,
    IntType,
    PointerType,
    StructType,
)
import gtirb
import pytest
import uuid


@pytest.mark.parametrize(
    "lhs,rhs,score",
    [
        ("int32_t", "uint32_t", 5),
        ("int32_t", "int", 1),
        ("uint32_t", "uint", 1),
        ("uint32_t", "num", 2),
        ("float", "int", 5),
    ],
)
@pytest.mark.commit
def test_gtirb_lattice(lhs, rhs, score):
    lattice = GTIRBLattice()
    assert lattice.compare_lattice(lhs, rhs) == score


@pytest.mark.commit
def test_gtirb_pointer_height():
    _, module = create_test_module(
        gtirb.Module.FileFormat.ELF, gtirb.Module.ISA.X64
    )

    lattice = GTIRBLattice()
    types = GtirbTypes(module)

    lhs1 = types.add_type(IntType(uuid.uuid4(), types, True, 4))
    lhs2 = types.add_type(PointerType(uuid.uuid4(), types, lhs1.uuid))
    lhs3 = types.add_type(PointerType(uuid.uuid4(), types, lhs2.uuid))

    assert lattice.pointer_accuracy(lhs3, lhs1) == 0
    assert lattice.pointer_accuracy(lhs3, lhs2) == 1 / 3
    assert lattice.pointer_accuracy(lhs3, lhs3) == 1
    assert lattice.pointer_accuracy(lhs2, lhs1) == 0


@pytest.mark.commit
def test_gtirb_struct_compare():
    _, module = create_test_module(
        gtirb.Module.FileFormat.ELF, gtirb.Module.ISA.X64
    )

    lattice = GTIRBLattice()
    types = GtirbTypes(module)

    int32_t = types.add_type(IntType(uuid.uuid4(), types, True, 4))
    struct1 = types.add_type(
        StructType(uuid.uuid4(), types, 4, [(0, int32_t.uuid)])
    )

    uint32_t = types.add_type(IntType(uuid.uuid4(), types, False, 4))
    struct2 = types.add_type(
        StructType(
            uuid.uuid4(), types, 8, [(0, int32_t.uuid), (4, uint32_t.uuid)]
        )
    )

    compare = lattice.compare_types(struct1, struct2)
    assert compare == 1.0
