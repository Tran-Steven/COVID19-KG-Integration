import argparse
import csv
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin


DEFAULT_INPUT = Path(
    "resources/who-covid-timeline/timeline.html"
)

DEFAULT_SOURCE = Path(
    "resources/who-covid-timeline/source.json"
)

DEFAULT_OUTPUT = Path(
    "resources/who-covid-timeline/events.tsv"
)

DEFAULT_METADATA = Path(
    "resources/who-covid-timeline/transform.json"
)

SOURCE_URL = (
    "https://www.who.int/news/item/"
    "29-06-2020-covidtimeline"
)

DATE_PATTERN = re.compile(
    r"^(?P<start>\d{1,2})"
    r"(?:\s*[-–]\s*(?P<end>\d{1,2}))?"
    r"\s+(?P<month>[A-Za-z]+)"
    r"\s+(?P<year>\d{4})$"
)

EVENT_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL,
    SOURCE_URL,
)


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_METADATA,
    )

    return parser.parse_args()


def normalize_whitespace(
    value: str,
):
    return " ".join(
        value.replace(
            "\xa0",
            " ",
        ).split()
    )


def sha256_bytes(
    data: bytes,
):
    return hashlib.sha256(
        data
    ).hexdigest()


def sha256_file(
    path: Path,
):
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as file:
        for chunk in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def parse_date_label(
    label: str,
):
    normalized = normalize_whitespace(
        label
    )

    match = DATE_PATTERN.fullmatch(
        normalized
    )

    if not match:
        return None

    start_day = int(
        match.group(
            "start"
        )
    )

    end_value = match.group(
        "end"
    )

    end_day = (
        int(end_value)
        if end_value
        else start_day
    )

    month = match.group(
        "month"
    )

    year = int(
        match.group(
            "year"
        )
    )

    start_date = parse_date(
        start_day,
        month,
        year,
    )

    end_date = parse_date(
        end_day,
        month,
        year,
    )

    if (
        start_date is None
        or end_date is None
    ):
        return None

    return {
        "label": normalized,
        "start": start_date,
        "end": end_date,
    }


def parse_date(
    day: int,
    month: str,
    year: int,
):
    value = (
        f"{day} {month} {year}"
    )

    for format_string in [
        "%d %B %Y",
        "%d %b %Y",
    ]:
        try:
            parsed = datetime.strptime(
                value,
                format_string,
            )

            return parsed.date().isoformat()
        except ValueError:
            continue

    return None


class TimelineParser(
    HTMLParser
):
    def __init__(
        self,
        source_url: str,
    ):
        super().__init__(
            convert_charrefs=True
        )

        self.source_url = source_url

        self.in_h2 = False
        self.h2_depth = 0
        self.h2_parts = []

        self.current_date = None

        self.block_tag = None
        self.block_depth = 0
        self.block_parts = []
        self.block_links = []

        self.blocks = []

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        tag = tag.lower()

        if self.in_h2:
            self.h2_depth += 1
            return

        if tag == "h2":
            self.in_h2 = True
            self.h2_depth = 1
            self.h2_parts = []
            return

        if self.block_tag:
            self.block_depth += 1

            if tag == "a":
                href = dict(
                    attrs
                ).get(
                    "href"
                )

                if href:
                    self.block_links.append(
                        urljoin(
                            self.source_url,
                            href,
                        )
                    )

            return

        if (
            self.current_date
            and tag in {
                "p",
                "li",
            }
        ):
            self.block_tag = tag
            self.block_depth = 1
            self.block_parts = []
            self.block_links = []

    def handle_startendtag(
        self,
        tag,
        attrs,
    ):
        if (
            self.block_tag
            and tag.lower() == "a"
        ):
            href = dict(
                attrs
            ).get(
                "href"
            )

            if href:
                self.block_links.append(
                    urljoin(
                        self.source_url,
                        href,
                    )
                )

    def handle_endtag(
        self,
        tag,
    ):
        tag = tag.lower()

        if self.in_h2:
            self.h2_depth -= 1

            if self.h2_depth == 0:
                heading = (
                    normalize_whitespace(
                        "".join(
                            self.h2_parts
                        )
                    )
                )

                self.current_date = (
                    parse_date_label(
                        heading
                    )
                )

                self.in_h2 = False
                self.h2_parts = []

            return

        if self.block_tag:
            self.block_depth -= 1

            if self.block_depth == 0:
                self.finish_block()

    def handle_data(
        self,
        data,
    ):
        if self.in_h2:
            self.h2_parts.append(
                data
            )
            return

        if self.block_tag:
            self.block_parts.append(
                data
            )

    def finish_block(
        self,
    ):
        text = normalize_whitespace(
            "".join(
                self.block_parts
            )
        )

        if text:
            self.blocks.append(
                {
                    "date": dict(
                        self.current_date
                    ),
                    "text": text,
                    "links": unique(
                        self.block_links
                    ),
                }
            )

        self.block_tag = None
        self.block_depth = 0
        self.block_parts = []
        self.block_links = []


