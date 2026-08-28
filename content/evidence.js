function evidenceSource(fact) {
  const evidence = fact.evidence || {};

  const attributes = evidence.attributes || {};

  return (
    attributes.source_name ||
    attributes.source_id ||
    evidence.sourceDataset ||
    evidence.primaryKnowledgeSource ||
    "Knowledge Graph"
  );
}

function collectEvidence(claim) {
  const retrieval = claim.retrieval || {};

  const items = [];

  for (const fact of retrieval.facts || []) {
    items.push({
      type: "fact",
      value: fact,
    });
  }

  const history = retrieval.history;

  if (history && Array.isArray(history.evidence)) {
    for (const evidence of history.evidence) {
      items.push({
        type: "history",
        value: evidence,
      });
    }
  }

  return items;
}

function assessmentLabel(claim) {
  const retrieval = claim.retrieval || {};

  if (retrieval.verificationType === "history") {
    return "WHO historical evidence";
  }

  if (retrieval.verificationType === "who") {
    return "WHO assessment";
  }

  const evidence = collectEvidence(claim);

  const fact = evidence.find((item) => item.type === "fact");

  if (fact) {
    return `${displaySourceName(evidenceSource(fact.value))} evidence`;
  }

  return "Knowledge Graph assessment";
}

function appendReferences(container, references) {
  const validReferences = [
    ...new Set(
      (references || []).filter(
        (reference) =>
          typeof reference === "string" && /^https?:\/\//i.test(reference),
      ),
    ),
  ];

  if (validReferences.length === 0) {
    return;
  }

  const source = createElement("div", "source");

  validReferences.forEach((reference, index) => {
    if (index > 0) {
      source.appendChild(document.createTextNode(" · "));
    }

    const link = document.createElement("a");

    link.href = reference;

    link.target = "_blank";

    link.rel = "noreferrer";

    link.textContent =
      validReferences.length === 1 ? "Source" : `Source ` + `${index + 1}`;

    source.appendChild(link);
  });

  container.appendChild(source);
}

function renderFactEvidence(container, fact) {
  const subject = fact.subject || {};

  const object = fact.object || {};

  const predicate = fact.predicate || "related_to";

  const evidence = fact.evidence || {};

  const attributes = evidence.attributes || {};

  const item = createElement("div", "evidence");

  item.appendChild(
    createElement(
      "div",
      "evidence-title",
      `${subject.name || subject.id || "Unknown"} → ` +
        `${predicate} → ` +
        `${object.name || object.id || "Unknown"}`,
    ),
  );

  item.appendChild(
    createElement("div", "source", displaySourceName(evidenceSource(fact))),
  );

  const references = [...(evidence.references || [])];

  if (attributes.source_url) {
    references.push(attributes.source_url);
  }

  appendReferences(item, references);

  container.appendChild(item);
}

function renderHistoryEvidence(container, evidence) {
  const item = createElement("div", "evidence");

  const date = evidence.dateStart || evidence.dateEnd;

  const text =
    evidence.sourceText || evidence.eventName || "Historical evidence";

  item.appendChild(
    createElement("div", "evidence-title", date ? `${date} · ${text}` : text),
  );

  const links = [];

  if (evidence.sourceUrl) {
    links.push(evidence.sourceUrl);
  }

  for (const link of evidence.sourceLinks || []) {
    if (!links.includes(link)) {
      links.push(link);
    }
  }

  appendReferences(item, links);

  container.appendChild(item);
}

function renderEvidenceDetails(claim) {
  const evidence = collectEvidence(claim);

  if (evidence.length === 0) {
    return null;
  }

  const content = createElement("div", "detail-content");

  const list = createElement("div", "evidence-list");

  for (const item of evidence) {
    if (item.type === "history") {
      renderHistoryEvidence(list, item.value);
    } else {
      renderFactEvidence(list, item.value);
    }
  }

  content.appendChild(list);

  return createDisclosure(`Evidence ` + `(${evidence.length})`, content, {
    className: "detail-disclosure",
  });
}

