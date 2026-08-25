import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_URL = (
    "https://www.who.int/news/item/"
    "29-06-2020-covidtimeline"
)

DEFAULT_OUTPUT = Path(
    "resources/who-covid-timeline"
)


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def sha256_bytes(data: bytes):
    return hashlib.sha256(
        data
    ).hexdigest()


def download():
    request = Request(
        SOURCE_URL,
        headers={
            "User-Agent": (
                "COVID19-KG-Integration/1.0"
            ),
            "Accept": (
                "text/html,"
                "application/xhtml+xml"
            ),
        },
    )

    with urlopen(
        request,
        timeout=60,
    ) as response:
        content = response.read()

        headers = {
            key.lower(): value
            for key, value
            in response.headers.items()
        }

        status = getattr(
            response,
            "status",
            None,
        )

    return (
        content,
        headers,
        status,
    )


def validate(content: bytes):
    text = content.decode(
        "utf-8",
        errors="replace",
    )

    required = [
        "31 Dec 2019",
        "Wuhan",
        "11 March 2020",
        "pandemic",
    ]

    missing = [
        value
        for value in required
        if value.lower()
        not in text.lower()
    ]

    if missing:
        raise RuntimeError(
            "Downloaded WHO page did not "
            "contain expected timeline "
            "content: "
            + ", ".join(missing)
        )


def main():
    args = parse_arguments()

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Downloading {SOURCE_URL}"
    )

    (
        content,
        headers,
        status,
    ) = download()

    validate(
        content
    )

    raw_path = (
        args.output
        / "timeline.html"
    )

    raw_path.write_bytes(
        content
    )

    digest = sha256_bytes(
        content
    )

    metadata = {
        "source": (
            "World Health Organization"
        ),
        "sourceName": (
            "Listings of WHO's "
            "response to COVID-19"
        ),
        "sourceUrl": SOURCE_URL,
        "retrievedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "httpStatus": status,
        "contentType": headers.get(
            "content-type"
        ),
        "etag": headers.get(
            "etag"
        ),
        "lastModified": headers.get(
            "last-modified"
        ),
        "rawFile": (
            "timeline.html"
        ),
        "sha256": digest,
        "bytes": len(content),
    }

    metadata_path = (
        args.output
        / "source.json"
    )

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"Downloaded {len(content):,} bytes"
    )

    print(
        f"SHA-256: {digest}"
    )

    print(
        f"Raw source: {raw_path}"
    )

    print(
        f"Metadata: {metadata_path}"
    )


if __name__ == "__main__":
    main()