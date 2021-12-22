from __future__ import annotations
from dataclasses import dataclass
import dataclasses
from typing import Any, List, Optional, Tuple, Type, TypeVar
import abc
import gtirb
from uuid import UUID

from gtirb.serialization import Variant


@dataclass
class AbstractType(abc.ABC):
    """ Abstract base class for GTIRB types """

    TTypeCons = TypeVar("TTypeCons", bound="AbstractType")
    uuid: UUID
    types: GtirbTypes

    @classmethod
    def get_type_data(
        cls: Type[TTypeCons], types: GtirbTypes, data: UUID
    ) -> Any:
        """Get the data from the type variant
        :param types: The GtirbTypes container with the loaded table
        :param data: UUID of the type object to query
        :returns: Data for that UUID
        """
        variant = types.type_table.data[data]
        return variant.val

    @classmethod
    def from_protobuf(
        cls: Type[TTypeCons], types: GtirbTypes, uuid: UUID
    ) -> TTypeCons:
        """Load a type object from the table in the protobuf
        :param types: GtirbTypes object with loaded module data
        :param uuid: UUID to load the data from
        :return: Object constructed with that data
        """
        data = cls.get_type_data(types, uuid)
        # Special case for the Void/Bool types which are a 1-length tuple
        if not isinstance(data, tuple) or hasattr(cls, "_empty"):
            data = (data,)
        return cls(uuid, types, *data)

    def to_protobuf(self) -> Any:
        """Encode the data for use in the protobuf serialization
        :return: Data encoded for serialization
        """
        data = tuple(
            [
                self.__dict__[field.name]
                for field in dataclasses.fields(self)
                if field.name not in ["uuid", "types", "GTIRB_TYPE"]
            ]
        )

        if len(data) == 1:
            return data[0]
        return data


@dataclass
class UnknownType(AbstractType):
    """ Type whose only known factor is their size """

    size: int
    GTIRB_TYPE: str = "uint64_t"


@dataclass
class BoolType(AbstractType):
    """ Boolean type """

    _empty: Tuple[int] = (0,)
    GTIRB_TYPE: str = "tuple<uint8_t>"  # TODO: This should be empty


@dataclass
class IntType(AbstractType):
    """ Integeral type """

    is_signed: bool
    size: int
    GTIRB_TYPE: str = "tuple<int8_t,uint64_t>"


@dataclass
class CharType(AbstractType):
    """ Char-like type"""

    size: int
    GTIRB_TYPE: str = "uint64_t"


@dataclass
class FloatType(AbstractType):
    """ Floating point numeral type """

    size: int
    GTIRB_TYPE: str = "uint64_t"


@dataclass
class FunctionType(AbstractType):
    """ Type of a function """

    _return_type: UUID
    _argument_types: List[UUID]
    GTIRB_TYPE: str = "tuple<UUID,sequence<UUID>>"

    @property
    def return_type(self) -> Optional[AbstractType]:
        return _load_type(self.types, self._return_type)

    @property
    def argument_types(self) -> List[Optional[AbstractType]]:
        return [
            _load_type(self.types, argument_type)
            for argument_type in self._argument_types
        ]


@dataclass
class PointerType(AbstractType):
    """ Type that is a pointer to another known type """

    _pointed_to: UUID
    GTIRB_TYPE: str = "UUID"

    @property
    def pointed_to(self) -> Optional[AbstractType]:
        return _load_type(self.types, self._pointed_to)


@dataclass
class ArrayType(AbstractType):
    """ Fixed-width size array of elements of a known type """

    _element_type: UUID
    number_elements: int
    GTIRB_TYPE: str = "tuple<UUID,uint64_t>"

    @property
    def element_type(self) -> Optional[AbstractType]:
        return _load_type(self.types, self._element_type)


@dataclass
class AliasType(AbstractType):
    """ Type that is an alias of another known type """

    _pointed_to: UUID
    GTIRB_TYPE: str = "UUID"

    @property
    def pointed_to(self) -> Optional[AbstractType]:
        return _load_type(self.types, self._pointed_to)


@dataclass
class StructType(AbstractType):
    """ Type of an aggregate of multiple subtypes"""

    size: int
    _fields: List[Tuple[int, UUID]]
    GTIRB_TYPE: str = "tuple<uint64_t,sequence<tuple<uint64_t,UUID>>>"

    @property
    def fields(self) -> List[Tuple[int, Optional[AbstractType]]]:
        return [
            (offset, _load_type(self.types, uuid))
            for (offset, uuid) in self._fields
        ]


@dataclass
class VoidType(AbstractType):
    """ Void type """

    _empty: Tuple[int] = (0,)
    GTIRB_TYPE: str = "tuple<uint8_t>"  # TODO: This should be empty


# The order of this list defines how types are encoded as variants in the GTIRB
# aux data table.
TYPE_VARIANT = [
    UnknownType,
    BoolType,
    IntType,
    CharType,
    FloatType,
    FunctionType,
    PointerType,
    ArrayType,
    StructType,
    VoidType,
    AliasType,
]


def _load_type(types: GtirbTypes, uuid: UUID) -> Optional[AbstractType]:
    """Load a type from a given GtirbTypes module
    :param types: GtirbTypes with loaded aux data tables
    :param uuid: UUID to load from aux data table
    :returns: Loaded type object
    """
    if uuid not in types.type_table.data:
        return None

    data = types.type_table.data[uuid]

    if data.index >= len(TYPE_VARIANT):
        raise ValueError(
            f"Variant index {data.index} is above supported "
            f"{len(TYPE_VARIANT)}"
        )

    return TYPE_VARIANT[data.index].from_protobuf(types, uuid)


class GtirbTypes:
    """ Object for loading and saving GTIRB type information """

    SOME_TYPE = (
        "variant<"
        + ",".join([variant.GTIRB_TYPE for variant in TYPE_VARIANT])
        + ">"
    )

    def __init__(self, module: gtirb.Module):
        self.module = module
        self.map = {}
        self._load_table()

    def _load_table(self):
        """ Load the aux data table into memory """
        if "typeTable" in self.module.aux_data:
            self.type_table = self.module.aux_data["typeTable"]
        else:
            self.type_table = gtirb.AuxData(
                {}, f"mapping<UUID,{self.SOME_TYPE}>"
            )
            self.module.aux_data["typeTable"] = self.type_table

    def get_type(self, uuid: UUID) -> Optional[AbstractType]:
        """Get a type object for a given UUID
        :param uuid: UUID to get the object of
        :returns: The object type if available, None otherwise
        """
        return self.map.get(uuid)

    @classmethod
    def build_types(cls: Type[GtirbTypes], module: gtirb.Module) -> GtirbTypes:
        """Build the GtirbTypes object froma given GTIRB Module
        :param module: Module to load GTIRB types from
        :returns: The loaded GtirbTypes object"""
        obj = cls(module)

        for key in obj.type_table.data.keys():
            obj.map[key] = _load_type(obj, key)

        return obj

    def save(self):
        """ Save the in-memory type objects to the module's aux data table """
        for (key, value) in self.map.items():
            self.type_table.data[key] = Variant(
                TYPE_VARIANT.index(type(value)), value.to_protobuf()
            )
