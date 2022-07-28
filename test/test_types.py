import gtirb
import gtirb_test_helpers
import pytest

from gtirb_types import (
    c_str,
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
    num = types.add_type(IntType(uuid4(), types, False, 32))

    tests = [
        num,
        types.add_type(UnknownType(uuid4(), types, 32)),
        types.add_type(BoolType(uuid4(), types)),
        types.add_type(CharType(uuid4(), types, 32)),
        types.add_type(FloatType(uuid4(), types, 32)),
        types.add_type(FunctionType(uuid4(), types, num.uuid, [num.uuid])),
        types.add_type(PointerType(uuid4(), types, num.uuid)),
        types.add_type(ArrayType(uuid4(), types, num.uuid, 4)),
        types.add_type(AliasType(uuid4(), types, num.uuid), "test"),
        types.add_type(StructType(uuid4(), types, 4, [(0, num.uuid)]), "test"),
        types.add_type(VoidType(uuid4(), types)),
    ]

    types.save()
    output = tmp_path / "tmp.gtirb"
    ir.save_protobuf(str(output))

    ir2 = gtirb.IR.load_protobuf(str(output))
    module2 = ir2.modules[0]
    types2 = GtirbTypes(module2)
    assert types2.names == types.names

    # Fix types field to new types for comparison's sake
    for type_ in tests:
        found_type = types2.map[type_.uuid]
        type_.types = types2
        assert type(found_type) == type(type_)
        assert found_type == type_

        if isinstance(type_, StructType):
            assert type_.name == "test"
            assert len(found_type.fields) == len(type_.fields)

            for (lhs, rhs) in zip(found_type.fields, type_.fields):
                assert lhs == rhs
        elif isinstance(type_, AliasType):
            assert type_.pointed_to == found_type.pointed_to
            assert type_.name == "test"
        elif isinstance(type_, PointerType):
            assert type_.pointed_to == found_type.pointed_to
        elif isinstance(type_, FunctionType):
            assert type_.return_type == found_type.return_type
            assert len(type_.argument_types) == len(found_type.argument_types)

            for (lhs, rhs) in zip(
                found_type.argument_types, type_.argument_types
            ):
                assert lhs == rhs


@pytest.mark.commit
def test_c_str():
    _, module = gtirb_test_helpers.create_test_module(
        gtirb.Module.FileFormat.ELF,
        gtirb.Module.ISA.X64,
    )

    types = GtirbTypes(module)

    # Construct all of the types we have
    num = types.add_type(IntType(uuid4(), types, False, 4))
    assert c_str(num) == "uint32_t"
    assert c_str(IntType(uuid4(), types, True, 4)) == "int32_t"
    assert c_str(UnknownType(uuid4(), types, 8)) == "char[8]"
    assert c_str(BoolType(uuid4(), types)) == "bool"
    assert c_str(CharType(uuid4(), types, 1)) == "char"
    assert c_str(FloatType(uuid4(), types, 4)) == "float"
    assert c_str(FloatType(uuid4(), types, 8)) == "double"
    assert (
        c_str(FunctionType(uuid4(), types, num.uuid, [num.uuid]))
        == "uint32_t (*)(uint32_t)"
    )
    num_ptr = types.add_type(PointerType(uuid4(), types, num.uuid))
    assert c_str(num_ptr) == "uint32_t*"
    assert c_str(ArrayType(uuid4(), types, num.uuid, 4)) == "uint32_t[4]"
    assert (
        c_str(types.add_type(AliasType(uuid4(), types, num.uuid), "test"))
        == "typedef test = uint32_t"
    )
    type_id = uuid4()
    calc_name = "AliasType_" + str(type_id).replace("-", "_")

    assert (
        c_str(types.add_type(AliasType(type_id, types, num.uuid)))
        == f"typedef {calc_name} = uint32_t"
    )
    assert (
        c_str(
            types.add_type(
                StructType(uuid4(), types, 8, [(0, num.uuid)]), "test"
            )
        )
        == """struct test {
\tuint32_t field_0;
\tchar gap_4[4];
}"""
    )
    assert c_str(VoidType(uuid4(), types)) == "void"
    assert (
        c_str(
            FunctionType(
                uuid4(),
                types,
                num.uuid,
                [
                    types.add_type(
                        StructType(uuid4(), types, 8, [(0, num.uuid)]), "test"
                    ).uuid
                ],
            )
        )
        == "uint32_t (*)(struct test)"
    )
    assert (
        c_str(
            types.add_type(
                StructType(uuid4(), types, 12, [(8, num.uuid), (0, num.uuid)]),
                "test",
            )
        )
        == """struct test {
\tuint32_t field_0;
\tchar gap_4[4];
\tuint32_t field_8;
}"""
    )
    assert (
        c_str(
            types.add_type(
                StructType(
                    uuid4(), types, 12, [(8, num_ptr.uuid), (0, num_ptr.uuid)]
                ),
                "test",
            )
        )
        == """struct test {
\tuint32_t* field_0;
\tuint32_t* field_8;
}"""
    )
