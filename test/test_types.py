import gtirb
import gtirb_test_helpers
import pytest

from gtirb_types import (
    UnknownType,
    BoolType,
    IntType,
    CharType,
    FloatType,
    FunctionType,
    PointerType,
    ArrayType,
    AliasType,
    StructType,
    VoidType,
    GtirbTypes,
)
from uuid import uuid4


@pytest.mark.commit()
def test_types(tmp_path):
    """ Encode types in a module """
    ir, module = gtirb_test_helpers.create_test_module(
        gtirb.Module.FileFormat.ELF,
        gtirb.Module.ISA.X64,
    )

    types = GtirbTypes(module)

    # Construct all of the types we have
    num = IntType(uuid4(), types, False, 32)

    tests = [
        num,
        UnknownType(uuid4(), types, 32),
        BoolType(uuid4(), types),
        CharType(uuid4(), types, 32),
        FloatType(uuid4(), types, 32),
        FunctionType(uuid4(), types, num.uuid, [num.uuid]),
        PointerType(uuid4(), types, num.uuid),
        ArrayType(uuid4(), types, num.uuid, 4),
        AliasType(uuid4(), types, num.uuid),
        StructType(uuid4(), types, 4, [(0, num.uuid)]),
        VoidType(uuid4(), types),
    ]

    types.map = {type_.uuid: type_ for type_ in tests}
    types.save()
    output = tmp_path / "tmp.gtirb"
    ir.save_protobuf(str(output))

    ir2 = gtirb.IR.load_protobuf(str(output))
    module2 = ir2.modules[0]
    types2 = GtirbTypes.build_types(module2)

    # Fix types field to new types for comparison's sake
    for type_ in tests:
        found_type = types2.map[type_.uuid]
        type_.types = types2
        assert type(found_type) == type(type_)
        assert found_type == type_

        if isinstance(type_, StructType):
            assert len(found_type.fields) == len(type_.fields)

            for (lhs, rhs) in zip(found_type.fields, type_.fields):
                assert lhs == rhs
        elif isinstance(type_, AliasType):
            assert type_.pointed_to == found_type.pointed_to
        elif isinstance(type_, PointerType):
            assert type_.pointed_to == found_type.pointed_to
        elif isinstance(type_, FunctionType):
            assert type_.return_type == found_type.return_type
            assert len(type_.argument_types) == len(found_type.argument_types)

            for (lhs, rhs) in zip(
                found_type.argument_types, type_.argument_types
            ):
                assert lhs == rhs
