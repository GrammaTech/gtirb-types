from functools import cached_property
from typing import Set, Tuple
from .types import (
    AbstractType,
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
)
import networkx
import uuid


class GTIRBLattice:
    """Lattice for GTIRB types that encode C types"""

    TOP = "⊤"
    BOT = "⊥"

    BOOL = "bool"
    NUM = "num"
    INT = "int"
    UINT = "uint"
    CHAR = "char"
    FLOAT = "float"
    VOID = "void"

    int_sizes = {8, 16, 32, 64}
    float_sizes = {32, 64}

    NUM_N = {size: f"num{size}_t" for size in int_sizes}
    INT_N = {size: f"int{size}_t" for size in int_sizes}
    CHAR_N = {size: f"char{size}_t" for size in int_sizes}
    UINT_N = {size: f"uint{size}_t" for size in int_sizes}
    FLOAT_N = {size: f"float{size}_t" for size in float_sizes}

    def __init__(self):
        self._compare_cache = {}

        self._graph = networkx.DiGraph()
        self._graph.add_edge(self.TOP, self.NUM)
        self._graph.add_edge(self.TOP, self.FLOAT)
        self._graph.add_edge(self.TOP, self.VOID)

        self._graph.add_edge(self.NUM, self.INT)
        self._graph.add_edge(self.NUM, self.UINT)
        self._graph.add_edge(self.UINT, self.CHAR)
        self._graph.add_edge(self.UINT, self.BOOL)

        for size in self.int_sizes:
            self._graph.add_edge(self.NUM, self.NUM_N[size])
            self._graph.add_edge(self.INT, self.INT_N[size])
            self._graph.add_edge(self.UINT, self.UINT_N[size])

            self._graph.add_edge(self.UINT_N[size], self.CHAR_N[size])

            self._graph.add_edge(self.NUM_N[size], self.INT_N[size])
            self._graph.add_edge(self.NUM_N[size], self.UINT_N[size])

            self._graph.add_edge(self.INT_N[size], self.BOT)
            self._graph.add_edge(self.CHAR_N[size], self.BOT)
            self._graph.add_edge(self.UINT_N[size], self.BOT)

        for size in self.float_sizes:
            self._graph.add_edge(self.FLOAT, self.FLOAT_N[size])
            self._graph.add_edge(self.FLOAT_N[size], self.BOT)

        self._graph.add_edge(self.CHAR, self.BOT)
        self._graph.add_edge(self.BOOL, self.BOT)
        self._graph.add_edge(self.FLOAT, self.BOT)
        self._graph.add_edge(self.INT, self.BOT)
        self._graph.add_edge(self.UINT, self.BOT)
        self._graph.add_edge(self.VOID, self.BOT)

        self._lengths = dict(networkx.shortest_path_length(self._graph))

    @classmethod
    def from_type(cls, type_obj: AbstractType) -> str:
        """Translate a type object to a lattice type
        :param type_obj: Type object to translate
        :returns: String that represents an object in the lattice
        """
        if isinstance(type_obj, UnknownType):
            return cls.BOT
        elif isinstance(type_obj, BoolType):
            return cls.BOOL
        elif isinstance(type_obj, IntType):
            return f"{'' if type_obj.is_signed else 'u'}int{type_obj.size*8}_t"
        elif isinstance(type_obj, CharType):
            return f"char{type_obj.size*8}_t"
        elif isinstance(type_obj, FloatType):
            return f"float{type_obj.size*8}_t"
        elif isinstance(
            type_obj, (FunctionType, PointerType, ArrayType, StructType)
        ):
            raise ValueError(f"{type_obj} invalid for lattice types")
        elif isinstance(type_obj, VoidType):
            return cls.VOID
        elif isinstance(type_obj, AliasType):
            pointed = type_obj.pointed_to

            if not pointed:
                raise ValueError(f"Alias type {type_obj} has no pointed-to")

            return cls.from_type(pointed)
        else:
            print(f"Unknown object {type_obj}")
            raise NotImplementedError()

    @cached_property
    def lattice_height(self) -> int:
        """Get the height of the lattice being used"""
        return networkx.dag_longest_path_length(self._graph)

    def compare_lattice(self, lhs: str, rhs: str) -> int:
        """Get the height between two lattice elments
        :param lhs: Left hand side type to compare
        :param rhs: Right hand side type to compare
        :returns: Height between two lattice elements
        """
        if rhs in self._lengths[lhs]:
            return self._lengths[lhs][rhs]
        elif lhs in self._lengths[rhs]:
            return self._lengths[rhs][lhs]
        else:
            return self.lattice_height

    def pointer_accuracy(self, lhs: AbstractType, rhs: AbstractType) -> float:
        """Compute pointer accuracy between types
        :param lhs: Left hand side type to compare
        :param rhs: Right hand side type to compare
        :param visited: Set of pairs already visited
        :returns: Multi-level pointer accuracy metric
        """
        num_correct = 0
        total_number = 0

        while lhs and isinstance(lhs, PointerType):
            if rhs and isinstance(rhs, PointerType):
                rhs = rhs.pointed_to
                num_correct += 1
            else:
                rhs = None

            total_number += 1
            lhs = lhs.pointed_to

        total_number += 1

        try:
            if self.from_type(lhs) == self.from_type(rhs):
                num_correct += 1
        except (ValueError, NotImplementedError):
            pass

        return num_correct / total_number

    def compare_structs(
        self,
        lhs: StructType,
        rhs: StructType,
        visited: Set[Tuple[uuid.UUID, uuid.UUID]],
    ) -> float:
        """Do a structure-to-structure comparison
        :param lhs: Left hand side structure
        :param rhs: Right hand side structure
        :param visited: Set of pairs already visited
        :returns: Score of structure similarity
        """
        if len(lhs.fields) == 0 and len(rhs.fields) == 0:
            return 0
        elif len(lhs.fields) == 0 or len(rhs.fields) == 0:
            return self.lattice_height
        lhs_fieldcount = 1 - 1 / len(lhs.fields)
        rhs_fieldcount = 1 - 1 / len(rhs.fields)
        field_ratio = abs(lhs_fieldcount - rhs_fieldcount)

        lhs_fields = dict(lhs.fields)
        rhs_fields = dict(rhs.fields)

        valid_offsets = {off for off, _ in lhs.fields} | {
            off for off, _ in rhs.fields
        }

        avg = 0.0

        for i in valid_offsets:
            if i in lhs_fields and i in rhs_fields:
                avg += self.compare_types(
                    lhs_fields[i], rhs_fields[i], visited
                )
            else:
                avg += self.lattice_height

        avg /= len(valid_offsets)
        return field_ratio + avg / self.lattice_height

    def compare_functions(
        self,
        lhs: FunctionType,
        rhs: FunctionType,
        visited: Set[Tuple[uuid.UUID, uuid.UUID]],
    ) -> float:
        """Do a function-wise comparison of types
        :param lhs: Left hand side function type
        :param rhs: Right hand side function type
        :param visited: Set of pairs already visited
        :returns: Average score of types
        """
        if not lhs.return_type or not rhs.return_type:
            raise ValueError(f"Missing return types for {lhs}/{rhs}")

        ret_score = self.compare_types(lhs.return_type, rhs.return_type)

        if len(lhs.argument_types) == 0 and len(rhs.argument_types) == 0:
            return ret_score

        # Get all argument scores
        arg_scores = []

        for lhs_arg, rhs_arg in zip(lhs.argument_types, rhs.argument_types):
            if not lhs_arg or not rhs_arg:
                raise ValueError(
                    f"Missing argument types for {lhs_arg}/{rhs_arg}"
                )

            arg_scores.append(self.compare_types(lhs_arg, rhs_arg, visited))

        # Missing arguments are considered TOP
        for _ in range(abs(len(lhs.argument_types) - len(rhs.argument_types))):
            arg_scores.append(self.lattice_height)

        all_scores = arg_scores + [ret_score]
        return sum(all_scores) / len(all_scores)

    def compare_types(
        self,
        lhs: AbstractType,
        rhs: AbstractType,
        visited: Set[Tuple[uuid.UUID, uuid.UUID]] = None,
    ) -> float:
        """Compare type information for gtirb-types objects
        :param lhs: Left hand side structure
        :param rhs: Right hand side structure
        :param visited: Set of pairs already visited
        :returns: Score of structure similarity
        """
        if visited is None:
            visited = set()
        elif (lhs.uuid, rhs.uuid) in visited:
            return 0.0

        visited = visited | {(lhs.uuid, rhs.uuid)}

        if isinstance(lhs, AliasType):
            assert lhs.pointed_to
            return self.compare_types(lhs.pointed_to, rhs, visited)
        elif isinstance(rhs, AliasType):
            assert rhs.pointed_to
            return self.compare_types(lhs, rhs.pointed_to, visited)

        if isinstance(lhs, StructType) and isinstance(rhs, StructType):
            return self.compare_structs(lhs, rhs, visited)
        elif isinstance(lhs, FunctionType) and isinstance(rhs, FunctionType):
            return self.compare_functions(lhs, rhs, visited)
        elif isinstance(lhs, PointerType) and isinstance(rhs, PointerType):
            assert lhs.pointed_to
            assert rhs.pointed_to
            return self.compare_types(lhs.pointed_to, rhs.pointed_to, visited)
        elif isinstance(
            lhs, (FunctionType, PointerType, ArrayType, StructType)
        ) or isinstance(
            rhs, (FunctionType, PointerType, ArrayType, StructType)
        ):
            # TODO - Is this correct? Probably not
            return self.lattice_height
        else:
            lhs_lat = self.from_type(lhs)
            rhs_lat = self.from_type(rhs)

            return self.compare_lattice(lhs_lat, rhs_lat)
