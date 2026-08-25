import argparse
import csv
import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from pypdf import PdfReader

WHO = "World Health Organization"
WHO_INFORES = "infores:who"
COVID_ID = "MONDO:0100096"
SARS_ID = "NCBITaxon:2697049"
LONG_COVID_ID = "MONDO:0100320"
VACCINATION_ID = "covidkg:who:concept:covid-19-vaccination"
DEFAULT_OUTPUT = Path("resources/who-covid-kg")
DEFAULT_HISTORY = Path("resources/who-covid-history")
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://www.who.int/covid-19-verification-kg")

SOURCES = [
    {
        "id": "covid_fact_sheet",
        "name": "Coronavirus disease (COVID-19) fact sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/coronavirus-disease-(covid-19)",
        "date": "2025-11-27",
        "topic": "covid_basics",
        "expected": ["27 November 2025", "SARS-CoV-2", "Transmission", "Vaccines"],
        "stop": ["WHO response"],
        "inline": ["Symptoms", "Transmission", "Treatment", "Prevention", "Vaccines"],
    },
    {
        "id": "long_covid_fact_sheet",
        "name": "Post COVID-19 condition (long COVID) fact sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/post-covid-19-condition-(long-covid)",
        "date": "2025-02-26",
        "topic": "long_covid",
        "expected": ["26 February 2025", "post COVID-19 condition", "Risk factors", "Symptoms"],
        "stop": ["References"],
        "inline": [],
    },
    {
        "id": "variants",
        "name": "Tracking SARS-CoV-2 variants",
        "url": "https://www.who.int/activities/tracking-SARS-CoV-2-variants",
        "date": "2026-07-28",
        "topic": "variants",
        "expected": ["28 July 2026", "variants of interest", "variants under monitoring", "JN.1"],
        "stop": ["News"],
        "inline": [],
    },
    {
        "id": "vaccine_policy",
        "name": "WHO COVID-19 vaccination policy page",
        "url": "https://www.who.int/teams/immunization-vaccines-and-biologicals/diseases/covid-19-(corona-virus)",
        "date": "2026-07-31",
        "topic": "vaccination",
        "expected": ["March 2026", "routine COVID-19 vaccination", "31 July 2026"],
        "start": "While the global burden of severe COVID-19 has declined",
        "stop": ["Q&A"],
        "inline": [],
    },
    {
        "id": "vaccine_position",
        "name": "WHO position paper on COVID-19 vaccines - July 2026",
        "url": "https://www.who.int/publications/i/item/who-wer10130-138-156",
        "date": "2026-07-31",
        "topic": "vaccination",
        "expected": ["31 July 2026", "current policy recommendations", "COVID-19 vaccines"],
        "stop": ["WHO Team"],
        "inline": [],
    },
    {
        "id": "global_risk_v10",
        "name": "WHO COVID-19 Global Risk Assessment- Version 10",
        "url": "https://www.who.int/publications/m/item/covid-19-global-risk-assessment--version-10",
        "date": "2026-08-06",
        "topic": "current_risk",
        "expected": ["6 August 2026", "global public health risk", "remains moderate"],
        "stop": ["WHO Team"],
        "inline": [],
    },
    {
        "id": "sago_origins",
        "name": "Independent assessment of the origins of SARS-CoV-2",
        "url": "https://www.who.int/publications/m/item/independent-assessment-of-the-origins-of-sars-cov-2-from-the-scientific-advisory-group-for-the-origins-of-novel-pathogens",
        "date": "2025-06-27",
        "topic": "origin",
        "expected": ["27 June 2025", "origins of SARS", "SAGO"],
        "stop": ["Related link"],
        "inline": [],
        "pdf": True,
    },
]

