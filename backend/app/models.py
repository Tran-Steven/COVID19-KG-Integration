from typing import Any

from pydantic import BaseModel


class EntityRequest(BaseModel):
    entity: str


class NLPRequest(BaseModel):
    text: str


class ExtractedEntity(BaseModel):
    text: str
    type: str
    start: int
    end: int


class NLPResponse(BaseModel):
    text: str
    entities: list[ExtractedEntity]


class GraphEntityCandidate(BaseModel):
    id: str
    categories: list[str]
    name: str
    aliases: list[str]
    score: float


class LinkedEntity(BaseModel):
    text: str
    type: str
    start: int
    end: int
    candidates: list[
        GraphEntityCandidate
    ]


class EntityLinkingResponse(BaseModel):
    text: str
    entities: list[LinkedEntity]


class ExtractedRelation(BaseModel):
    text: str | None
    normalized: str | None
    root: str | None


class RelationResponse(BaseModel):
    text: str
    relation: ExtractedRelation


class NLPAnalysisResponse(BaseModel):
    text: str
    entities: list[LinkedEntity]
    relation: ExtractedRelation


class RelationshipCandidate(
    BaseModel
):
    relationship: str
    normalized: str
    score: float


class KnowledgeGraphEntity(
    BaseModel
):
    id: str
    name: str
    categories: list[str]


class Evidence(BaseModel):
    edgeId: str | None

    primaryKnowledgeSource: (
        str | None
    )

    providedBy: list[str]

    sourceDataset: (
        str | None
    )

    references: list[str]

    maxPhaseForIndication: (
        float | None
    )

    attributes: dict[
        str,
        Any,
    ]


class GraphFact(BaseModel):
    subject: KnowledgeGraphEntity
    predicate: str
    object: KnowledgeGraphEntity
    evidence: Evidence


class HistoryInterpretation(
    BaseModel
):
    intent: str
    canonicalSubject: str
    eventType: str
    semanticRole: str | None
    requestedField: str
    matchedText: str | None
    method: str


class HistoryAnswer(BaseModel):
    field: str
    value: str
    qualification: str | None


class HistoryEvidence(BaseModel):
    eventId: str | None
    eventName: str | None
    eventType: str | None
    dateStart: str | None
    dateEnd: str | None
    sourceText: str | None
    sourceUrl: str | None
    sourceLinks: list[str]
    semanticRole: str | None
    relatedEntityId: str | None
    relatedEntityName: str | None


class HistoryRetrievalResult(
    BaseModel
):
    text: str
    status: str

    interpretation: (
        HistoryInterpretation
        | None
    )

    answer: (
        HistoryAnswer
        | None
    )

    evidence: list[
        HistoryEvidence
    ]


class VerificationResult(
    BaseModel
):
    status: str
    reason: str
    evidenceCount: int
    method: str


class GraphRetrievalResponse(
    BaseModel
):
    text: str

    verificationType: str = (
        "relationship"
    )

    verification: (
        VerificationResult
    )

    entities: list[
        LinkedEntity
    ]

    relation: ExtractedRelation

    relationships: list[
        RelationshipCandidate
    ]

    facts: list[
        GraphFact
    ]

    history: (
        HistoryRetrievalResult
        | None
    ) = None


class GroundingContextResponse(
    GraphRetrievalResponse
):
    context: str


class AugmentedPromptResponse(
    GroundingContextResponse
):
    hasEvidence: bool
    augmentedPrompt: str


class QueryAmbiguity(BaseModel):
    term: str
    type: str

    possibleInterpretations: (
        list[str]
    )


class ResolvedOutcome(BaseModel):
    outcome: str
    matchedText: str | None
    method: str = "rule"
    score: float | None = None


class ResolvedRelationIntent(
    BaseModel
):
    intent: str
    direction: str | None
    matchedText: str | None
    specific: bool
    method: str = "rule"
    score: float | None = None


class QueryInterpretation(
    BaseModel
):
    ambiguous: bool
    broadRelation: bool

    outcomes: list[
        ResolvedOutcome
    ]

    relationIntent: (
        ResolvedRelationIntent
    )

    ambiguities: list[
        QueryAmbiguity
    ]


class InterpretationResponse(
    BaseModel
):
    text: str
    relation: ExtractedRelation

    interpretation: (
        QueryInterpretation
    )