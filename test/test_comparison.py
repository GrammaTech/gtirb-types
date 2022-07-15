from gtirb_test_helpers import create_test_module
from gtirb_types import GtirbTypes, GTIRBLattice, IntType, PointerType
import gtirb
import pytest
import uuid


@pytest.mark.commit
def test_gtirb_latitice():
    _, module = create_test_module(
        gtirb.Module.FileFormat.ELF, gtirb.Module.ISA.X64
    )

    lattice = GTIRBLattice()
    types = GtirbTypes(module)

    lhs = IntType(uuid.uuid4(), types, True, 4)
    rhs = IntType(uuid.uuid4(), types, False, 4)

    assert lattice.compare_types(lhs, rhs) == 2


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
