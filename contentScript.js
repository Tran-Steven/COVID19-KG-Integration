const processedUserMessages = new WeakSet();
const assistantTimers = new WeakMap();
const assistantPendingText = new WeakMap();
const assistantVerifiedText = new WeakMap();

const ORIGINAL_QUERY_MARKER =
  "=== ORIGINAL USER QUERY ===";

const CONTEXT_MARKER =
  "=== KNOWLEDGE GRAPH CONTEXT ===";

const FEEDBACK_STORAGE_KEY =
  "covidKgVerificationFeedback";

const ISSUE_URL =
  "https://github.com/Tran-Steven/COVID19-KG-Integration/issues/new/choose";

const LOGO_URL =
  chrome.runtime.getURL(
    "images/icon-32.png"
  );

const CONFIDENCE_COMPONENTS = [
  [
    "evidenceCoverage",
    "Evidence coverage",
  ],
  [
    "provenanceCompleteness",
    "Provenance completeness",
  ],
  [
    "relationCertainty",
    "Relation certainty",
  ],
  [
    "entityLinkCertainty",
    "Entity-link certainty",
  ],
  [
    "evidenceAgreement",
    "Evidence agreement",
  ],
  [
    "sourceDiversity",
    "Source diversity",
  ],
  [
    "recency",
    "Recency",
  ],
];

let panelHost = null;
let panelElements = null;
let lastOriginalDraft = null;

function createElement(
  tag,
  className = "",
  text = null
) {
  const element =
    document.createElement(tag);

  if (className) {
    element.className = className;
  }

  if (text !== null) {
    element.textContent = text;
  }

  return element;
}

function createLogo(
  className = "logo"
) {
  const wrapper =
    createElement(
      "span",
      `${className}-wrapper`
    );

  const image =
    document.createElement("img");

  image.className = className;
  image.src = LOGO_URL;
  image.alt =
    "COVID-19 Knowledge Graph";

  wrapper.appendChild(image);

  return wrapper;
}

function createPanel() {
  if (panelHost) {
    return panelElements;
  }

  panelHost =
    document.createElement("div");

  panelHost.id =
    "covid-kg-integration";

  const shadow =
    panelHost.attachShadow({
      mode: "open",
    });

  shadow.innerHTML = `
    <style>
      * {
        box-sizing: border-box;
      }

      .launcher {
        position: fixed;
        right: 20px;
        bottom: 20px;
        z-index: 2147483647;
        width: 48px;
        height: 48px;
        padding: 7px;
        border: 1px solid #d8d8d8;
        border-radius: 50%;
        background: #ffffff;
        cursor: pointer;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
      }

      .launcher img {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: contain;
      }

      .panel {
        display: none;
        position: fixed;
        right: 20px;
        bottom: 20px;
        width: min(380px, calc(100vw - 40px));
        max-height: 72vh;
        overflow: auto;
        z-index: 2147483647;
        background: #ffffff;
        color: #111111;
        border: 1px solid #d9d9d9;
        border-radius: 12px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.16);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        font-size: 13px;
      }

      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 12px 14px;
        border-bottom: 1px solid #e5e5e5;
      }

      .header-title {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
        font-weight: 650;
      }

      .header-logo {
        display: block;
        width: 22px;
        height: 22px;
        object-fit: contain;
      }

      .close {
        border: 0;
        background: transparent;
        color: inherit;
        cursor: pointer;
        font-size: 18px;
        line-height: 1;
      }

      .body {
        padding: 12px 14px 14px;
      }

      .actions {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
      }

      .action {
        border: 1px solid #d0d0d0;
        border-radius: 8px;
        background: #ffffff;
        color: #111111;
        cursor: pointer;
        padding: 8px 10px;
        font-size: 12px;
        font-weight: 600;
      }

      .action:disabled {
        cursor: default;
        opacity: 0.45;
      }

      .primary {
        background: #111111;
        color: #ffffff;
        border-color: #111111;
      }

      .status {
        font-weight: 600;
        margin-bottom: 10px;
      }

      .row {
        margin-bottom: 8px;
        line-height: 1.4;
      }

      details {
        margin-top: 12px;
      }

      summary {
        cursor: pointer;
        font-weight: 600;
      }

      pre {
        white-space: pre-wrap;
        word-break: break-word;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 11px;
        line-height: 1.4;
        margin: 10px 0 0;
        padding: 10px;
        background: #f6f6f6;
        border-radius: 8px;
      }
    </style>

    <button
      class="launcher"
      type="button"
      aria-label="Open COVID-19 Knowledge Graph"
    >
      <img
        src="${LOGO_URL}"
        alt=""
      >
    </button>

    <div class="panel">
      <div class="header">
        <div class="header-title">
          <img
            class="header-logo"
            src="${LOGO_URL}"
            alt=""
          >
          <span>
            COVID-19 Knowledge Graph
          </span>
        </div>

        <button
          class="close"
          type="button"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      <div class="body">
        <div class="actions">
          <button
            class="action primary augment"
            type="button"
          >
            Ground current prompt
          </button>

          <button
            class="action restore"
            type="button"
            disabled
          >
            Restore original
          </button>
        </div>

        <div class="status">
          Ready
        </div>

        <div class="query row"></div>
        <div class="entities row"></div>
        <div class="relation row"></div>

        <details>
          <summary>
            Grounding context
          </summary>
          <pre class="context"></pre>
        </details>
      </div>
    </div>
  `;

  panelElements = {
    launcher:
      shadow.querySelector(
        ".launcher"
      ),
    panel:
      shadow.querySelector(
        ".panel"
      ),
    close:
      shadow.querySelector(
        ".close"
      ),
    augment:
      shadow.querySelector(
        ".augment"
      ),
    restore:
      shadow.querySelector(
        ".restore"
      ),
    status:
      shadow.querySelector(
        ".status"
      ),
    query:
      shadow.querySelector(
        ".query"
      ),
    entities:
      shadow.querySelector(
        ".entities"
      ),
    relation:
      shadow.querySelector(
        ".relation"
      ),
    context:
      shadow.querySelector(
        ".context"
      ),
  };

  panelElements.launcher
    .addEventListener(
      "click",
      showPanel
    );

  panelElements.close
    .addEventListener(
      "click",
      hidePanel
    );

  panelElements.augment
    .addEventListener(
      "click",
      augmentCurrentPrompt
    );

  panelElements.restore
    .addEventListener(
      "click",
      restoreOriginalPrompt
    );

  document.documentElement
    .appendChild(panelHost);

  return panelElements;
}