function renderConfidenceDetails(confidence) {
  if (!confidence || confidence.score === undefined) {
    return null;
  }

  const content = createElement("div", "detail-content");

  const box = createElement("div", "confidence-box");

  const overall = createElement("div", "confidence-overall");

  overall.appendChild(createElement("span", "", "Evidence strength"));

  overall.appendChild(
    createElement(
      "strong",
      "",
      `${confidenceLevel(confidence)} · ` +
        `${percent(confidence.score) || "N/A"}`,
    ),
  );

  box.appendChild(overall);

  const components = confidence.components || {};

  const weights = confidence.weights || {};

  for (const [key, label] of CONFIDENCE_COMPONENTS) {
    if (components[key] === undefined) {
      continue;
    }

    const value = Number(components[key]);

    const weight = weights[key];

    const row = createElement("div", "confidence-row");

    const line = createElement("div", "confidence-line");

    line.appendChild(createElement("span", "confidence-label", label));

    line.appendChild(
      createElement(
        "span",
        "confidence-value",
        `${percent(value)}` +
          (weight !== undefined ? ` · weight ` + `${percent(weight)}` : ""),
      ),
    );

    row.appendChild(line);

    const bar = createElement("div", "confidence-bar");

    const fill = createElement("div", "confidence-fill");

    fill.style.width = `${Math.max(0, Math.min(100, value * 100))}%`;

    bar.appendChild(fill);

    row.appendChild(bar);

    box.appendChild(row);
  }

  box.appendChild(
    createElement(
      "div",
      "confidence-note",
      confidence.explanation ||
        "This is a heuristic " +
          "evidence-grounding score. " +
          "It is uncalibrated and is " +
          "not the probability that " +
          "the claim is true.",
    ),
  );

  content.appendChild(box);

  return createDisclosure("Confidence details", content, {
    className: "detail-disclosure",
  });
}

function appendClaimMeta(container, claim) {
  const verification = claim.retrieval?.verification || {};

  const confidence = verification.confidence || {};

  const meta = createElement("div", "meta");

  if (confidence.level) {
    const strength = createElement("span");

    strength.appendChild(document.createTextNode("Evidence strength: "));

    strength.appendChild(
      createElement("strong", "", confidenceLevel(confidence)),
    );

    meta.appendChild(strength);
  }

  if (verification.evidenceCount !== undefined) {
    meta.appendChild(
      createElement(
        "span",
        "",
        `${verification.evidenceCount} ` +
          `evidence record${verification.evidenceCount === 1 ? "" : "s"}`,
      ),
    );
  }

  if (claim.usedQuestionContext) {
    meta.appendChild(createElement("span", "", "Used question context"));
  }

  if (meta.childNodes.length > 0) {
    container.appendChild(meta);
  }
}

function createClaimElement(claim) {
  const verification = claim.retrieval?.verification || {};

  const confidence = verification.confidence || {};

  const container = createElement("div", "claim");

  const top = createElement("div", "claim-top");

  top.appendChild(createElement("div", "claim-text", claim.text || ""));

  top.appendChild(
    createElement(
      "span",
      "badge " + statusClass(verification.status),
      statusLabel(verification.status),
    ),
  );

  container.appendChild(top);

  if (verification.reason) {
    container.appendChild(
      createElement("div", "claim-reason", verification.reason),
    );
  }

  appendClaimMeta(container, claim);

  const evidence = renderEvidenceDetails(claim);

  if (evidence) {
    container.appendChild(evidence);
  }

  const confidenceDetails = renderConfidenceDetails(confidence);

  if (confidenceDetails) {
    container.appendChild(confidenceDetails);
  }

  return container;
}

