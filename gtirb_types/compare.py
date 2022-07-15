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

            self._graph.add_edge(self.NUM_N[size], self.INT_N[size])
            self._graph.add_edge(self.NUM_N[size], self.UINT_N[size])

            self._graph.add_edge(self.INT_N[size], self.BOT)
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
            raise NotImplementedError()

    @property
    def lattice_height(self) -> int:
        """Get the height of the lattice being used"""
        return self._lengths[self.TOP][self.BOT]

    def compare_types(self, lhs: AbstractType, rhs: AbstractType) -> int:
        """Get the height between two types
        :param lhs: Left hand side type to compare
        :param rhs: Right hand side type to compare
        :returns: Height between two types"""
        lhs_s = self.from_type(lhs)
        rhs_s = self.from_type(rhs)

        if rhs_s in self._lengths[lhs_s]:
            return self._lengths[lhs_s][rhs_s]
        elif lhs_s in self._lengths[rhs_s]:
            return self._lengths[rhs_s][lhs_s]
        else:
            return self.lattice_height

    def pointer_accuracy(self, lhs: AbstractType, rhs: AbstractType) -> float:
        """Compute pointer accuracy between types
        :param lhs: Left hand side type to compare
        :param rhs: Right hand side type to compare
        :returns: Multi-level pointer accuracy metric"""
        num_correct = 0
        total_number = 0

        while lhs and isinstance(lhs, PointerType):
            print(type(lhs), type(rhs))
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
