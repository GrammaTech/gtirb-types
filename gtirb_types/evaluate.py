from .compare import GTIRBLattice
from .display import c_str
from gtirb_functions import Function
from pathlib import Path
from .types import (
    AbstractType,
    ArrayType,
    FunctionType,
    GtirbTypes,
    PointerType,
    StructType,
)
from typing import Dict
import argparse
import gtirb
import uuid


def aggregate_user_def(
    type_: AbstractType, aggregate: Dict[uuid.UUID, AbstractType]
):
    if type_.uuid in aggregate or not type_:
        return

    if isinstance(type_, StructType):
        aggregate[type_.uuid] = type_

        for _, field_type in type_.fields:
            aggregate_user_def(field_type, aggregate)
    elif isinstance(type_, PointerType):
        aggregate_user_def(type_.pointed_to, aggregate)
    elif isinstance(type_, FunctionType):
        aggregate[type_.uuid] = type_
        aggregate_user_def(type_.return_type, aggregate)

        for arg in type_.argument_types:
            aggregate_user_def(arg, aggregate)
    elif isinstance(type_, ArrayType):
        aggregate_user_def(type_.element_type, aggregate)


def main():
    parser = argparse.ArgumentParser(
        description="Do a function-wise type comparison of the inputs"
    )
    parser.add_argument(
        "ground_truth", type=Path, help="GTIRB with ground truth"
    )
    parser.add_argument(
        "inferred", type=Path, help="GTIRB with inferred types"
    )
    args = parser.parse_args()

    ground_truth_ir = gtirb.IR.load_protobuf(str(args.ground_truth))
    inferred_ir = gtirb.IR.load_protobuf(str(args.inferred))

    if len(ground_truth_ir.modules) != 1 or len(inferred_ir.modules) != 1:
        raise ValueError("Currently single-module IRs supported only")

    ground_truth_mod = ground_truth_ir.modules[0]
    inferred_mod = inferred_ir.modules[0]

    ground_truth_types = GtirbTypes(ground_truth_mod)
    inferred_types = GtirbTypes(inferred_mod)

    ground_truth_funcs = {
        func.get_name(): func
        for func in Function.build_functions(ground_truth_mod)
    }

    inferred_funcs = {
        func.get_name(): func
        for func in Function.build_functions(inferred_mod)
    }

    common_funcs = set(inferred_funcs.keys()) & set(ground_truth_funcs.keys())
    all_funcs = set(inferred_funcs.keys()) | set(ground_truth_funcs.keys())

    if len(common_funcs) < len(all_funcs) / 2:
        raise ValueError("Less than half of functions are common")

    lattice = GTIRBLattice()
    scores = []

    for func in common_funcs:
        ground_truth_func = ground_truth_funcs[func]
        inferred_func = inferred_funcs[func]

        if (
            ground_truth_func.uuid not in ground_truth_types.prototypes
            or inferred_func.uuid not in inferred_types.prototypes
        ):
            print("Skipping", func)
            continue

        ground_truth_proto = ground_truth_types.prototypes[
            ground_truth_func.uuid
        ]
        inferred_proto = inferred_types.prototypes[inferred_func.uuid]

        ground_truth_type = ground_truth_types.get_type(ground_truth_proto)
        inferred_type = inferred_types.get_type(inferred_proto)

        print("Function:", func)
        user_defs = {}
        aggregate_user_def(inferred_type, user_defs)
        for type_ in user_defs.values():
            if isinstance(type_, StructType):
                try:
                    print(c_str(type_))
                except RecursionError:
                    print(f"struct {type_.name} {{ <inf> }}")

        try:
            print("Inferred", c_str(inferred_type))
        except RecursionError:
            print("Inferred: <recursion error>")

        score = lattice.compare_types(ground_truth_type, inferred_type)
        print("Score:", score)
        print("Original", c_str(ground_truth_type))

        scores.append(score)
        print()

    print("Average:", sum(scores) / len(scores))


if __name__ == "__main__":
    main()