function renderSingleClaim(shell, claim) {
  const verification = claim.retrieval?.verification || {};

  const confidence = verification.confidence || {};

  const assessment = createElement("div", "assessment");

  assessment.appendChild(
    createElement("div", "assessment-label", assessmentLabel(claim)),
  );

  assessment.appendChild(
    createElement(
      "div",
      "assessment-text",
      verification.reason ||
        "The Knowledge Graph " + "did not return an explanatory summary.",
    ),
  );

  appendClaimMeta(assessment, claim);

  const evidence = renderEvidenceDetails(claim);

  if (evidence) {
    assessment.appendChild(evidence);
  }

  const confidenceDetails = renderConfidenceDetails(confidence);

  if (confidenceDetails) {
    assessment.appendChild(confidenceDetails);
  }

  shell.appendChild(assessment);
}

function appendAggregate(shell, data) {
  const summary = data.summary || {};

  const aggregate = createElement("div", "aggregate");

  const supported =
    summary.supportedRatio !== null && summary.supportedRatio !== undefined
      ? percent(summary.supportedRatio)
      : percent(summary.groundingScore);

  const coverage = percent(summary.coverageRatio);

  if (supported !== null) {
    const metric = createElement("span");

    metric.appendChild(document.createTextNode("Supported "));

    metric.appendChild(createElement("strong", "", supported));

    aggregate.appendChild(metric);
  }

  if (coverage !== null) {
    const metric = createElement("span");

    metric.appendChild(
      document.createTextNode("Knowledge Graph " + "coverage "),
    );

    metric.appendChild(createElement("strong", "", coverage));

    aggregate.appendChild(metric);
  }

  const attention = createElement("span");

  attention.appendChild(document.createTextNode("Needs attention "));

  attention.appendChild(
    createElement("strong", "", String(summary.needsAttentionCount || 0)),
  );

  aggregate.appendChild(attention);

  shell.appendChild(aggregate);
}

function getClaimStatusCounts(claims) {
  const counts = new Map();

  for (const claim of claims) {
    const status = claim.retrieval?.verification?.status || "UNKNOWN";

    counts.set(status, (counts.get(status) || 0) + 1);
  }

  return counts;
}

function createClaimStatusSummary(claims) {
  const counts = getClaimStatusCounts(claims);

  const container = createElement("div", "claim-summary-counts");

  const order = [
    "SUPPORTED",
    "CONTRADICTED",
    "INSUFFICIENT_EVIDENCE",
    "NOT_VERIFIABLE_WITH_CURRENT_KG",
  ];

  for (const status of order) {
    const count = counts.get(status);

    if (!count) {
      continue;
    }

    container.appendChild(
      createElement(
        "span",
        "summary-chip " + statusClass(status),
        `${count} ` + `${humanStatusLabel(status)}`,
      ),
    );
  }

  return container;
}

function renderMultipleClaims(shell, data) {
  const claims = data.claims || [];

  appendAggregate(shell, data);

  const claimsContainer = createElement("div", "claims");

  for (const claim of claims) {
    claimsContainer.appendChild(createClaimElement(claim));
  }

  if (claims.length < COLLAPSE_CLAIM_THRESHOLD) {
    shell.appendChild(claimsContainer);

    return;
  }

  const summary = createElement("div", "claim-summary");

  summary.appendChild(
    createElement(
      "div",
      "claim-summary-title",
      `${claims.length} factual claims checked`,
    ),
  );

  summary.appendChild(createClaimStatusSummary(claims));

  shell.appendChild(summary);

  shell.appendChild(
    createDisclosure("Show all claims", claimsContainer, {
      className: "claim-disclosure",
      closedLabel: "Show all claims",
      openLabel: "Hide claims",
      resetChildrenOnClose: true,
    }),
  );
}

async function saveFeedbackLocally(feedback) {
  const result = await storageGet([FEEDBACK_STORAGE_KEY]);

  const existing = Array.isArray(result[FEEDBACK_STORAGE_KEY])
    ? result[FEEDBACK_STORAGE_KEY]
    : [];

  await storageSet({
    [FEEDBACK_STORAGE_KEY]: [...existing, feedback],
  });
}