def unique(
    values: list[str],
):
    result = []
    seen = set()

    for value in values:
        if value in seen:
            continue

        seen.add(
            value
        )

        result.append(
            value
        )

    return result


def event_id(
    date_label: str,
    text: str,
):
    value = (
        f"{date_label}|{text}"
    )

    identifier = uuid.uuid5(
        EVENT_NAMESPACE,
        value,
    )

    return (
        f"urn:uuid:{identifier}"
    )


def transform_blocks(
    blocks: list[dict],
):
    events = []

    sequence_by_date = {}

    for block in blocks:
        date = block[
            "date"
        ]

        date_label = date[
            "label"
        ]

        sequence = (
            sequence_by_date.get(
                date_label,
                0,
            )
            + 1
        )

        sequence_by_date[
            date_label
        ] = sequence

        events.append(
            {
                "id": event_id(
                    date_label,
                    block["text"],
                ),
                "date_label": date_label,
                "date_start": date[
                    "start"
                ],
                "date_end": date[
                    "end"
                ],
                "sequence": sequence,
                "text": block[
                    "text"
                ],
                "links": json.dumps(
                    block[
                        "links"
                    ],
                    ensure_ascii=False,
                    separators=(
                        ",",
                        ":",
                    ),
                ),
            }
        )

    return events


def validate_events(
    events: list[dict],
):
    if not events:
        raise RuntimeError(
            "No dated WHO timeline "
            "events were extracted."
        )

    checks = [
        (
            "2019-12-31",
            "wuhan",
        ),
        (
            "2020-03-11",
            "pandemic",
        ),
    ]

    for date, keyword in checks:
        matches = [
            event
            for event in events
            if (
                event[
                    "date_start"
                ] == date
                and keyword
                in event[
                    "text"
                ].lower()
            )
        ]

        if not matches:
            raise RuntimeError(
                "Expected WHO timeline "
                "event was not extracted: "
                f"{date} / {keyword}"
            )


def write_events(
    path: Path,
    events: list[dict],
):
    fieldnames = [
        "id",
        "date_label",
        "date_start",
        "date_end",
        "sequence",
        "text",
        "links",
    ]

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
        )

        writer.writeheader()

        for event in events:
            writer.writerow(
                event
            )


def main():
    args = parse_arguments()

    source = json.loads(
        args.source.read_text(
            encoding="utf-8"
        )
    )

    raw_bytes = (
        args.input.read_bytes()
    )

    actual_hash = sha256_bytes(
        raw_bytes
    )

    expected_hash = source.get(
        "sha256"
    )

    if (
        expected_hash
        and actual_hash
        != expected_hash
    ):
        raise RuntimeError(
            "WHO timeline HTML hash "
            "does not match source.json."
        )

    source_url = (
        source.get(
            "sourceUrl"
        )
        or SOURCE_URL
    )

    parser = TimelineParser(
        source_url
    )

    parser.feed(
        raw_bytes.decode(
            "utf-8",
            errors="replace",
        )
    )

    parser.close()

    events = transform_blocks(
        parser.blocks
    )

    validate_events(
        events
    )

    write_events(
        args.output,
        events,
    )

    dates = [
        event[
            "date_start"
        ]
        for event in events
    ]

    metadata = {
        "source": (
            "World Health Organization"
        ),
        "sourceUrl": source_url,
        "inputFile": str(
            args.input
        ),
        "inputSha256": actual_hash,
        "outputFile": str(
            args.output
        ),
        "outputSha256": sha256_file(
            args.output
        ),
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "eventCount": len(
            events
        ),
        "firstEventDate": min(
            dates
        ),
        "lastEventDate": max(
            dates
        ),
        "representation": (
            "dated source statements"
        ),
        "semanticInterpretation": False,
    }

    args.metadata.write_text(
        json.dumps(
            metadata,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"Events extracted: {len(events)}"
    )

    print(
        "Date range: "
        f"{metadata['firstEventDate']} "
        "to "
        f"{metadata['lastEventDate']}"
    )

    print(
        f"Events: {args.output}"
    )

    print(
        f"Metadata: {args.metadata}"
    )


if __name__ == "__main__":
    main()