TOPICS = {
    "covid_fact_sheet": {
        "Key facts": "covid_basics",
        "Overview": "covid_basics",
        "Symptoms": "symptoms",
        "Transmission": "transmission",
        "Treatment": "treatment",
        "Prevention": "prevention",
        "Vaccines": "vaccination",
    },
    "long_covid_fact_sheet": {
        "Key facts": "long_covid",
        "Overview": "long_covid",
        "Scope of the problem": "long_covid_epidemiology",
        "Risk factors": "long_covid_risk",
        "Symptoms": "long_covid_symptoms",
        "Impact": "long_covid_impact",
        "Recovery": "long_covid_recovery",
        "Treatments": "long_covid_treatment",
        "Self-care": "long_covid_self_care",
        "Prevention": "long_covid_prevention",
    },
}


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--reuse", action="store_true")
    return parser.parse_args()


def norm(value):
    return " ".join(str(value).replace("\xa0", " ").split())


def canon(value):
    return norm(value).lower().rstrip(" .;:")


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:100] or "item"


def local_id(kind, name):
    return f"covidkg:who:{kind}:{slug(name)}"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url):
    request = Request(
        url,
        headers={
            "User-Agent": "COVID19-KG-Integration/1.0",
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
        },
    )
    with urlopen(request, timeout=90) as response:
        return (
            response.read(),
            {k.lower(): v for k, v in response.headers.items()},
            getattr(response, "status", None),
            response.geturl(),
        )


def pdf_link(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, anchor["href"])
        text = norm(anchor.get_text(" ", strip=True)).lower()
        if ".pdf" in href.lower() and ("download" in text or "cdn.who.int" in href.lower()):
            return href
    raise RuntimeError(f"No WHO PDF link found on {base_url}")


def html_text(content):
    return norm(
        BeautifulSoup(
            content,
            "html.parser",
        ).get_text(
            " ",
            strip=True,
        )
    )


def acquire(source, raw_dir, reuse):
    path = raw_dir / f"{source['id']}.html"
    if reuse and path.exists():
        content, headers, status, final_url = path.read_bytes(), {}, None, source["url"]
    else:
        content, headers, status, final_url = fetch(source["url"])
        path.write_bytes(content)
    text = html_text(content)
    missing = [p for p in source["expected"] if p.lower() not in text.lower()]
    if missing:
        raise RuntimeError(f"{source['id']} missing expected content: {', '.join(missing)}")
    meta = {
        "id": source["id"],
        "name": source["name"],
        "sourceUrl": source["url"],
        "finalUrl": final_url,
        "sourceDate": source["date"],
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
        "httpStatus": status,
        "contentType": headers.get("content-type"),
        "etag": headers.get("etag"),
        "lastModified": headers.get("last-modified"),
        "rawFile": str(path),
        "sha256": sha_bytes(content),
        "bytes": len(content),
    }
    if source.get("pdf"):
        url = pdf_link(content, final_url)
        pdf_path = raw_dir / f"{source['id']}.pdf"
        if reuse and pdf_path.exists():
            pdf, pdf_headers, pdf_status, pdf_final = pdf_path.read_bytes(), {}, None, url
        else:
            pdf, pdf_headers, pdf_status, pdf_final = fetch(url)
            if not pdf.startswith(b"%PDF"):
                raise RuntimeError(f"WHO download is not a PDF: {url}")
            pdf_path.write_bytes(pdf)
        meta.update(
            {
                "pdfUrl": url,
                "pdfFinalUrl": pdf_final,
                "pdfHttpStatus": pdf_status,
                "pdfContentType": pdf_headers.get("content-type"),
                "pdfFile": str(pdf_path),
                "pdfSha256": sha_bytes(pdf),
                "pdfBytes": len(pdf),
            }
        )
    return content, meta


def statement_id(source_id, section, text):
    return f"urn:uuid:{uuid.uuid5(NAMESPACE, f'{source_id}|{section}|{text}')}"


def tag_links(tag, base_url):
    result = []
    for anchor in tag.find_all("a", href=True):
        value = urljoin(base_url, anchor["href"])
        if value not in result:
            result.append(value)
    return result