function showPanel() {
  const elements =
    createPanel();

  elements.launcher
    .style.display =
      "none";

  elements.panel
    .style.display =
      "block";
}

function hidePanel() {
  const elements =
    createPanel();

  elements.panel
    .style.display =
      "none";

  elements.launcher
    .style.display =
      "block";
}

function findComposer() {
  const selectors = [
    "#prompt-textarea",
    '[data-testid="prompt-textarea"]',
    "form textarea",
    'form [contenteditable="true"]',
  ];

  for (
    const selector
    of selectors
  ) {
    const elements =
      document.querySelectorAll(
        selector
      );

    for (
      const element
      of elements
    ) {
      const rectangle =
        element
          .getBoundingClientRect();

      if (
        rectangle.width > 0 &&
        rectangle.height > 0
      ) {
        return element;
      }
    }
  }

  return null;
}

function getComposerText(
  element
) {
  if (
    element instanceof
      HTMLTextAreaElement ||
    element instanceof
      HTMLInputElement
  ) {
    return element
      .value
      .trim();
  }

  return element
    .innerText
    .trim();
}

function setTextInputValue(
  element,
  text
) {
  const prototype =
    element instanceof
      HTMLTextAreaElement
      ? HTMLTextAreaElement
          .prototype
      : HTMLInputElement
          .prototype;

  const descriptor =
    Object
      .getOwnPropertyDescriptor(
        prototype,
        "value"
      );

  descriptor.set.call(
    element,
    text
  );

  element.dispatchEvent(
    new Event(
      "input",
      {
        bubbles: true,
      }
    )
  );

  element.dispatchEvent(
    new Event(
      "change",
      {
        bubbles: true,
      }
    )
  );
}

function setContentEditableValue(
  element,
  text
) {
  element.focus();

  const selection =
    window.getSelection();

  const range =
    document.createRange();

  range.selectNodeContents(
    element
  );

  selection.removeAllRanges();
  selection.addRange(range);

  const inserted =
    document.execCommand(
      "insertText",
      false,
      text
    );

  if (!inserted) {
    element.textContent =
      text;

    element.dispatchEvent(
      new InputEvent(
        "input",
        {
          bubbles: true,
          inputType:
            "insertText",
          data: text,
        }
      )
    );
  }
}

function setComposerText(
  element,
  text
) {
  if (
    element instanceof
      HTMLTextAreaElement ||
    element instanceof
      HTMLInputElement
  ) {
    setTextInputValue(
      element,
      text
    );

    return;
  }

  setContentEditableValue(
    element,
    text
  );
}

function extractOriginalQuery(
  text
) {
  const originalIndex =
    text.indexOf(
      ORIGINAL_QUERY_MARKER
    );

  const contextIndex =
    text.indexOf(
      CONTEXT_MARKER
    );

  if (
    originalIndex === -1 ||
    contextIndex === -1 ||
    contextIndex <=
      originalIndex
  ) {
    return null;
  }

  return text
    .slice(
      originalIndex +
        ORIGINAL_QUERY_MARKER
          .length,
      contextIndex
    )
    .trim();
}

function normalizeQueryText(
  text
) {
  return (
    extractOriginalQuery(text) ||
    text.trim()
  );
}

function setLoading(
  text
) {
  const elements =
    createPanel();

  elements.status
    .textContent =
      "Checking knowledge graph...";

  elements.query
    .textContent =
      `Query: ${text}`;

  elements.entities
    .textContent =
      "";

  elements.relation
    .textContent =
      "";

  elements.context
    .textContent =
      "";
}

function setError(
  text,
  error
) {
  const elements =
    createPanel();

  elements.status
    .textContent =
      "Knowledge graph unavailable";

  elements.query
    .textContent =
      text
        ? `Query: ${text}`
        : "";

  elements.entities
    .textContent =
      "";

  elements.relation
    .textContent =
      error;

  elements.context
    .textContent =
      "";
}

function displaySourceName(
  value
) {
  if (!value) {
    return "Knowledge graph";
  }

  const normalized =
    String(value)
      .trim()
      .toLowerCase();

  if (
    normalized.includes("who")
  ) {
    return "WHO";
  }

  if (
    normalized.includes(
      "chembl"
    )
  ) {
    return "ChEMBL";
  }

  if (
    normalized.includes(
      "monarch"
    )
  ) {
    return "Monarch";
  }

  return String(value);
}

function setResult(
  data,
  statusOverride = null
) {
  const elements =
    createPanel();

  const facts =
    data.facts || [];

  if (statusOverride) {
    elements.status
      .textContent =
        statusOverride;
  } else if (
    facts.length > 0
  ) {
    elements.status
      .textContent =
        (
          `${facts.length} ` +
          `evidence record${
            facts.length === 1
              ? ""
              : "s"
          } found`
        );
  } else {
    elements.status
      .textContent =
        (
          "No matching " +
          "knowledge-graph " +
          "evidence"
        );
  }

  elements.query
    .textContent =
      `Query: ${data.text}`;

  const linkedEntities =
    (data.entities || [])
      .map(
        (entity) => {
          const candidate =
            (
              entity.candidates &&
              entity.candidates
                .length > 0
            )
              ? entity
                  .candidates[0]
              : null;

          if (!candidate) {
            return null;
          }

          return (
            `${candidate.name} ` +
            `(${candidate.id})`
          );
        }
      )
      .filter(Boolean);

  elements.entities
    .textContent =
      linkedEntities.length > 0
        ? (
            "Entities: " +
            linkedEntities
              .join(", ")
          )
        : "Entities: none";

  const relationship =
    (
      data.relationships &&
      data.relationships
        .length > 0
    )
      ? data
          .relationships[0]
          .relationship
      : null;

  elements.relation
    .textContent =
      relationship
        ? (
            "Relation: " +
            relationship
          )
        : (
            "Relation: " +
            "unresolved"
          );

  elements.context
    .textContent =
      data.context || "";
}

async function requestContext(
  text
) {
  return chrome.runtime
    .sendMessage({
      type:
        "GET_KG_CONTEXT",
      text,
    });
}

async function requestAugmentation(
  text
) {
  return chrome.runtime
    .sendMessage({
      type:
        "GET_KG_AUGMENTATION",
      text,
    });
}

async function requestResponseVerification(
  question,
  response
) {
  return chrome.runtime
    .sendMessage({
      type:
        "VERIFY_KG_RESPONSE",
      question,
      response,
    });
}

