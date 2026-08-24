import argparse

from app.database import Neo4jClient
from app.ingestion.kgx_importer import KGXImporter


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--nodes",
        required=True,
    )

    parser.add_argument(
        "--edges",
        required=True,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
    )

    parser.add_argument(
        "--clear",
        action="store_true",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    database = Neo4jClient()

    try:
        importer = KGXImporter(
            database,
            batch_size=args.batch_size,
        )

        result = importer.import_graph(
            nodes_path=args.nodes,
            edges_path=args.edges,
            clear=args.clear,
        )

        print(
            f"Imported {result['nodes']} nodes "
            f"and {result['edges']} edges."
        )
    finally:
        database.close()


if __name__ == "__main__":
    main()