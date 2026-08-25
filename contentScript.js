const processedMessages = new WeakSet();

const ORIGINAL_QUERY_MARKER =
  "=== ORIGINAL USER QUERY ===";

const CONTEXT_MARKER =
  "=== KNOWLEDGE GRAPH CONTEXT ===";

let panelHost = null;
let panelElements = null;
let lastOriginalDraft = null;
let lastAugmentedDraft = null;

function createPanel() {
  if (panelHost) {
    return panelElements;
  }

  panelHost = document.createElement("div");
  panelHost.id = "covid-kg-integration";

  const shadow = panelHost.attachShadow({
    mode: "open",
  });

  shadow.innerHTML = `
    <style>
      .launcher {
        position: fixed;
        right: 20px;
        bottom: 20px;
        z-index: 2147483647;
        width: 46px;
        height: 46px;
        border: 0;
        border-radius: 50%;
        background: #111111;
        color: #ffffff;
        cursor: pointer;
        font-size: 13px;
        font-weight: 700;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
      }

      .panel {
        display: none;
        position: fixed;
        right: 20px;
        bottom: 20px;
        width: 380px;
        max-height: 72vh;
        overflow: auto;
        z-index: 2147483647;
        background: #ffffff;
        color: #111111;
        border: 1px solid #d9d9d9;
        border-radius: 12px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.16);
        font-family: Arial, sans-serif;
        font-size: 13px;
      }

      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 14px;
        border-bottom: 1px solid #e5e5e5;
        font-weight: 600;
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

    <button class="launcher" type="button">
      KG
    </button>

    <div class="panel">
      <div class="header">
        <span>COVID-19 Knowledge Graph</span>
        <button class="close" type="button">×</button>
      </div>

      <div class="body">
        <div class="actions">
          <button class="action primary augment" type="button">
            Ground current prompt
          </button>

          <button class="action restore" type="button" disabled>
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
          <summary>Grounding context</summary>
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

  panelElements.launcher.addEventListener(
    "click",
    showPanel
  );

  panelElements.close.addEventListener(
    "click",
    hidePanel
  );

  panelElements.augment.addEventListener(
    "click",
    augmentCurrentPrompt
  );

  panelElements.restore.addEventListener(
    "click",
    restoreOriginalPrompt
  );

  document.documentElement.appendChild(
    panelHost
  );

  return panelElements;
}

function showPanel() {
  const elements = createPanel();

  elements.launcher.style.display =
    "none";

  elements.panel.style.display =
    "block";
}

function hidePanel() {
  const elements = createPanel();

  elements.panel.style.display =
    "none";

  elements.launcher.style.display =
    "block";
}

function findComposer() {
  const selectors = [
    "#prompt-textarea",
    '[data-testid="prompt-textarea"]',
    "form textarea",
    'form [contenteditable="true"]',
  ];

  for (const selector of selectors) {
    const elements =
      document.querySelectorAll(
        selector
      );

    for (const element of elements) {
      const rectangle =
        element.getBoundingClientRect();

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

function getComposerText(element) {
  if (
    element instanceof
      HTMLTextAreaElement ||
    element instanceof HTMLInputElement
  ) {
    return element.value.trim();
  }

  return element.innerText.trim();
}

function setTextInputValue(
  element,
  text
) {
  const prototype =
    element instanceof
    HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;

  const descriptor =
    Object.getOwnPropertyDescriptor(
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
    element.textContent = text;

    element.dispatchEvent(
      new InputEvent(
        "input",
        {
          bubbles: true,
          inputType: "insertText",
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
    element instanceof HTMLInputElement
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
    contextIndex <= originalIndex
  ) {
    return null;
  }

  return text
    .slice(
      originalIndex +
        ORIGINAL_QUERY_MARKER.length,
      contextIndex
    )
    .trim();
}

function normalizeQueryText(text) {
  return (
    extractOriginalQuery(text) ||
    text.trim()
  );
}

function setLoading(text) {
  const elements = createPanel();

  showPanel();

  elements.status.textContent =
    "Checking knowledge graph...";

  elements.query.textContent =
    `Query: ${text}`;

  elements.entities.textContent = "";
  elements.relation.textContent = "";
  elements.context.textContent = "";
}

function setError(
  text,
  error
) {
  const elements = createPanel();

  showPanel();

  elements.status.textContent =
    "Knowledge graph unavailable";

  elements.query.textContent =
    text
      ? `Query: ${text}`
      : "";

  elements.entities.textContent = "";

  elements.relation.textContent =
    error;

  elements.context.textContent = "";
}

function setResult(
  data,
  statusOverride = null
) {
  const elements = createPanel();

  showPanel();

  const facts =
    data.facts || [];

  if (statusOverride) {
    elements.status.textContent =
      statusOverride;
  } else if (facts.length > 0) {
    elements.status.textContent =
      `${facts.length} evidence record${
        facts.length === 1
          ? ""
          : "s"
      } found`;
  } else {
    elements.status.textContent =
      "No matching KG evidence";
  }

  elements.query.textContent =
    `Query: ${data.text}`;

  const linkedEntities =
    (data.entities || [])
      .map((entity) => {
        const candidate =
          entity.candidates &&
          entity.candidates.length > 0
            ? entity.candidates[0]
            : null;

        if (!candidate) {
          return null;
        }

        return `${candidate.name} (${candidate.id})`;
      })
      .filter(Boolean);

  elements.entities.textContent =
    linkedEntities.length > 0
      ? `Entities: ${linkedEntities.join(", ")}`
      : "Entities: none";

  const relationship =
    data.relationships &&
    data.relationships.length > 0
      ? data.relationships[0]
          .relationship
      : null;

  elements.relation.textContent =
    relationship
      ? `Relation: ${relationship}`
      : "Relation: unresolved";

  elements.context.textContent =
    data.context || "";
}

async function requestContext(
  text
) {
  return chrome.runtime.sendMessage({
    type: "GET_KG_CONTEXT",
    text,
  });
}

async function requestAugmentation(
  text
) {
  return chrome.runtime.sendMessage({
    type: "GET_KG_AUGMENTATION",
    text,
  });
}

async function augmentCurrentPrompt() {
  const composer =
    findComposer();

  if (!composer) {
    setError(
      "",
      "ChatGPT prompt editor was not found"
    );

    return;
  }

  const currentText =
    getComposerText(
      composer
    );

  if (!currentText) {
    setError(
      "",
      "Enter a prompt before grounding it"
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
      "The current prompt is already grounded"
    );

    return;
  }

  setLoading(
    currentText
  );

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
        response &&
        response.error
          ? response.error
          : "Knowledge graph request failed"
      );
    }

    const data =
      response.data;

    lastOriginalDraft =
      currentText;

    lastAugmentedDraft =
      data.augmentedPrompt;

    setComposerText(
      composer,
      data.augmentedPrompt
    );

    const count =
      (data.facts || []).length;

    const status =
      count > 0
        ? `Prompt grounded with ${count} evidence record${
            count === 1
              ? ""
              : "s"
          }`
        : "Prompt grounded with insufficient KG evidence";

    setResult(
      data,
      status
    );

    panelElements.restore.disabled =
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
      "ChatGPT prompt editor was not found"
    );

    return;
  }

  setComposerText(
    composer,
    lastOriginalDraft
  );

  panelElements.status.textContent =
    "Original prompt restored";

  panelElements.query.textContent =
    `Query: ${lastOriginalDraft}`;

  panelElements.restore.disabled =
    true;

  lastAugmentedDraft = null;
}

function extractMessageText(
  element
) {
  const content =
    element.querySelector(
      ".whitespace-pre-wrap"
    ) ||
    element;

  return content.innerText.trim();
}

async function processMessage(
  element
) {
  if (!element) {
    return;
  }

  if (
    processedMessages.has(
      element
    )
  ) {
    return;
  }

  const rawText =
    extractMessageText(
      element
    );

  if (!rawText) {
    return;
  }

  processedMessages.add(
    element
  );

  const text =
    normalizeQueryText(
      rawText
    );

  setLoading(
    text
  );

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
        response &&
        response.error
          ? response.error
          : "Knowledge graph request failed"
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
        '[data-message-author-role="user"]'
      )
    );

  if (
    messages.length === 0
  ) {
    return;
  }

  processMessage(
    messages[
      messages.length - 1
    ]
  );
}

const observer =
  new MutationObserver(
    processLatestUserMessage
  );

observer.observe(
  document.documentElement,
  {
    childList: true,
    subtree: true,
  }
);

createPanel();

processLatestUserMessage();