function createFeedbackBody(data) {
  const body = createElement("div", "feedback-body");

  body.appendChild(
    createElement(
      "div",
      "feedback-question",
      "How useful was " + "this verification?",
    ),
  );

  body.appendChild(
    createElement(
      "div",
      "feedback-help",
      "1 = not useful · " + "5 = very useful",
    ),
  );

  const ratingRow = createElement("div", "rating-row");

  let rating = null;

  let correctness = null;

  for (let value = 1; value <= 5; value += 1) {
    const button = createElement("button", "rating-button", String(value));

    button.type = "button";

    button.addEventListener("click", () => {
      rating = value;

      ratingRow.querySelectorAll(".rating-button").forEach((candidate) => {
        candidate.classList.remove("selected");
      });

      button.classList.add("selected");
    });

    ratingRow.appendChild(button);
  }

  body.appendChild(ratingRow);

  body.appendChild(
    createElement(
      "div",
      "feedback-question",
      "Did the verification " + "result seem correct?",
    ),
  );

  const choiceRow = createElement("div", "choice-row");

  for (const [value, label] of [
    ["yes", "Yes"],
    ["no", "No"],
    ["unsure", "Unsure"],
  ]) {
    const button = createElement("button", "choice-button", label);

    button.type = "button";

    button.addEventListener("click", () => {
      correctness = value;

      choiceRow.querySelectorAll(".choice-button").forEach((candidate) => {
        candidate.classList.remove("selected");
      });

      button.classList.add("selected");
    });

    choiceRow.appendChild(button);
  }

  body.appendChild(choiceRow);

  body.appendChild(
    createElement(
      "div",
      "feedback-question",
      "What was unclear " + "or incorrect?",
    ),
  );

  body.appendChild(createElement("div", "feedback-help", "Optional"));

  const textarea = document.createElement("textarea");

  textarea.placeholder = "Add any details " + "that would help...";

  body.appendChild(textarea);

  const actions = createElement("div", "feedback-actions");

  const save = createElement("button", "save-feedback", "Save feedback");

  save.type = "button";

  const status = createElement("span", "feedback-status");

  save.addEventListener("click", async () => {
    const comment = textarea.value.trim();

    if (rating === null && correctness === null && !comment) {
      status.textContent = "Add a rating, " + "answer, or note.";

      return;
    }

    save.disabled = true;

    status.textContent = "Saving...";

    const feedback = {
      id: `${Date.now()}-` + `${Math.random().toString(36).slice(2)}`,
      createdAt: new Date().toISOString(),
      usefulRating: rating,
      perceivedCorrectness: correctness,
      comment,
      question: data.question || "",
      response: data.response || "",
      summaryStatus: data.summary?.status || null,
      claimCount: data.claimCount || 0,
      claims: (data.claims || []).map((claim) => ({
        text: claim.text,
        status: claim.retrieval?.verification?.status || null,
      })),
    };

    try {
      await saveFeedbackLocally(feedback);

      status.textContent = "Saved locally " + "in this browser.";

      save.textContent = "Saved";
    } catch (error) {
      save.disabled = false;

      if (isInvalidContextError(error)) {
        status.textContent = "Extension updated. " + "Refresh ChatGPT.";

        return;
      }

      status.textContent = "Could not save: " + error.message;
    }
  });

  actions.appendChild(save);

  actions.appendChild(status);

  body.appendChild(actions);

  body.appendChild(
    createElement(
      "div",
      "feedback-privacy",
      "Feedback is stored locally " +
        "in this browser and is not " +
        "automatically sent to the " +
        "project authors.",
    ),
  );

  return body;
}

function createFeedbackSection(data) {
  const wrapper = createElement("div", "feedback");

  wrapper.appendChild(
    createDisclosure("Give feedback", createFeedbackBody(data)),
  );

  return wrapper;
}

function createHeader(subtitle, status = null) {
  const header = createElement("div", "header");

  const titleWrap = createElement("div", "title-wrap");

  titleWrap.appendChild(createLogo());

  const titles = createElement("div");

  titles.appendChild(createElement("div", "title", "Knowledge Graph Check"));

  if (subtitle) {
    titles.appendChild(createElement("div", "subtitle", subtitle));
  }

  titleWrap.appendChild(titles);

  header.appendChild(titleWrap);

  if (status) {
    header.appendChild(
      createElement(
        "span",
        "badge " + statusClass(status),
        statusLabel(status),
      ),
    );
  }

  return header;
}