def article_statements(source, content, raw_file):
    soup = BeautifulSoup(content, "html.parser")
    if source.get("start"):
        needle = source["start"].lower()
        start = soup.find(
            lambda tag: tag.name in {"p", "li", "h2", "h3", "h4"}
            and needle in norm(tag.get_text(" ", strip=True)).lower()
        )
    else:
        start = soup.find("h1")
    if start is None:
        raise RuntimeError(f"Could not find article body for {source['id']}")
    current = "Overview"
    stop = {canon(v) for v in source.get("stop", [])}
    inline = {canon(v): v for v in source.get("inline", [])}
    tags = [start, *start.find_all_next(["h2", "h3", "h4", "p", "li"])]
    result, seen = [], set()
    for tag in tags:
        text = norm(tag.get_text(" ", strip=True))
        if not text:
            continue
        if canon(text) in stop:
            break
        if tag.name in {"h2", "h3", "h4"}:
            current = text
            continue
        if canon(text) in inline:
            current = inline[canon(text)]
            continue
        if tag.name == "li" and tag.find_parent("li") is not None:
            continue
        if len(text) < 15 or (current, text) in seen:
            continue
        seen.add((current, text))
        result.append(
            {
                "id": statement_id(source["id"], current, text),
                "source_id": source["id"],
                "source_name": source["name"],
                "source_url": source["url"],
                "source_date": source["date"],
                "section": current,
                "topic": TOPICS.get(source["id"], {}).get(current, source["topic"]),
                "kind": "html_statement",
                "text": text,
                "links": tag_links(tag, source["url"]),
                "raw_file": raw_file,
            }
        )
    return result


def clean_pdf_text(value):
    value = str(value)
    value = value.replace("\u00ad", "")
    value = value.translate(
        str.maketrans(
            {
                "‐": "-",
                "‑": "-",
                "‒": "-",
                "–": "-",
                "—": "-",
                "−": "-",
            }
        )
    )
    value = re.sub(
        r"(?<=[A-Za-z0-9])[\x00-\x08\x0b\x0c\x0e-\x1f](?=[A-Za-z0-9])",
        "-",
        value,
    )
    value = re.sub(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
        " ",
        value,
    )
    return norm(value)


def pdf_pages(path):
    return [
        clean_pdf_text(
            page.extract_text() or ""
        )
        for page in PdfReader(str(path)).pages
    ]


def anchor_pattern(value):
    tokens = re.findall(
        r"[a-z0-9]+",
        value.lower(),
    )
    if not tokens:
        raise RuntimeError(
            f"Invalid empty SAGO anchor: {value}"
        )
    return r"[^a-z0-9]+".join(
        re.escape(token)
        for token in tokens
    )


def block(text, start, end):
    start_match = re.search(
        anchor_pattern(start),
        text,
        flags=re.IGNORECASE,
    )
    if start_match is None:
        raise RuntimeError(
            f"Could not extract SAGO block start: {start}"
        )
    end_match = re.search(
        anchor_pattern(end),
        text[start_match.start():],
        flags=re.IGNORECASE,
    )
    if end_match is None:
        raise RuntimeError(
            f"Could not extract SAGO block end: {end}"
        )
    end_index = (
        start_match.start()
        + end_match.end()
    )
    return norm(
        text[
            start_match.start():
            end_index
        ]
    )