async function augmentCurrentPrompt() {
  showPanel();

  const composer =
    findComposer();

  if (!composer) {
    setError(
      "",
      (
        "ChatGPT prompt " +
        "editor was not found"
      )
    );

    return;
  }

  const currentText =
    getComposerText(composer);

  if (!currentText) {
    setError(
      "",
      (
        "Enter a prompt " +
        "before grounding it"
      )
    );

    return;
  }

  if (
    extractOriginalQuery(
      currentText
    )
  ) {
    setError(
      normalizeQueryText(
        currentText
      ),
      (
        "The current prompt " +
        "is already grounded"
      )
    );

    return;
  }

  setLoading(currentText);

  try {
    const response =
      await requestAugmentation(
        currentText
      );

    if (
      !response ||
      !response.ok
    ) {
      throw new Error(
        (
          response &&
          response.error
        )
          ? response.error
          : (
              "Knowledge graph " +
              "request failed"
            )
      );
    }

    const data =
      response.data;

    lastOriginalDraft =
      currentText;

    setComposerText(
      composer,
      data.augmentedPrompt
    );

    const count =
      (
        data.facts || []
      ).length;

    const status =
      count > 0
        ? (
            "Prompt grounded " +
            `with ${count} ` +
            `evidence record${
              count === 1
                ? ""
                : "s"
            }`
          )
        : (
            "Prompt grounded " +
            "with insufficient " +
            "knowledge-graph " +
            "evidence"
          );

    setResult(
      data,
      status
    );

    panelElements.restore
      .disabled =
        false;
  } catch (error) {
    setError(
      currentText,
      error.message
    );
  }
}

function restoreOriginalPrompt() {
  if (!lastOriginalDraft) {
    return;
  }

  const composer =
    findComposer();

  if (!composer) {
    setError(
      lastOriginalDraft,
      (
        "ChatGPT prompt " +
        "editor was not found"
      )
    );

    return;
  }

  setComposerText(
    composer,
    lastOriginalDraft
  );

  panelElements.status
    .textContent =
      (
        "Original prompt " +
        "restored"
      );

  panelElements.query
    .textContent =
      (
        "Query: " +
        lastOriginalDraft
      );

  panelElements.restore
    .disabled =
      true;
}

function extractUserMessageText(
  element
) {
  const content =
    (
      element.querySelector(
        ".whitespace-pre-wrap"
      )
      ||
      element
    );

  return content
    .innerText
    .trim();
}

function extractAssistantMessageText(
  element
) {
  const content =
    (
      element.querySelector(
        ".markdown"
      )
      ||
      element.querySelector(
        "[data-message-content]"
      )
      ||
      element.querySelector(
        ".whitespace-pre-wrap"
      )
    );

  if (content) {
    return content
      .innerText
      .trim();
  }

  const clone =
    element.cloneNode(true);

  clone.querySelectorAll(
    (
      "[data-covid-" +
      "kg-verification]"
    )
  )
    .forEach(
      (node) => {
        node.remove();
      }
    );

  return clone
    .innerText
    .trim();
}

async function processUserMessage(
  element
) {
  if (!element) {
    return;
  }

  if (
    processedUserMessages
      .has(element)
  ) {
    return;
  }

  const rawText =
    extractUserMessageText(
      element
    );

  if (!rawText) {
    return;
  }

  processedUserMessages
    .add(element);

  const text =
    normalizeQueryText(
      rawText
    );

  setLoading(text);

  try {
    const response =
      await requestContext(
        text
      );

    if (
      !response ||
      !response.ok
    ) {
      throw new Error(
        (
          response &&
          response.error
        )
          ? response.error
          : (
              "Knowledge graph " +
              "request failed"
            )
      );
    }

    setResult(
      response.data
    );
  } catch (error) {
    setError(
      text,
      error.message
    );
  }
}

function processLatestUserMessage() {
  const messages =
    Array.from(
      document.querySelectorAll(
        (
          "[data-message-" +
          'author-role="user"]'
        )
      )
    );

  if (
    messages.length === 0
  ) {
    return;
  }

  processUserMessage(
    messages[
      messages.length - 1
    ]
  );
}

function findQuestionForAssistant(
  element
) {
  const messages =
    Array.from(
      document.querySelectorAll(
        (
          "[data-message-" +
          "author-role]"
        )
      )
    );

  const index =
    messages.indexOf(element);

  if (index === -1) {
    return null;
  }

  for (
    let i = index - 1;
    i >= 0;
    i -= 1
  ) {
    if (
      messages[i]
        .getAttribute(
          "data-message-author-role"
        )
      !== "user"
    ) {
      continue;
    }

    const text =
      extractUserMessageText(
        messages[i]
      );

    if (text) {
      return normalizeQueryText(
        text
      );
    }
  }

  return null;
}

function statusClass(
  status
) {
  switch (status) {
    case "SUPPORTED":
      return "supported";

    case "CONTRADICTED":
      return "contradicted";

    case "INSUFFICIENT_EVIDENCE":
      return "insufficient";

    case (
      "NOT_VERIFIABLE_" +
      "WITH_CURRENT_KG"
    ):
      return "not-verifiable";

    case "MIXED":
      return "mixed";

    default:
      return "neutral";
  }
}

function statusLabel(
  status
) {
  switch (status) {
    case "INSUFFICIENT_EVIDENCE":
      return (
        "INSUFFICIENT EVIDENCE"
      );

    case (
      "NOT_VERIFIABLE_" +
      "WITH_CURRENT_KG"
    ):
      return "NOT VERIFIABLE";

    case "NO_FACTUAL_CLAIMS":
      return (
        "NO FACTUAL CLAIMS"
      );

    default:
      return status || "UNKNOWN";
  }
}

function percent(
  value
) {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(
      Number(value)
    )
  ) {
    return null;
  }

  return (
    `${Math.round(
      Number(value) * 100
    )}%`
  );
}

function confidenceLevel(
  confidence
) {
  const value =
    confidence &&
    confidence.level
      ? String(
          confidence.level
        )
      : "";

  if (!value) {
    return "Unknown";
  }

  return (
    value
      .charAt(0)
      .toUpperCase()
    +
    value
      .slice(1)
      .toLowerCase()
  );
}

function routeLabel(
  route
) {
  switch (route) {
    case "who":
      return "WHO evidence";

    case "history":
      return "WHO history";

    case "relationship":
      return (
        "Knowledge graph"
      );

    default:
      return (
        route ||
        "Knowledge graph"
      );
  }
}