function createFooter() {
  const footer = createElement("div", "footer");

  footer.appendChild(
    createElement("span", "", "Research prototype · " + "not a clinical tool"),
  );

  const issueLink = document.createElement("a");

  issueLink.className = "report-link";

  issueLink.href = ISSUE_URL;

  issueLink.target = "_blank";

  issueLink.rel = "noreferrer";

  issueLink.textContent = "Report an issue ↗";

  footer.appendChild(issueLink);

  return footer;
}

function renderVerification(element, data) {
  if (!element || !element.isConnected) {
    return;
  }

  adoptPendingHostForAssistant(element);

  const host = createVerificationHost(element);

  host.dataset.kgState = "result";

  delete host.dataset.kgPending;

  applyTheme(host);

  const card = host.shadowRoot.querySelector(".card");

  const shell = createElement("div", "content-shell");

  const summary = data.summary || {};

  const claims = data.claims || [];

  shell.appendChild(
    createHeader(
      `${data.claimCount || 0} ` +
        `factual claim${data.claimCount === 1 ? "" : "s"} checked`,
      summary.status,
    ),
  );

  if (claims.length === 0) {
    shell.appendChild(
      createElement(
        "div",
        "empty",
        summary.explanation ||
          "No factual claims were " + "detected in this response.",
      ),
    );
  } else if (claims.length === 1) {
    renderSingleClaim(shell, claims[0]);
  } else {
    renderMultipleClaims(shell, data);
  }

  shell.appendChild(createFeedbackSection(data));

  shell.appendChild(createFooter());

  swapCardContent(card, shell);
}

function renderNonAnswer(element, question) {
  adoptPendingHostForNonAnswer(element);

  const host = createVerificationHost(element, {
    after: true,
  });

  host.dataset.kgState = "non-answer";

  delete host.dataset.kgPending;

  applyTheme(host);

  const card = host.shadowRoot.querySelector(".card");

  const shell = createElement("div", "content-shell");

  shell.appendChild(createHeader("No verification result"));

  const body = createElement("div", "non-answer");

  body.appendChild(
    createElement("div", "non-answer-title", "No response available to verify"),
  );

  body.appendChild(
    createElement(
      "div",
      "non-answer-copy",
      "ChatGPT did not return a " +
        "substantive factual answer, " +
        "so the verification pipeline " +
        "was not run.",
    ),
  );

  body.appendChild(
    createElement(
      "div",
      "evidence-explorer-note",
      "You can still inspect relevant " +
        "Knowledge Graph evidence. " +
        "This is evidence retrieval, " +
        "not a verification result.",
    ),
  );

  const button = createElement(
    "button",
    "inline-action",
    "Check Knowledge Graph " + "for evidence →",
  );

  button.type = "button";

  button.addEventListener("click", async () => {
    button.disabled = true;

    button.textContent = "Checking Knowledge Graph…";

    try {
      const response = await requestContext(question);

      if (!response || !response.ok) {
        throw new Error(response?.error || "Knowledge graph request failed");
      }

      renderEvidenceExplorer(element, question, response.data);
    } catch (error) {
      button.disabled = false;

      button.textContent = "Check Knowledge Graph " + "for evidence →";

      if (isInvalidContextError(error)) {
        renderReconnect(element, true);

        return;
      }

      const existingError = body.querySelector(".retrieval-error");

      if (existingError) {
        existingError.remove();
      }

      const errorText = createElement(
        "div",
        "evidence-explorer-note " + "retrieval-error",
        "Evidence retrieval failed: " + error.message,
      );

      body.appendChild(errorText);
    }
  });

  body.appendChild(button);

  shell.appendChild(body);

  shell.appendChild(createFooter());

  swapCardContent(card, shell);
}

