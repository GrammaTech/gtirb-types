from pathlib import Path
import argparse
import gtirb


AUX_TO_REMOVE = {
    "typeTable",
    "typeNameTable",
    "prototypeTable",
}


def main():
    parser = argparse.ArgumentParser(
        description="Remove gtirb-types information from a GTIRB file"
    )
    parser.add_argument("in_gtirb", type=Path, help="Input GTIRB")
    parser.add_argument("out_gtirb", type=Path, help="Output GTIRB")
    args = parser.parse_args()

    ir = gtirb.IR.load_protobuf(str(args.in_gtirb))

    for module in ir.modules:
        for aux in AUX_TO_REMOVE:
            if aux in module.aux_data:
                del module.aux_data[aux]

    ir.save_protobuf(str(args.out_gtirb))


if __name__ == "__main__":
    main()
