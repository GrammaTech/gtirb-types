#
# Copyright (C) 2022 GrammaTech, Inc.
#
# This code is licensed under the MIT license. See the LICENSE file in
# the project root for license terms.
#
# This project is sponsored by the Office of Naval Research, One Liberty
# Center, 875 N. Randolph Street, Arlington, VA 22203 under contract #
# N68335-17-C-0700.  The content of the information does not necessarily
# reflect the position or policy of the Government and no official
# endorsement should be inferred.
#
import bisect
import gtirb
from gtirb_types.types import (
    AbstractType,
    AliasType,
    ArrayType,
    BoolType,
    CharType,
    FloatType,
    FunctionType,
    PointerType,
    IntType,
    StructType,
    UnknownType,
    VoidType,
)


def get_pointer_size(module: gtirb.Module) -> int:
    """Address and register sizes for a given module's ISA
    :param module: GTIRB Module to read from
    :returns: (ptr, reg) sizes in bits
    """
    if module.isa in (
        gtirb.module.Module.ISA.X64,
        gtirb.module.Module.ISA.ARM64,
        gtirb.module.Module.ISA.MIPS64,
        gtirb.module.Module.ISA.PPC64,
    ):
        return 8
    elif module.isa == gtirb.module.Module.ISA.PPC32:
        return 4
    elif module.isa in (
        gtirb.module.Module.ISA.ARM,
        gtirb.module.Module.ISA.IA32,
        gtirb.module.Module.ISA.MIPS32,
    ):
        return 4
    else:
        raise NotImplementedError()


def type_size(type_: AbstractType) -> int:
    """Get the size of a given type
    :param type_: Type to get the size of
    :returns: Size in bytes of that type
    """
    if isinstance(
        type_,
        (
            CharType,
            FloatType,
            IntType,
            StructType,
        ),
    ):
        return type_.size
    elif isinstance(type_, AliasType):
        assert type_.pointed_to
        return type_size(type_.pointed_to)
    elif isinstance(type_, ArrayType):
        assert type_.element_type
        return type_.number_elements * type_size(type_.element_type)
    elif isinstance(type_, (FunctionType, PointerType, UnknownType)):
        module = type_.types.module
        return get_pointer_size(module)
    elif isinstance(type_, BoolType):
        return 1
    elif isinstance(type_, VoidType):
        return 0
    else:
        raise NotImplementedError()


def c_str(type_: AbstractType, define: bool = True) -> str:
    """Create a C string from a type object
    :param type_: Type object to convert to a C-string
    :param define: Create a definition or declaration of the type object. This
        is, for example, for creating struct x; vs struct x {int x;};, where the
        former is the declaration and the latter is definition. This defaults to
        definition (True), though when recursing down types it becomes False.
    :returns: The C-string
    """
    if type_.name:
        name = type_.name
    else:
        # Generate a rough/unique name in case we don't have one avaiable to us
        uuid_str = str(type_.uuid).replace("-", "_")
        name = f"{type(type_).__name__}_{uuid_str}"

    if isinstance(type_, IntType):
        signedness = "" if type_.is_signed else "u"
        return f"{signedness}int{type_.size*8}_t"
    elif isinstance(type_, FloatType):
        if type_.size == 4:
            return "float"
        elif type_.size == 8:
            return "double"
        else:
            return f"float{type_.size*8}_t"
    elif isinstance(type_, BoolType):
        return "bool"
    elif isinstance(type_, UnknownType):
        return f"char[{type_.size}]"
    elif isinstance(type_, CharType):
        if type_.size == 1:
            return "char"
        else:
            return f"char{type_.size*8}_t"
    elif isinstance(type_, PointerType):
        assert type_.pointed_to
        return f"{c_str(type_.pointed_to, False)}*"
    elif isinstance(type_, ArrayType):
        # XXX - This isn't technically valid for a struct field, because we
        # need to print as int x[4]; not int[4] x;. For now we'll consider
        # this "good enough".
        assert type_.element_type
        return f"{c_str(type_.element_type, False)}[{type_.number_elements}]"
    elif isinstance(type_, AliasType):
        if define:
            assert type_.pointed_to
            return f"typedef {name} = {c_str(type_.pointed_to, False)}"
        else:
            if type_.name:
                return name
            elif type_.pointed_to:
                return c_str(type_.pointed_to, False)
    elif isinstance(type_, StructType):
        # If we've accidentally recordered "struct <x>", cut off the first part
        # since we print the struct ourselves.
        if name.startswith("struct "):
            name = name[7:]

        if define:
            field_strs = ""
            fields = {offset: field for (offset, field) in type_.fields}
            loc = 0

            while loc < type_.size:
                if loc in fields:
                    field_type = fields[loc]
                    assert field_type
                    field_strs += (
                        f"\t{c_str(field_type, False)} field_{loc:x};\n"
                    )
                    loc += type_size(field_type)
                else:
                    field_keys = sorted(fields.keys())
                    key_index = bisect.bisect_left(field_keys, loc)
                    field_offset = (
                        field_keys[key_index]
                        if key_index < len(field_keys)
                        else type_.size
                    )
                    dist = field_offset - loc
                    field_strs += f"\tchar gap_{loc:x}[{dist}];\n"
                    loc = field_offset

            return f"struct {name} {{\n{field_strs}}}"
        else:
            return f"struct {name}"
    elif isinstance(type_, FunctionType):
        ret_str = c_str(type_.return_type, False)
        args_str = ", ".join(
            map(lambda x: c_str(x, False), type_.argument_types)
        )
        return f"{ret_str} (*)({args_str})"
    elif isinstance(type_, VoidType):
        return "void"

    raise NotImplementedError()