function renderEvidenceExplorer(element, question, data) {
  const host = createVerificationHost(element, {
    after: true,
  });

  host.dataset.kgState = "evidence-explorer";

  delete host.dataset.kgPending;

  applyTheme(host);

  const card = host.shadowRoot.querySelector(".card");

  const facts = data.facts || [];

  if (facts.length === 0) {
    const existingBody = card.shadowRoot?.querySelector(".non-answer");

    const shell = createElement("div", "content-shell");

    shell.appendChild(createHeader("No verification result"));

    const body = createElement("div", "non-answer");

    body.appendChild(
      createElement(
        "div",
        "non-answer-title",
        "No response available to verify",
      ),
    );

    body.appendChild(
      createElement(
        "div",
        "non-answer-copy",
        "ChatGPT did not return a " +
          "substantive factual answer, " +
          "so the verification pipeline " +
          "was not run.",
      ),
    );

    body.appendChild(
      createElement(
        "div",
        "evidence-explorer-note",
        "No matching source-backed " +
          "Knowledge Graph evidence " +
          "was retrieved for this prompt.",
      ),
    );

    shell.appendChild(body);

    shell.appendChild(createFooter());

    swapCardContent(card, shell);

    return;
  }

  const shell = createElement("div", "content-shell");

  shell.appendChild(
    createHeader("Evidence view · " + "not a verification result"),
  );

  const body = createElement("div", "explorer");

  body.appendChild(
    createElement("div", "explorer-heading", "Knowledge Graph evidence"),
  );

  body.appendChild(
    createElement(
      "div",
      "explorer-copy",
      `${facts.length} source-backed ` +
        `evidence record${
          facts.length === 1 ? "" : "s"
        } retrieved for this prompt.`,
    ),
  );

  const list = createElement("div", "explorer-list");

  for (const fact of facts) {
    renderFactEvidence(list, fact);
  }

  body.appendChild(list);

  body.appendChild(
    createElement(
      "div",
      "evidence-explorer-note",
      "Retrieved evidence is shown " +
        "without generating a replacement " +
        "answer and is not included in " +
        "response-verification metrics.",
    ),
  );

  shell.appendChild(body);

  shell.appendChild(createFooter());

  swapCardContent(card, shell);
}

function renderReconnect(element, after = false) {
  const host = createVerificationHost(element, {
    after,
  });

  host.dataset.kgState = "error";

  delete host.dataset.kgPending;

  const card = host.shadowRoot.querySelector(".card");

  const shell = createElement("div", "content-shell");

  const wrapper = createElement("div", "reconnect");

  wrapper.appendChild(
    createElement("div", "reconnect-title", "Knowledge Graph Check"),
  );

  wrapper.appendChild(
    createElement(
      "div",
      "reconnect-copy",
      "The extension was updated. " + "Refresh ChatGPT to reconnect.",
    ),
  );

  const button = createElement("button", "refresh", "Refresh ChatGPT");

  button.type = "button";

  button.addEventListener("click", () => {
    window.location.reload();
  });

  wrapper.appendChild(button);

  shell.appendChild(wrapper);

  swapCardContent(card, shell);
}

function renderVerificationError(element, question, responseText, error) {
  if (isInvalidContextError(error)) {
    renderReconnect(element);

    return;
  }

  const host = createVerificationHost(element);

  host.dataset.kgState = "error";

  delete host.dataset.kgPending;

  const card = host.shadowRoot.querySelector(".card");

  const shell = createElement("div", "content-shell");

  const wrapper = createElement("div", "error");

  wrapper.appendChild(
    createElement("div", "error-title", "Knowledge Graph unavailable"),
  );

  wrapper.appendChild(
    createElement(
      "div",
      "error-copy",
      "Make sure the local backend " + "is running, then retry.",
    ),
  );

  const retry = createElement("button", "retry", "Retry");

  retry.type = "button";

  retry.addEventListener("click", () => {
    verifyAssistantMessage(element, {
      question,
      responseText,
      force: true,
    });
  });

  wrapper.appendChild(retry);

  shell.appendChild(wrapper);

  swapCardContent(card, shell);
}
