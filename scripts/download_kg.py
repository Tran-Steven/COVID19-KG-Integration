import hashlib
import json
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


URL = "https://data.monarchinitiative.org/monarch-kg/latest/monarch-kg.tar.gz"
OUTPUT_DIRECTORY = Path("resources/monarch-kg")


def sha256(path: Path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def download(destination: Path):
    request = Request(
        URL,
        headers={
            "User-Agent": "COVID19-KG-Integration/1.0",
        },
    )

    with urlopen(request) as response:
        with destination.open("wb") as file:
            shutil.copyfileobj(response, file)


def find_file(archive: tarfile.TarFile, kind: str):
    members = [
        member
        for member in archive.getmembers()
        if member.isfile()
    ]

    preferred_names = {
        f"{kind}.tsv",
        f"monarch-kg_{kind}.tsv",
        f"merged-kg_{kind}.tsv",
        f"merged_kg_{kind}.tsv",
    }

    matches = [
        member
        for member in members
        if Path(member.name).name.lower() in preferred_names
    ]

    if len(matches) == 1:
        return matches[0]

    fallback = [
        member
        for member in members
        if Path(member.name).name.lower().endswith(
            f"_{kind}.tsv"
        )
    ]

    if len(fallback) == 1:
        return fallback[0]

    raise RuntimeError(
        f"Unable to uniquely identify {kind}.tsv in Monarch archive"
    )


def extract_file(
    archive: tarfile.TarFile,
    member: tarfile.TarInfo,
    destination: Path,
):
    source = archive.extractfile(member)

    if source is None:
        raise RuntimeError(
            f"Unable to extract {member.name}"
        )

    with source:
        with destination.open("wb") as output:
            shutil.copyfileobj(source, output)


def main():
    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        archive_path = (
            Path(temporary_directory)
            / "monarch-kg.tar.gz"
        )

        print(f"Downloading {URL}")

        download(archive_path)

        print("Download complete")

        with tarfile.open(
            archive_path,
            "r:gz",
        ) as archive:
            nodes_member = find_file(
                archive,
                "nodes",
            )

            edges_member = find_file(
                archive,
                "edges",
            )

            nodes_path = (
                OUTPUT_DIRECTORY
                / "nodes.tsv"
            )

            edges_path = (
                OUTPUT_DIRECTORY
                / "edges.tsv"
            )

            extract_file(
                archive,
                nodes_member,
                nodes_path,
            )

            extract_file(
                archive,
                edges_member,
                edges_path,
            )

        metadata = {
            "source": "Monarch Initiative Knowledge Graph",
            "sourceUrl": URL,
            "downloadedAt": datetime.now(
                timezone.utc
            ).isoformat(),
            "archiveSha256": sha256(
                archive_path
            ),
            "nodesArchivePath": nodes_member.name,
            "edgesArchivePath": edges_member.name,
            "nodesSha256": sha256(
                nodes_path
            ),
            "edgesSha256": sha256(
                edges_path
            ),
        }

        metadata_path = (
            OUTPUT_DIRECTORY
            / "source.json"
        )

        metadata_path.write_text(
            json.dumps(
                metadata,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(f"Nodes: {nodes_path}")
        print(f"Edges: {edges_path}")
        print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()