def sago_statements(source, meta):
    pages = pdf_pages(
        Path(
            meta["pdfFile"]
        )
    )
    start = next(
        (
            i
            for i, page
            in enumerate(pages)
            if (
                re.search(
                    r"\bexecutive\s+summary\b",
                    page,
                    flags=re.IGNORECASE,
                )
                and re.search(
                    r"\bcovid\W*19\b",
                    page,
                    flags=re.IGNORECASE,
                )
                and "pandemic" in page.lower()
            )
        ),
        None,
    )
    if start is None:
        hypothesis_page = next(
            (
                i
                for i, page
                in enumerate(pages)
                if "hypotheses include" in page.lower()
            ),
            None,
        )
        if hypothesis_page is not None:
            start = max(
                0,
                hypothesis_page - 1,
            )
    if start is None:
        candidates = [
            f"{i + 1}: {page[:180]}"
            for i, page
            in enumerate(pages)
            if (
                "executive summary" in page.lower()
                or "hypotheses include" in page.lower()
                or "zoonotic" in page.lower()
            )
        ]
        detail = " | ".join(
            candidates[:8]
        )
        raise RuntimeError(
            "Could not locate SAGO executive-summary evidence. "
            f"Candidate pages: {detail or 'none'}"
        )
    text = clean_pdf_text(
        " ".join(
            pages[
                start:
                min(
                    start + 6,
                    len(pages),
                )
            ]
        )
    )
    background_match = re.search(
        r"\bBackground\b",
        text,
        flags=re.IGNORECASE,
    )
    if background_match is not None:
        text = text[
            :background_match.start()
        ]
    specs = [
        (
            "cold_chain",
            "No additional evidence to support this hypothesis has become available",
            "SAGO will re-evaluate this hypothesis should additional evidence become available.",
        ),
        (
            "deliberate_manipulation",
            "To evaluate hypothesis #4",
            "SAGO will re-evaluate this hypothesis should additional evidence become available.",
        ),
        (
            "zoonotic",
            "While most available and accessible published scientific evidence supports hypothesis #1",
            "SARS-CoV-2 first entered the human population.",
        ),
        (
            "laboratory_event",
            "Much of the information needed to assess hypothesis #2",
            "It can therefore not be ruled out, nor can it be proven until more information is provided.",
        ),
        (
            "conclusion",
            "To conclude, while a zoonotic origin with spillover from animals to humans is currently considered the best supported hypothesis",
            "will remain inconclusive.",
        ),
    ]
    result = []
    for key, start_text, end_text in specs:
        value = block(
            text,
            start_text,
            end_text,
        )
        result.append(
            {
                "id": statement_id(
                    source["id"],
                    key,
                    value,
                ),
                "source_id": source["id"],
                "source_name": source["name"],
                "source_url": source["url"],
                "source_date": source["date"],
                "section": "Executive summary",
                "topic": "origin",
                "kind": "pdf_evidence",
                "text": value,
                "links": [meta["pdfUrl"]],
                "raw_file": meta["pdfFile"],
                "evidence_key": key,
            }
        )
    return result