function createVerificationHost(
  element
) {
  let host =
    element.querySelector(
      (
        "[data-covid-" +
        "kg-verification]"
      )
    );

  if (host) {
    return host;
  }

  host =
    document.createElement(
      "div"
    );

  host.setAttribute(
    (
      "data-covid-" +
      "kg-verification"
    ),
    "true"
  );

  host.style.display =
    "block";

  host.style.width =
    "100%";

  host.style.maxWidth =
    "48rem";

  host.style.marginTop =
    "12px";

  const content =
    (
      element.querySelector(
        ".markdown"
      )
      ||
      element.querySelector(
        "[data-message-content]"
      )
      ||
      element.querySelector(
        ".whitespace-pre-wrap"
      )
    );

  const target =
    (
      content &&
      content.parentElement
    )
      ? content.parentElement
      : element;

  target.appendChild(host);

  const shadow =
    host.attachShadow({
      mode: "open",
    });

  shadow.innerHTML = `
    <style>
      * {
        box-sizing: border-box;
      }

      :host {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      .card {
        overflow: hidden;
        background: #ffffff;
        color: #111111;
        border: 1px solid #dedede;
        border-radius: 12px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
      }

      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 10px 12px;
        border-bottom: 1px solid #e9e9e9;
      }

      .title-wrap {
        display: flex;
        align-items: center;
        min-width: 0;
        gap: 9px;
      }

      .logo-wrapper {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        flex: 0 0 28px;
        border: 1px solid #e4e4e4;
        border-radius: 8px;
        background: #ffffff;
      }

      .logo {
        display: block;
        width: 21px;
        height: 21px;
        object-fit: contain;
      }

      .title {
        font-size: 13px;
        font-weight: 700;
        line-height: 1.25;
      }

      .subtitle {
        margin-top: 1px;
        font-size: 10px;
        color: #737373;
        line-height: 1.3;
      }

      .badge {
        display: inline-flex;
        align-items: center;
        flex: 0 0 auto;
        padding: 4px 7px;
        border-radius: 999px;
        font-size: 9px;
        font-weight: 800;
        letter-spacing: 0.04em;
        white-space: nowrap;
      }

      .supported {
        background: #dcfce7;
        color: #166534;
      }

      .contradicted {
        background: #fee2e2;
        color: #991b1b;
      }

      .insufficient {
        background: #fef3c7;
        color: #92400e;
      }

      .not-verifiable,
      .neutral {
        background: #f1f1f1;
        color: #444444;
      }

      .mixed {
        background: #ede9fe;
        color: #5b21b6;
      }

      .summary {
        display: flex;
        flex-wrap: wrap;
        gap: 6px 16px;
        padding: 8px 12px;
        font-size: 10px;
        border-bottom: 1px solid #eeeeee;
        color: #444444;
      }

      .metric strong {
        color: #111111;
        font-weight: 700;
      }

      .claims {
        padding: 0 12px;
      }

      .claim {
        padding: 10px 0;
        border-bottom: 1px solid #eeeeee;
      }

      .claim:last-child {
        border-bottom: 0;
      }

      .claim-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 10px;
      }

      .claim-text {
        min-width: 0;
        font-size: 12px;
        line-height: 1.45;
        font-weight: 560;
      }

      .meta {
        display: flex;
        flex-wrap: wrap;
        gap: 4px 8px;
        margin-top: 5px;
        font-size: 10px;
        line-height: 1.4;
        color: #777777;
      }

      .meta strong {
        color: #444444;
      }

      details {
        margin-top: 7px;
      }

      summary {
        cursor: pointer;
        width: fit-content;
        font-size: 10px;
        font-weight: 650;
        color: #444444;
      }

      .reason {
        margin-top: 7px;
        font-size: 10px;
        line-height: 1.45;
        color: #686868;
      }

      .evidence-list {
        max-height: 220px;
        overflow: auto;
        margin-top: 7px;
        padding: 8px;
        border-radius: 8px;
        background: #f7f7f7;
      }

      .evidence {
        padding: 7px 0;
        border-bottom: 1px solid #e5e5e5;
        font-size: 10px;
        line-height: 1.45;
      }

      .evidence:first-child {
        padding-top: 0;
      }

      .evidence:last-child {
        padding-bottom: 0;
        border-bottom: 0;
      }

      .evidence-title {
        font-weight: 650;
      }

      .source {
        margin-top: 2px;
        color: #737373;
      }

      .source a {
        color: #444444;
      }

      .confidence-box {
        margin-top: 7px;
        padding: 9px;
        border-radius: 8px;
        background: #f7f7f7;
      }

      .confidence-overall {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 8px;
        font-size: 10px;
      }

      .confidence-overall strong {
        font-size: 11px;
      }

      .confidence-row {
        margin-top: 7px;
      }

      .confidence-line {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        font-size: 9px;
        line-height: 1.3;
      }

      .confidence-label {
        color: #555555;
      }

      .confidence-value {
        color: #222222;
        font-weight: 650;
        white-space: nowrap;
      }

      .confidence-bar {
        height: 4px;
        margin-top: 4px;
        overflow: hidden;
        border-radius: 999px;
        background: #e4e4e4;
      }

      .confidence-fill {
        height: 100%;
        border-radius: inherit;
        background: #333333;
      }

      .confidence-note {
        margin-top: 9px;
        font-size: 9px;
        line-height: 1.4;
        color: #777777;
      }

      .feedback {
        padding: 0 12px 10px;
        border-top: 1px solid #eeeeee;
      }

      .feedback details {
        margin-top: 10px;
      }

      .feedback-body {
        margin-top: 10px;
      }

      .feedback-question {
        margin-top: 11px;
        font-size: 10px;
        font-weight: 650;
      }

      .feedback-help {
        margin-top: 2px;
        font-size: 9px;
        color: #777777;
      }

      .rating-row,
      .choice-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 7px;
      }

      .rating-button,
      .choice-button {
        border: 1px solid #d7d7d7;
        border-radius: 7px;
        background: #ffffff;
        color: #222222;
        cursor: pointer;
        font-size: 10px;
        font-weight: 600;
      }

      .rating-button {
        width: 31px;
        height: 29px;
      }

      .choice-button {
        padding: 6px 10px;
      }

      .rating-button.selected,
      .choice-button.selected {
        border-color: #111111;
        background: #111111;
        color: #ffffff;
      }

      .feedback textarea {
        width: 100%;
        min-height: 62px;
        resize: vertical;
        margin-top: 7px;
        padding: 7px 8px;
        border: 1px solid #d7d7d7;
        border-radius: 7px;
        background: #ffffff;
        color: #111111;
        font: inherit;
        font-size: 10px;
        line-height: 1.4;
      }

      .feedback-actions {
        display: flex;
        align-items: center;
        gap: 9px;
        margin-top: 8px;
      }

      .save-feedback {
        border: 0;
        border-radius: 7px;
        padding: 6px 10px;
        background: #111111;
        color: #ffffff;
        cursor: pointer;
        font-size: 10px;
        font-weight: 650;
      }

      .save-feedback:disabled {
        cursor: default;
        opacity: 0.55;
      }

      .feedback-status {
        font-size: 9px;
        color: #666666;
      }

      .feedback-privacy {
        margin-top: 7px;
        font-size: 9px;
        line-height: 1.4;
        color: #888888;
      }

      .footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 8px 12px;
        border-top: 1px solid #eeeeee;
        font-size: 9px;
        line-height: 1.4;
        color: #777777;
      }

      .report-link {
        color: #555555;
        font-weight: 650;
        text-decoration: none;
        white-space: nowrap;
      }

      .report-link:hover {
        text-decoration: underline;
      }

      .loading-card {
        display: flex;
        align-items: center;
        gap: 9px;
        padding: 10px 12px;
      }

      .loading-copy {
        min-width: 0;
      }

      .loading-title {
        font-size: 11px;
        font-weight: 650;
      }

      .loading-subtitle {
        margin-top: 1px;
        font-size: 9px;
        color: #777777;
      }

      .spinner {
        width: 13px;
        height: 13px;
        margin-left: auto;
        flex: 0 0 13px;
        border: 2px solid #dddddd;
        border-top-color: #333333;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }

      .error {
        padding: 12px;
        font-size: 10px;
        line-height: 1.45;
        color: #991b1b;
      }

      .retry {
        margin-top: 8px;
        border: 1px solid #cccccc;
        border-radius: 7px;
        padding: 6px 9px;
        background: #ffffff;
        color: #111111;
        cursor: pointer;
        font-size: 10px;
        font-weight: 650;
      }

      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }
    </style>

    <div class="card"></div>
  `;

  return host;
}

