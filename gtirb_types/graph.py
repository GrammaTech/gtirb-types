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
from gtirb_types.types import (
    AliasType,
    FunctionType,
    GtirbTypes,
    PointerType,
    StructType,
)
from pathlib import Path
import argparse
import gtirb
import graphviz


def main():
    parser = argparse.ArgumentParser(
        description="Graph the type information found in a GTIRB file"
    )
    parser.add_argument("gtirb_in", type=Path, help="GTIRB file to read")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "Location to write graph, otherwise graphviz is displayed to "
            "console"
        ),
    )
    args = parser.parse_args()

    if not args.gtirb_in.exists():
        raise FileNotFoundError(f"{args.gtirb_in} does not exist")

    ir = gtirb.IR.load_protobuf(str(args.gtirb_in))
    module = ir.modules[0]
    types = GtirbTypes.build_types(module)

    dot = graphviz.Digraph(comment=f"Types of {args.gtirb_in.name}")
    for (uuid, type_) in types.map.items():
        dot.node(str(uuid), label=str(type_))

        if isinstance(type_, StructType):
            for (_, field_id) in type_._fields:
                dot.edge(str(uuid), str(field_id))
        elif isinstance(type_, AliasType):
            dot.edge(str(uuid), str(type_._pointed_to))
        elif isinstance(type_, PointerType):
            dot.edge(str(uuid), str(type_._pointed_to))
        elif isinstance(type_, FunctionType):
            dot.edge(str(uuid), str(type_._return_type))

            for arg in type_._argument_types:
                dot.edge(str(uuid), str(arg))

    if args.output is None:
        print(dot.source)
    else:
        dot.render(str(args.output), view=True)


if __name__ == "__main__":
    main()