def variant_rows(source, content, raw_file):
    soup = BeautifulSoup(content, "html.parser")
    statements, variants = [], []
    for table in soup.find_all("table"):
        heading_tag = table.find_previous(["h2", "h3"])
        heading = norm(heading_tag.get_text(" ", strip=True)) if heading_tag else ""
        lower = heading.lower()
        if "variants of interest" in lower:
            classification = "variant_of_interest"
        elif "variants under monitoring" in lower:
            classification = "variant_under_monitoring"
        elif "variants of concern" in lower:
            classification = "variant_of_concern"
        else:
            continue
        for row in table.find_all("tr"):
            cells = [norm(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
            if len(cells) < 5 or "Pango lineage" in cells[0]:
                continue
            lineage = re.sub(r"[^A-Za-z0-9.\-]", "", cells[0].split()[0])
            if not lineage:
                continue
            earliest = re.search(r"\b\d{2}-\d{2}-\d{4}\b", cells[3])
            designation = re.search(r"\b\d{2}-\d{2}-\d{4}\b", cells[4])
            text = " | ".join(cells)
            evidence = {
                "id": statement_id(source["id"], heading, text),
                "source_id": source["id"],
                "source_name": source["name"],
                "source_url": source["url"],
                "source_date": source["date"],
                "section": heading,
                "topic": "variants",
                "kind": "table_row",
                "text": text,
                "links": tag_links(row, source["url"]),
                "raw_file": raw_file,
            }
            statements.append(evidence)
            variants.append(
                {
                    "lineage": lineage,
                    "classification": classification,
                    "nextstrain": cells[1],
                    "features": cells[2],
                    "earliest": earliest.group(0) if earliest else "",
                    "designation": designation.group(0) if designation else "",
                    "links": evidence["links"],
                    "evidence": evidence,
                }
            )
    expected = {"JN.1", "PQ.16.1.1", "NB.1.8.1", "XFG", "BA.3.2"}
    missing = expected - {v["lineage"] for v in variants}
    if missing:
        raise RuntimeError("Missing expected WHO variants: " + ", ".join(sorted(missing)))
    return statements, variants


def add_node(nodes, node_id, category, name, provided=WHO_INFORES, **props):
    row = {
        "id": node_id,
        "category": category,
        "name": name,
        "xref": props.pop("xref", ""),
        "synonym": props.pop("synonym", ""),
        "provided_by": provided,
        **props,
    }
    if node_id not in nodes:
        nodes[node_id] = row
    else:
        for key, value in row.items():
            if value and not nodes[node_id].get(key):
                nodes[node_id][key] = value


def edge_id(subject, role, object_id, evidence_id):
    return f"urn:uuid:{uuid.uuid5(NAMESPACE, f'{subject}|{role}|{object_id}|{evidence_id}')}"


def add_edge(edges, subject, role, object_id, evidence, **props):
    edges.append(
        {
            "id": edge_id(subject, role, object_id, evidence["id"]),
            "predicate": "biolink:related_to",
            "relation": "biolink:related_to",
            "category": "biolink:Association",
            "primary_knowledge_source": WHO_INFORES,
            "provided_by": WHO_INFORES,
            "publications": "|".join(evidence.get("links", [])) or evidence["source_url"],
            "semantic_role": role,
            "evidence_statement_id": evidence["id"],
            "source_id": evidence["source_id"],
            "source_url": evidence["source_url"],
            "source_date": evidence["source_date"],
            "source_section": evidence["section"],
            "source_text": evidence["text"],
            "topic": evidence["topic"],
            "subject": subject,
            "object": object_id,
            **props,
        }
    )


def find_all(records, source_id, contains=None, key=None):
    matches = []

    for record in records:
        if record["source_id"] != source_id:
            continue

        if key and record.get("evidence_key") != key:
            continue

        if contains and not all(
            part.lower() in record["text"].lower()
            for part in contains
        ):
            continue

        matches.append(record)

    unique_matches = {}

    for record in matches:
        text_key = canon(
            record["text"]
        )

        if text_key not in unique_matches:
            unique_matches[text_key] = record

    matches = list(
        unique_matches.values()
    )

    if not matches:
        label = key or ", ".join(
            contains or []
        )

        raise RuntimeError(
            f"No evidence records found for {source_id} / {label}"
        )

    return matches


def find_one(records, source_id, contains=None, key=None):
    matches = find_all(
        records,
        source_id,
        contains=contains,
        key=key,
    )

    if len(matches) != 1:
        label = key or ", ".join(
            contains or []
        )

        details = " | ".join(
            f"{record.get('section')}: {record['text'][:180]}"
            for record in matches[:5]
        )

        raise RuntimeError(
            f"Expected one unique evidence record for {source_id} / {label}; "
            f"found {len(matches)}"
            + (
                f". Matches: {details}"
                if details
                else ""
            )
        )

    return matches[0]


def target_for_statement(record):
    if record["source_id"] == "long_covid_fact_sheet":
        return LONG_COVID_ID
    if record["topic"] == "transmission" or record["source_id"] == "variants":
        return SARS_ID
    if record["topic"] == "vaccination" or record["source_id"] in {"vaccine_policy", "vaccine_position"}:
        return VACCINATION_ID
    if record["source_id"] == "sago_origins":
        return SARS_ID
    return COVID_ID


def add_statement_graph(nodes, edges, records, source_meta):
    for source_id, meta in source_meta.items():
        doc_id = local_id("source", source_id)
        add_node(
            nodes,
            doc_id,
            "biolink:InformationContentEntity",
            f"WHO source document · {source_id}",
            source_title=meta["name"],
            source_url=meta["sourceUrl"],
            source_date=meta["sourceDate"],
            node_type="who_source_document",
        )
    for record in records:
        node_id = record["id"]
        add_node(
            nodes,
            node_id,
            "biolink:InformationContentEntity",
            f"WHO evidence statement · {record['id'][-8:]}",
            description=record["text"],
            topic=record["topic"],
            source_id=record["source_id"],
            source_url=record["source_url"],
            source_date=record["source_date"],
            source_section=record["section"],
            node_type="who_evidence_statement",
        )
        synthetic = {**record, "links": []}
        add_edge(edges, node_id, "extracted_from", local_id("source", record["source_id"]), synthetic)
        add_edge(edges, node_id, "evidence_about", target_for_statement(record), synthetic)


def add_semantic_claims(nodes, edges, records, variants):
    cause_evidence = find_all(
        records,
        "covid_fact_sheet",
        [
            "COVID-19 is caused by the SARS-CoV-2 virus",
            "spreads through the air",
        ],
    )

    for evidence in cause_evidence:
        add_edge(
            edges,
            SARS_ID,
            "causes",
            COVID_ID,
            evidence,
        )

    transmission_evidence = find_all(
        records,
        "covid_fact_sheet",
        [
            "spreads through the air via infectious respiratory particles",
        ],
    )

    for name, role in [
        (
            "infectious respiratory particles",
            "transmitted_via",
        ),
        (
            "close contact with an infected person",
            "transmission_risk_context",
        ),
        (
            "shared closed indoor spaces",
            "transmission_risk_context",
        ),
        (
            "contaminated surface contact followed by touching the eyes, nose or mouth",
            "transmitted_via",
        ),
    ]:
        node_id = local_id(
            "transmission",
            name,
        )

        add_node(
            nodes,
            node_id,
            "biolink:NamedThing",
            name,
            topic="transmission",
        )

        for evidence in transmission_evidence:
            add_edge(
                edges,
                SARS_ID,
                role,
                node_id,
                evidence,
            )

    long_covid_evidence = find_all(
        records,
        "long_covid_fact_sheet",
        [
            "COVID-19 can lead to serious long-term effects",
            "post COVID-19 condition",
        ],
    )

    for evidence in long_covid_evidence:
        add_edge(
            edges,
            COVID_ID,
            "can_lead_to_post_covid_condition",
            LONG_COVID_ID,
            evidence,
        )

    vaccine_evidence = find_all(
        records,
        "covid_fact_sheet",
        [
            "vaccines have saved millions of lives",
            "severe disease",
            "hospitalization",
            "death",
        ],
    )

    for name in [
        "severe disease",
        "hospitalization",
        "death",
    ]:
        node_id = local_id(
            "vaccine-outcome",
            name,
        )

        add_node(
            nodes,
            node_id,
            "biolink:NamedThing",
            name,
            topic="vaccination",
        )

        for evidence in vaccine_evidence:
            add_edge(
                edges,
                VACCINATION_ID,
                "protects_against",
                node_id,
                evidence,
            )

    risk_evidence = find_all(
        records,
        "global_risk_v10",
        [
            "global public health risk from COVID-19 remains moderate",
            "30 July 2026",
        ],
    )

    risk_id = local_id(
        "risk-level",
        "moderate global public health risk",
    )

    add_node(
        nodes,
        risk_id,
        "biolink:NamedThing",
        "moderate global public health risk",
        topic="current_risk",
    )

    for evidence in risk_evidence:
        add_edge(
            edges,
            COVID_ID,
            "global_public_health_risk_level",
            risk_id,
            evidence,
            as_of_date="2026-07-30",
        )

    origin_specs = [
        (
            "natural zoonotic spillover",
            "zoonotic",
            "best_supported_by_available_scientific_data",
        ),
        (
            "accidental laboratory-related event",
            "laboratory_event",
            "cannot_be_ruled_out_or_proven_with_available_information",
        ),
        (
            "cold-chain introduction into animal markets",
            "cold_chain",
            "no_additional_evidence_supporting",
        ),
        (
            "deliberate laboratory manipulation followed by a biosafety breach",
            "deliberate_manipulation",
            "no_scientific_evidence_supporting_over_natural_processes",
        ),
    ]

    for name, key, assessment in origin_specs:
        evidence = find_one(
            records,
            "sago_origins",
            key=key,
        )

        node_id = local_id(
            "origin-hypothesis",
            name,
        )

        add_node(
            nodes,
            node_id,
            "biolink:NamedThing",
            name,
            topic="origin",
        )

        add_edge(
            edges,
            SARS_ID,
            "origin_hypothesis_assessment",
            node_id,
            evidence,
            assessment=assessment,
        )

    conclusion = find_one(
        records,
        "sago_origins",
        key="conclusion",
    )

    status_id = local_id(
        "origin-status",
        "origin remains inconclusive",
    )

    add_node(
        nodes,
        status_id,
        "biolink:NamedThing",
        "origin remains inconclusive",
        topic="origin",
    )

    add_edge(
        edges,
        SARS_ID,
        "overall_origin_status",
        status_id,
        conclusion,
        assessment="inconclusive_pending_additional_information_or_scientific_data",
    )

    for variant in variants:
        node_id = local_id(
            "variant",
            variant["lineage"],
        )

        add_node(
            nodes,
            node_id,
            "biolink:OrganismTaxon",
            variant["lineage"],
            topic="variants",
            pango_lineage=variant["lineage"],
            variant_classification=variant["classification"],
            nextstrain_clade=variant["nextstrain"],
            genetic_features=variant["features"],
            earliest_documented_sample=variant["earliest"],
            designation_date=variant["designation"],
            risk_assessment_links=json.dumps(
                variant["links"],
                separators=(",", ":"),
            ),
        )

        add_edge(
            edges,
            SARS_ID,
            variant["classification"],
            node_id,
            variant["evidence"],
            earliest_documented_sample=variant["earliest"],
            designation_date=variant["designation"],
        )


def read_tsv(path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter="\t"))


def merge_history(nodes, edges, history):
    node_path, edge_path = history / "nodes.tsv", history / "edges.tsv"
    if not node_path.exists() or not edge_path.exists():
        raise RuntimeError(f"Existing WHO history slice not found in {history}")
    for row in read_tsv(node_path):
        if row.get("id") not in nodes:
            nodes[row["id"]] = row
        else:
            for key, value in row.items():
                if value and not nodes[row["id"]].get(key):
                    nodes[row["id"]][key] = value
    edge_ids = {edge["id"] for edge in edges}
    for row in read_tsv(edge_path):
        if row.get("id") and row["id"] not in edge_ids:
            edges.append(row)
            edge_ids.add(row["id"])
    return {
        "nodesSha256": sha_file(node_path),
        "edgesSha256": sha_file(edge_path),
        "metadata": json.loads((history / "source.json").read_text(encoding="utf-8"))
        if (history / "source.json").exists()
        else None,
    }


def dynamic_tsv(path, preferred, rows):
    fields, seen = [], set()
    for field in preferred:
        if field not in seen:
            fields.append(field)
            seen.add(field)
    for row in rows:
        for field in row:
            if field not in seen:
                fields.append(field)
                seen.add(field)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_evidence(path, records):
    fields = [
        "id",
        "source_id",
        "source_name",
        "source_url",
        "source_date",
        "section",
        "topic",
        "kind",
        "text",
        "links",
        "raw_file",
        "evidence_key",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for record in records:
            row = {**record, "links": json.dumps(record.get("links", []), separators=(",", ":"))}
            writer.writerow({field: row.get(field, "") for field in fields})


def main():
    config = args()
    config.output.mkdir(parents=True, exist_ok=True)
    raw_dir = config.output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    contents, metadata, records = {}, {}, []
    for source in SOURCES:
        print(f"Acquiring {source['id']}: {source['name']}")
        content, meta = acquire(source, raw_dir, config.reuse)
        contents[source["id"]] = content
        metadata[source["id"]] = meta
        extracted = article_statements(source, content, meta["rawFile"])
        records.extend(extracted)
        print(f"  statements: {len(extracted)}")

    sago = next(source for source in SOURCES if source["id"] == "sago_origins")
    sago_records = sago_statements(sago, metadata["sago_origins"])
    records.extend(sago_records)
    print(f"  SAGO executive-summary evidence blocks: {len(sago_records)}")

    variants_source = next(source for source in SOURCES if source["id"] == "variants")
    variant_records, variants = variant_rows(
        variants_source,
        contents["variants"],
        metadata["variants"]["rawFile"],
    )
    records.extend(variant_records)
    print(f"  current WHO variant rows: {len(variants)}")

    records = list({record["id"]: record for record in records}.values())

    nodes, edges = {}, []
    add_node(nodes, COVID_ID, "biolink:Disease", "COVID-19", provided="")
    add_node(nodes, SARS_ID, "biolink:OrganismTaxon", "SARS-CoV-2", provided="")
    add_node(
        nodes,
        LONG_COVID_ID,
        "biolink:Disease",
        "post-COVID-19 disorder",
        provided="",
        synonym="post COVID-19 condition|long COVID|PCC",
    )
    add_node(nodes, VACCINATION_ID, "biolink:NamedThing", "COVID-19 vaccination", topic="vaccination")

    add_statement_graph(nodes, edges, records, metadata)
    add_semantic_claims(nodes, edges, records, variants)
    history_meta = merge_history(nodes, edges, config.history)

    seen_edges = set()
    for edge in edges:
        if edge["id"] in seen_edges:
            raise RuntimeError(f"Duplicate WHO edge ID: {edge['id']}")
        seen_edges.add(edge["id"])
        if edge.get("subject") not in nodes or edge.get("object") not in nodes:
            raise RuntimeError(f"WHO edge references missing node: {edge['id']}")

    nodes_path = config.output / "nodes.tsv"
    edges_path = config.output / "edges.tsv"
    evidence_path = config.output / "evidence.tsv"
    dynamic_tsv(nodes_path, ["id", "category", "name", "xref", "synonym", "provided_by"], list(nodes.values()))
    dynamic_tsv(
        edges_path,
        [
            "id",
            "predicate",
            "relation",
            "category",
            "primary_knowledge_source",
            "provided_by",
            "publications",
            "semantic_role",
            "subject",
            "object",
        ],
        edges,
    )
    write_evidence(evidence_path, records)

    manifest = {
        "name": "WHO-derived COVID-19 verification knowledge graph",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "evidenceStatementCount": len(records),
        "sources": metadata,
        "history": history_meta,
        "evidenceCountsBySource": dict(sorted(Counter(r["source_id"] for r in records).items())),
        "evidenceCountsByTopic": dict(sorted(Counter(r["topic"] for r in records).items())),
        "semanticRoleCounts": dict(sorted(Counter(e.get("semantic_role", "") for e in edges).items())),
        "nodeCategoryCounts": dict(sorted(Counter(n.get("category", "") for n in nodes.values()).items())),
        "outputHashes": {
            "nodes": sha_file(nodes_path),
            "edges": sha_file(edges_path),
            "evidence": sha_file(evidence_path),
        },
        "representation": {
            "sourceDocuments": "WHO pages and publication records",
            "evidenceStatements": "provenance-preserving statements extracted from WHO source sections",
            "semanticEdges": "deterministic mappings for high-value verification claims",
            "originModel": "qualified SAGO hypothesis assessments",
            "variantModel": "structured WHO current variant table rows",
        },
    }
    metadata_path = config.output / "source.json"
    metadata_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print()
    print(f"WHO nodes written: {len(nodes)}")
    print(f"WHO edges written: {len(edges)}")
    print(f"WHO evidence statements written: {len(records)}")
    print(f"Nodes: {nodes_path}")
    print(f"Edges: {edges_path}")
    print(f"Evidence: {evidence_path}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