function setVerificationWaiting(
  element
) {
  const host =
    createVerificationHost(
      element
    );

  if (
    host.dataset.state ===
    "waiting"
  ) {
    return;
  }

  host.dataset.state =
    "waiting";

  const card =
    host.shadowRoot
      .querySelector(
        ".card"
      );

  const wrapper =
    createElement(
      "div",
      "loading-card"
    );

  wrapper.appendChild(
    createLogo()
  );

  const copy =
    createElement(
      "div",
      "loading-copy"
    );

  copy.appendChild(
    createElement(
      "div",
      "loading-title",
      "Knowledge Graph Check"
    )
  );

  copy.appendChild(
    createElement(
      "div",
      "loading-subtitle",
      (
        "Waiting for the " +
        "response to finish..."
      )
    )
  );

  wrapper.appendChild(copy);

  wrapper.appendChild(
    createElement(
      "div",
      "spinner"
    )
  );

  card.replaceChildren(
    wrapper
  );
}

function setVerificationLoading(
  element
) {
  const host =
    createVerificationHost(
      element
    );

  host.dataset.state =
    "verifying";

  const card =
    host.shadowRoot
      .querySelector(
        ".card"
      );

  const wrapper =
    createElement(
      "div",
      "loading-card"
    );

  wrapper.appendChild(
    createLogo()
  );

  const copy =
    createElement(
      "div",
      "loading-copy"
    );

  copy.appendChild(
    createElement(
      "div",
      "loading-title",
      "Knowledge Graph Check"
    )
  );

  copy.appendChild(
    createElement(
      "div",
      "loading-subtitle",
      (
        "Verifying with the " +
        "knowledge graph..."
      )
    )
  );

  wrapper.appendChild(copy);

  wrapper.appendChild(
    createElement(
      "div",
      "spinner"
    )
  );

  card.replaceChildren(
    wrapper
  );
}

function collectEvidence(
  claim
) {
  const retrieval =
    claim.retrieval || {};

  const items = [];

  for (
    const fact
    of retrieval.facts || []
  ) {
    items.push({
      type: "fact",
      value: fact,
    });
  }

  const history =
    retrieval.history;

  if (
    history &&
    Array.isArray(
      history.evidence
    )
  ) {
    for (
      const evidence
      of history.evidence
    ) {
      items.push({
        type: "history",
        value: evidence,
      });
    }
  }

  return items;
}

function evidenceSource(
  fact
) {
  const evidence =
    fact.evidence || {};

  const attributes =
    evidence.attributes || {};

  return (
    attributes.source_name ||
    attributes.source_id ||
    evidence.sourceDataset ||
    evidence
      .primaryKnowledgeSource ||
    "Knowledge graph"
  );
}

function appendReferences(
  container,
  references
) {
  const validReferences =
    [
      ...new Set(
        (references || [])
          .filter(
            (reference) =>
              (
                typeof reference ===
                  "string"
                &&
                /^https?:\/\//i
                  .test(reference)
              )
          )
      ),
    ];

  if (
    validReferences.length ===
    0
  ) {
    return;
  }

  const source =
    createElement(
      "div",
      "source"
    );

  validReferences.forEach(
    (
      reference,
      index
    ) => {
      if (index > 0) {
        source.appendChild(
          document
            .createTextNode(
              " · "
            )
        );
      }

      const link =
        document
          .createElement("a");

      link.href = reference;
      link.target = "_blank";
      link.rel = "noreferrer";

      link.textContent =
        validReferences
          .length === 1
          ? "Source"
          : (
              `Source ` +
              `${index + 1}`
            );

      source.appendChild(link);
    }
  );

  container.appendChild(
    source
  );
}

function renderFactEvidence(
  container,
  fact
) {
  const subject =
    fact.subject || {};

  const object =
    fact.object || {};

  const predicate =
    fact.predicate ||
    "related_to";

  const evidence =
    fact.evidence || {};

  const attributes =
    evidence.attributes || {};

  const item =
    createElement(
      "div",
      "evidence"
    );

  item.appendChild(
    createElement(
      "div",
      "evidence-title",
      (
        `${
          subject.name ||
          subject.id ||
          "Unknown"
        } → ` +
        `${predicate} → ` +
        `${
          object.name ||
          object.id ||
          "Unknown"
        }`
      )
    )
  );

  item.appendChild(
    createElement(
      "div",
      "source",
      displaySourceName(
        evidenceSource(fact)
      )
    )
  );

  const references = [
    ...(
      evidence.references ||
      []
    ),
  ];

  if (
    attributes.source_url
  ) {
    references.push(
      attributes.source_url
    );
  }

  appendReferences(
    item,
    references
  );

  container.appendChild(
    item
  );
}

function renderHistoryEvidence(
  container,
  evidence
) {
  const item =
    createElement(
      "div",
      "evidence"
    );

  const date =
    (
      evidence.dateStart ||
      evidence.dateEnd
    );

  const text =
    (
      evidence.sourceText ||
      evidence.eventName ||
      "Historical evidence"
    );

  item.appendChild(
    createElement(
      "div",
      "evidence-title",
      date
        ? `${date} · ${text}`
        : text
    )
  );

  const links = [];

  if (
    evidence.sourceUrl
  ) {
    links.push(
      evidence.sourceUrl
    );
  }

  for (
    const link
    of evidence.sourceLinks ||
      []
  ) {
    if (
      !links.includes(link)
    ) {
      links.push(link);
    }
  }

  appendReferences(
    item,
    links
  );

  container.appendChild(
    item
  );
}

function renderConfidenceDetails(
  confidence
) {
  const details =
    document.createElement(
      "details"
    );

  const summary =
    document.createElement(
      "summary"
    );

  summary.textContent =
    "Confidence details";

  details.appendChild(
    summary
  );

  const box =
    createElement(
      "div",
      "confidence-box"
    );

  const overall =
    createElement(
      "div",
      "confidence-overall"
    );

  overall.appendChild(
    createElement(
      "span",
      "",
      "Evidence strength"
    )
  );

  overall.appendChild(
    createElement(
      "strong",
      "",
      (
        `${confidenceLevel(
          confidence
        )} · ` +
        `${
          percent(
            confidence.score
          ) || "N/A"
        }`
      )
    )
  );

  box.appendChild(
    overall
  );

  const components =
    confidence.components || {};

  const weights =
    confidence.weights || {};

  for (
    const [
      key,
      label,
    ]
    of CONFIDENCE_COMPONENTS
  ) {
    if (
      components[key] ===
      undefined
    ) {
      continue;
    }

    const value =
      Number(
        components[key]
      );

    const weight =
      weights[key];

    const row =
      createElement(
        "div",
        "confidence-row"
      );

    const line =
      createElement(
        "div",
        "confidence-line"
      );

    line.appendChild(
      createElement(
        "span",
        "confidence-label",
        label
      )
    );

    line.appendChild(
      createElement(
        "span",
        "confidence-value",
        (
          `${percent(value)}` +
          (
            weight !==
            undefined
              ? (
                  ` · weight ` +
                  `${percent(
                    weight
                  )}`
                )
              : ""
          )
        )
      )
    );

    row.appendChild(line);

    const bar =
      createElement(
        "div",
        "confidence-bar"
      );

    const fill =
      createElement(
        "div",
        "confidence-fill"
      );

    fill.style.width =
      (
        `${Math.max(
          0,
          Math.min(
            100,
            value * 100
          )
        )}%`
      );

    bar.appendChild(fill);

    row.appendChild(bar);

    box.appendChild(row);
  }

  box.appendChild(
    createElement(
      "div",
      "confidence-note",
      (
        confidence.explanation ||
        (
          "This is a heuristic " +
          "evidence-grounding score. " +
          "It is uncalibrated and is " +
          "not the probability that " +
          "the claim is true."
        )
      )
    )
  );

  details.appendChild(box);

  return details;
}

function renderClaim(
  claim
) {
  const retrieval =
    claim.retrieval || {};

  const verification =
    retrieval.verification ||
    {};

  const confidence =
    verification.confidence ||
    {};

  const evidence =
    collectEvidence(claim);

  const container =
    createElement(
      "div",
      "claim"
    );

  const top =
    createElement(
      "div",
      "claim-top"
    );

  top.appendChild(
    createElement(
      "div",
      "claim-text",
      claim.text || ""
    )
  );

  top.appendChild(
    createElement(
      "span",
      (
        "badge " +
        statusClass(
          verification.status
        )
      ),
      statusLabel(
        verification.status
      )
    )
  );

  container.appendChild(top);

  const meta =
    createElement(
      "div",
      "meta"
    );

  meta.appendChild(
    createElement(
      "span",
      "",
      routeLabel(
        retrieval.verificationType
      )
    )
  );

  if (
    confidence.level
  ) {
    const strength =
      createElement("span");

    strength.appendChild(
      document.createTextNode(
        "Evidence strength: "
      )
    );

    strength.appendChild(
      createElement(
        "strong",
        "",
        confidenceLevel(
          confidence
        )
      )
    );

    meta.appendChild(
      strength
    );
  }

  if (
    verification.evidenceCount !==
      undefined
  ) {
    meta.appendChild(
      createElement(
        "span",
        "",
        (
          `${verification.evidenceCount} ` +
          `evidence record${
            verification.evidenceCount ===
              1
              ? ""
              : "s"
          }`
        )
      )
    );
  }

  if (
    claim.usedQuestionContext
  ) {
    meta.appendChild(
      createElement(
        "span",
        "",
        "Used question context"
      )
    );
  }

  container.appendChild(meta);

  if (
    verification.reason ||
    evidence.length > 0
  ) {
    const details =
      document.createElement(
        "details"
      );

    const summary =
      document.createElement(
        "summary"
      );

    summary.textContent =
      evidence.length > 0
        ? (
            `Evidence ` +
            `(${evidence.length})`
          )
        : "Verification details";

    details.appendChild(
      summary
    );

    if (
      verification.reason
    ) {
      details.appendChild(
        createElement(
          "div",
          "reason",
          verification.reason
        )
      );
    }

    if (
      evidence.length > 0
    ) {
      const evidenceList =
        createElement(
          "div",
          "evidence-list"
        );

      for (
        const item
        of evidence
      ) {
        if (
          item.type ===
          "history"
        ) {
          renderHistoryEvidence(
            evidenceList,
            item.value
          );
        } else {
          renderFactEvidence(
            evidenceList,
            item.value
          );
        }
      }

      details.appendChild(
        evidenceList
      );
    }

    container.appendChild(
      details
    );
  }

  if (
    confidence &&
    confidence.score !==
      undefined
  ) {
    container.appendChild(
      renderConfidenceDetails(
        confidence
      )
    );
  }

  return container;
}

function saveFeedbackLocally(
  feedback
) {
  return new Promise(
    (
      resolve,
      reject
    ) => {
      chrome.storage.local.get(
        [
          FEEDBACK_STORAGE_KEY,
        ],
        (result) => {
          if (
            chrome.runtime
              .lastError
          ) {
            reject(
              new Error(
                chrome.runtime
                  .lastError
                  .message
              )
            );

            return;
          }

          const existing =
            Array.isArray(
              result[
                FEEDBACK_STORAGE_KEY
              ]
            )
              ? result[
                  FEEDBACK_STORAGE_KEY
                ]
              : [];

          chrome.storage.local.set(
            {
              [
                FEEDBACK_STORAGE_KEY
              ]:
                [
                  ...existing,
                  feedback,
                ],
            },
            () => {
              if (
                chrome.runtime
                  .lastError
              ) {
                reject(
                  new Error(
                    chrome.runtime
                      .lastError
                      .message
                  )
                );

                return;
              }

              resolve();
            }
          );
        }
      );
    }
  );
}

function createFeedbackSection(
  data
) {
  const wrapper =
    createElement(
      "div",
      "feedback"
    );

  const details =
    document.createElement(
      "details"
    );

  const summary =
    document.createElement(
      "summary"
    );

  summary.textContent =
    "Give feedback";

  details.appendChild(
    summary
  );

  const body =
    createElement(
      "div",
      "feedback-body"
    );

  body.appendChild(
    createElement(
      "div",
      "feedback-question",
      (
        "How useful was " +
        "this verification?"
      )
    )
  );

  body.appendChild(
    createElement(
      "div",
      "feedback-help",
      (
        "1 = not useful · " +
        "5 = very useful"
      )
    )
  );

  const ratingRow =
    createElement(
      "div",
      "rating-row"
    );

  let rating = null;
  let correctness = null;

  for (
    let value = 1;
    value <= 5;
    value += 1
  ) {
    const button =
      createElement(
        "button",
        "rating-button",
        String(value)
      );

    button.type =
      "button";

    button.addEventListener(
      "click",
      () => {
        rating = value;

        ratingRow.querySelectorAll(
          ".rating-button"
        )
          .forEach(
            (candidate) => {
              candidate.classList
                .remove(
                  "selected"
                );
            }
          );

        button.classList.add(
          "selected"
        );
      }
    );

    ratingRow.appendChild(
      button
    );
  }

  body.appendChild(
    ratingRow
  );

  body.appendChild(
    createElement(
      "div",
      "feedback-question",
      (
        "Did the verification " +
        "result seem correct?"
      )
    )
  );

  const choiceRow =
    createElement(
      "div",
      "choice-row"
    );

  for (
    const [
      value,
      label,
    ]
    of [
      ["yes", "Yes"],
      ["no", "No"],
      ["unsure", "Unsure"],
    ]
  ) {
    const button =
      createElement(
        "button",
        "choice-button",
        label
      );

    button.type =
      "button";

    button.addEventListener(
      "click",
      () => {
        correctness = value;

        choiceRow.querySelectorAll(
          ".choice-button"
        )
          .forEach(
            (candidate) => {
              candidate.classList
                .remove(
                  "selected"
                );
            }
          );

        button.classList.add(
          "selected"
        );
      }
    );

    choiceRow.appendChild(
      button
    );
  }

  body.appendChild(
    choiceRow
  );

  body.appendChild(
    createElement(
      "div",
      "feedback-question",
      (
        "What was unclear " +
        "or incorrect?"
      )
    )
  );

  body.appendChild(
    createElement(
      "div",
      "feedback-help",
      "Optional"
    )
  );

  const textarea =
    document.createElement(
      "textarea"
    );

  textarea.placeholder =
    (
      "Add any details " +
      "that would help..."
    );

  body.appendChild(
    textarea
  );

  const actions =
    createElement(
      "div",
      "feedback-actions"
    );

  const save =
    createElement(
      "button",
      "save-feedback",
      "Save feedback"
    );

  save.type = "button";

  const status =
    createElement(
      "span",
      "feedback-status"
    );

  save.addEventListener(
    "click",
    async () => {
      const comment =
        textarea.value.trim();

      if (
        rating === null &&
        correctness === null &&
        !comment
      ) {
        status.textContent =
          (
            "Add a rating, " +
            "answer, or note."
          );

        return;
      }

      save.disabled = true;
      status.textContent =
        "Saving...";

      const feedback = {
        id:
          (
            `${Date.now()}-` +
            `${Math.random()
              .toString(36)
              .slice(2)}`
          ),
        createdAt:
          new Date()
            .toISOString(),
        usefulRating:
          rating,
        perceivedCorrectness:
          correctness,
        comment,
        question:
          data.question || "",
        response:
          data.response || "",
        summaryStatus:
          (
            data.summary &&
            data.summary.status
          )
            ? data.summary.status
            : null,
        claimCount:
          data.claimCount || 0,
        claims:
          (data.claims || [])
            .map(
              (claim) => ({
                text:
                  claim.text,
                status:
                  (
                    claim.retrieval &&
                    claim.retrieval
                      .verification
                  )
                    ? (
                        claim.retrieval
                          .verification
                          .status
                      )
                    : null,
              })
            ),
      };

      try {
        await saveFeedbackLocally(
          feedback
        );

        status.textContent =
          (
            "Saved locally " +
            "in this browser."
          );

        save.textContent =
          "Saved";
      } catch (error) {
        save.disabled =
          false;

        status.textContent =
          (
            "Could not save: " +
            error.message
          );
      }
    }
  );

  actions.appendChild(save);
  actions.appendChild(status);

  body.appendChild(actions);

  body.appendChild(
    createElement(
      "div",
      "feedback-privacy",
      (
        "Feedback is stored " +
        "locally in this browser " +
        "and is not automatically " +
        "sent to the project authors."
      )
    )
  );

  details.appendChild(body);
  wrapper.appendChild(details);

  return wrapper;
}

function renderVerification(
  element,
  data
) {
  const host =
    createVerificationHost(
      element
    );

  host.dataset.state =
    "complete";

  const card =
    host.shadowRoot
      .querySelector(
        ".card"
      );

  card.replaceChildren();

  const summary =
    data.summary || {};

  const header =
    createElement(
      "div",
      "header"
    );

  const titleWrap =
    createElement(
      "div",
      "title-wrap"
    );

  titleWrap.appendChild(
    createLogo()
  );

  const titles =
    createElement("div");

  titles.appendChild(
    createElement(
      "div",
      "title",
      "Knowledge Graph Check"
    )
  );

  titles.appendChild(
    createElement(
      "div",
      "subtitle",
      (
        `${data.claimCount || 0} ` +
        `factual claim${
          data.claimCount === 1
            ? ""
            : "s"
        } checked`
      )
    )
  );

  titleWrap.appendChild(
    titles
  );

  header.appendChild(
    titleWrap
  );

  header.appendChild(
    createElement(
      "span",
      (
        "badge " +
        statusClass(
          summary.status
        )
      ),
      statusLabel(
        summary.status
      )
    )
  );

  card.appendChild(header);

  if (
    (data.claims || [])
      .length === 0
  ) {
    const empty =
      createElement(
        "div",
        "claim"
      );

    empty.style.margin =
      "0 12px";

    empty.textContent =
      (
        summary.explanation ||
        (
          "No factual claims " +
          "were detected in " +
          "this response."
        )
      );

    card.appendChild(empty);
  } else {
    const summaryRow =
      createElement(
        "div",
        "summary"
      );

    const supported =
      (
        summary.supportedRatio !==
          null
        &&
        summary.supportedRatio !==
          undefined
      )
        ? percent(
            summary
              .supportedRatio
          )
        : percent(
            summary
              .groundingScore
          );

    const coverage =
      percent(
        summary.coverageRatio
      );

    if (
      supported !== null
    ) {
      const metric =
        createElement(
          "span",
          "metric"
        );

      metric.appendChild(
        document.createTextNode(
          "Supported "
        )
      );

      metric.appendChild(
        createElement(
          "strong",
          "",
          supported
        )
      );

      summaryRow.appendChild(
        metric
      );
    }

    if (
      coverage !== null
    ) {
      const metric =
        createElement(
          "span",
          "metric"
        );

      metric.appendChild(
        document.createTextNode(
          "Coverage "
        )
      );

      metric.appendChild(
        createElement(
          "strong",
          "",
          coverage
        )
      );

      summaryRow.appendChild(
        metric
      );
    }

    const attention =
      createElement(
        "span",
        "metric"
      );

    attention.appendChild(
      document.createTextNode(
        "Needs attention "
      )
    );

    attention.appendChild(
      createElement(
        "strong",
        "",
        String(
          summary
            .needsAttentionCount ||
          0
        )
      )
    );

    summaryRow.appendChild(
      attention
    );

    card.appendChild(
      summaryRow
    );

    const claims =
      createElement(
        "div",
        "claims"
      );

    for (
      const claim
      of data.claims || []
    ) {
      claims.appendChild(
        renderClaim(claim)
      );
    }

    card.appendChild(claims);
  }

  card.appendChild(
    createFeedbackSection(
      data
    )
  );

  const footer =
    createElement(
      "div",
      "footer"
    );

  footer.appendChild(
    createElement(
      "span",
      "",
      (
        "Research prototype · " +
        "not a clinical tool"
      )
    )
  );

  const issueLink =
    document.createElement(
      "a"
    );

  issueLink.className =
    "report-link";

  issueLink.href =
    ISSUE_URL;

  issueLink.target =
    "_blank";

  issueLink.rel =
    "noreferrer";

  issueLink.textContent =
    "Report an issue ↗";

  footer.appendChild(
    issueLink
  );

  card.appendChild(footer);
}

function renderVerificationError(
  element,
  question,
  responseText,
  error
) {
  const host =
    createVerificationHost(
      element
    );

  host.dataset.state =
    "error";

  const card =
    host.shadowRoot
      .querySelector(
        ".card"
      );

  const wrapper =
    createElement(
      "div",
      "error"
    );

  wrapper.appendChild(
    createElement(
      "div",
      "",
      (
        "Knowledge Graph Check " +
        `unavailable: ${error}`
      )
    )
  );

  const retry =
    createElement(
      "button",
      "retry",
      "Retry"
    );

  retry.type = "button";

  retry.addEventListener(
    "click",
    () => {
      verifyAssistantMessage(
        element,
        question,
        responseText
      );
    }
  );

  wrapper.appendChild(retry);

  card.replaceChildren(
    wrapper
  );
}

async function verifyAssistantMessage(
  element,
  knownQuestion = null,
  knownResponse = null
) {
  if (
    !element ||
    !element.isConnected
  ) {
    return;
  }

  const responseText =
    (
      knownResponse ||
      extractAssistantMessageText(
        element
      )
    );

  const question =
    (
      knownQuestion ||
      findQuestionForAssistant(
        element
      )
    );

  if (
    !responseText ||
    !question
  ) {
    return;
  }

  if (
    assistantVerifiedText
      .get(element) ===
      responseText
    ||
    assistantPendingText
      .get(element) ===
      responseText
  ) {
    return;
  }

  assistantPendingText.set(
    element,
    responseText
  );

  setVerificationLoading(
    element
  );

  try {
    const response =
      await requestResponseVerification(
        question,
        responseText
      );

    if (
      !response ||
      !response.ok
    ) {
      throw new Error(
        (
          response &&
          response.error
        )
          ? response.error
          : (
              "Knowledge graph " +
              "request failed"
            )
      );
    }

    assistantVerifiedText.set(
      element,
      responseText
    );

    renderVerification(
      element,
      response.data
    );
  } catch (error) {
    renderVerificationError(
      element,
      question,
      responseText,
      error.message
    );
  } finally {
    assistantPendingText
      .delete(element);
  }
}

function scheduleAssistantVerification(
  element
) {
  if (!element) {
    return;
  }

  const text =
    extractAssistantMessageText(
      element
    );

  if (!text) {
    return;
  }

  if (
    assistantVerifiedText
      .get(element) ===
      text
    ||
    assistantPendingText
      .get(element) ===
      text
  ) {
    return;
  }

  const existingTimer =
    assistantTimers.get(
      element
    );

  if (existingTimer) {
    clearTimeout(
      existingTimer
    );
  }

  setVerificationWaiting(
    element
  );

  const timer =
    setTimeout(
      () => {
        assistantTimers.delete(
          element
        );

        verifyAssistantMessage(
          element
        );
      },
      1800
    );

  assistantTimers.set(
    element,
    timer
  );
}

function scheduleLatestAssistantVerification() {
  const messages =
    Array.from(
      document.querySelectorAll(
        (
          "[data-message-" +
          'author-role="assistant"]'
        )
      )
    );

  if (
    messages.length === 0
  ) {
    return;
  }

  scheduleAssistantVerification(
    messages[
      messages.length - 1
    ]
  );
}

function handlePageMutation() {
  processLatestUserMessage();
  scheduleLatestAssistantVerification();
}

const observer =
  new MutationObserver(
    handlePageMutation
  );

observer.observe(
  document.documentElement,
  {
    childList: true,
    subtree: true,
    characterData: true,
  }
);

createPanel();
processLatestUserMessage();
scheduleLatestAssistantVerification();