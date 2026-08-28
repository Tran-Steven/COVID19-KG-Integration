const assistantTimers = new Map();
const assistantPendingText = new WeakMap();
const assistantVerifiedText = new WeakMap();
const assistantVerificationData = new WeakMap();
const verificationHosts = new WeakMap();

const ORIGINAL_QUERY_MARKER = "=== ORIGINAL USER QUERY ===";

const CONTEXT_MARKER = "=== KNOWLEDGE GRAPH CONTEXT ===";

const FEEDBACK_STORAGE_KEY = "covidKgVerificationFeedback";

const VERIFICATION_CACHE_KEY = "covidKgVerificationCache";

const VERIFICATION_CACHE_VERSION = "v1";

const ISSUE_URL =
  "https://github.com/Tran-Steven/COVID19-KG-Integration/issues/new/choose";

const LOGO_URL = chrome.runtime.getURL("images/icon-32.png");

const RESPONSE_SETTLE_MS = 1400;
const GENERATION_RECHECK_MS = 450;
const CONVERSATION_SETTLE_MS = 700;
const INITIAL_DELAY_MS = 1200;
const CONTEXT_USER_MESSAGE_LIMIT = 8;
const CONTEXTUAL_FOLLOW_UP_WORD_LIMIT = 18;
const COLLAPSE_CLAIM_THRESHOLD = 3;
const CARD_RESIZE_MS = 220;
const DISCLOSURE_MS = 145;
const CONTENT_FADE_OUT_MS = 65;
const CONTENT_FADE_IN_MS = 160;

const COVID_CONTEXT_PATTERNS = [
  /\bcovid(?:-?19)?\b/i,
  /\bsars[- ]?cov[- ]?2\b/i,
  /\bcoronavirus\b/i,
  /\bcoronavirus disease 2019\b/i,
  /\blong covid\b/i,
  /\bpaxlovid\b/i,
  /\bnirmatrelvir\b/i,
  /\bremdesivir\b/i,
  /\bbaricitinib\b/i,
  /\bomicron\b/i,
  /\bdelta variant\b/i,
];

const CONTEXTUAL_FOLLOW_UP_PATTERN =
  /^(what|how|why|when|where|which|who|is|are|was|were|can|could|would|should|does|do|did|and|but|so|ok|okay)\b/i;

const CONTEXTUAL_REFERENCE_PATTERN =
  /\b(it|that|this|they|them|those|these|there|then|what about|how about|the lab|the vaccine|the virus|the treatment|the origin)\b/i;

const HOST_NON_ANSWER_PATTERNS = [
  /this content can(?:'|’)?t be shown/i,
  /this content cannot be shown/i,
  /we(?:'|’)?re especially careful with requests involving biological research/i,
  /eligible researchers can apply for trusted access/i,
];

const CONFIDENCE_COMPONENTS = [
  ["evidenceCoverage", "Evidence coverage"],
  ["provenanceCompleteness", "Provenance completeness"],
  ["relationCertainty", "Relation certainty"],
  ["entityLinkCertainty", "Entity-link certainty"],
  ["evidenceAgreement", "Evidence agreement"],
  ["sourceDiversity", "Source diversity"],
  ["recency", "Recency"],
];

let lastConversationUrl = location.href;

let conversationChangeTimer = null;

let lastOriginalDraft = null;

let mutationFrame = null;

function createElement(tag, className = "", text = null) {
  const element = document.createElement(tag);

  if (className) {
    element.className = className;
  }

  if (text !== null) {
    element.textContent = text;
  }

  return element;
}

function createLogo() {
  const wrapper = createElement("span", "logo-wrapper");

  const image = document.createElement("img");

  image.className = "logo";

  image.src = LOGO_URL;

  image.alt = "Knowledge Graph Check";

  wrapper.appendChild(image);

  return wrapper;
}

function runtimeContextAvailable() {
  try {
    return Boolean(chrome && chrome.runtime && chrome.runtime.id);
  } catch {
    return false;
  }
}

function invalidContextError() {
  const error = new Error("Extension context unavailable");

  error.code = "EXTENSION_CONTEXT_INVALIDATED";

  return error;
}

function isInvalidContextError(error) {
  if (!error) {
    return false;
  }

  if (error.code === "EXTENSION_CONTEXT_INVALIDATED") {
    return true;
  }

  const message = String(error.message || error).toLowerCase();

  return (
    message.includes("extension context invalidated") ||
    message.includes("extension context unavailable")
  );
}

async function sendRuntimeMessage(payload) {
  if (!runtimeContextAvailable()) {
    throw invalidContextError();
  }

  try {
    return await chrome.runtime.sendMessage(payload);
  } catch (error) {
    if (isInvalidContextError(error) || !runtimeContextAvailable()) {
      throw invalidContextError();
    }

    throw error;
  }
}

function storageGet(keys) {
  return new Promise((resolve, reject) => {
    if (!runtimeContextAvailable()) {
      reject(invalidContextError());

      return;
    }

    chrome.storage.local.get(keys, (result) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));

        return;
      }

      resolve(result);
    });
  });
}

function storageSet(values) {
  return new Promise((resolve, reject) => {
    if (!runtimeContextAvailable()) {
      reject(invalidContextError());

      return;
    }

    chrome.storage.local.set(values, () => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));

        return;
      }

      resolve();
    });
  });
}

function hashText(text) {
  let hash = 2166136261;

  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);

    hash = Math.imul(hash, 16777619);
  }

  return (hash >>> 0).toString(16).padStart(8, "0");
}

function conversationKey() {
  return location.origin + location.pathname;
}

function verificationCacheId(question, response) {
  return (
    `${VERIFICATION_CACHE_VERSION}:` +
    `${conversationKey()}:` +
    `${hashText(`${question}\u0000${response}`)}`
  );
}

async function getVerificationCache() {
  const result = await storageGet([VERIFICATION_CACHE_KEY]);

  const cache = result[VERIFICATION_CACHE_KEY];

  if (!cache || typeof cache !== "object" || Array.isArray(cache)) {
    return {};
  }

  return cache;
}

async function getCachedVerification(question, response) {
  const cache = await getVerificationCache();

  return cache[verificationCacheId(question, response)] || null;
}

async function saveCachedVerification(question, response, data) {
  const cache = await getVerificationCache();

  const id = verificationCacheId(question, response);

  cache[id] = {
    version: VERIFICATION_CACHE_VERSION,
    conversation: conversationKey(),
    question,
    response,
    savedAt: new Date().toISOString(),
    data,
  };

  await storageSet({
    [VERIFICATION_CACHE_KEY]: cache,
  });
}

function parseRgb(value) {
  const match = String(value).match(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/);

  if (!match) {
    return null;
  }

  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

function isDarkTheme() {
  const html = document.documentElement;

  const body = document.body;

  if (
    html.classList.contains("dark") ||
    body?.classList.contains("dark") ||
    html.dataset.theme === "dark" ||
    body?.dataset.theme === "dark"
  ) {
    return true;
  }

  const scheme = getComputedStyle(html).colorScheme;

  if (scheme === "dark") {
    return true;
  }

  if (!body) {
    return false;
  }

  const rgb = parseRgb(getComputedStyle(body).backgroundColor);

  if (!rgb) {
    return false;
  }

  const luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];

  return luminance < 128;
}

function applyTheme(host) {
  if (!host) {
    return;
  }

  host.dataset.theme = isDarkTheme() ? "dark" : "light";
}

function syncThemes() {
  document.querySelectorAll("[data-covid-kg-verification]").forEach((host) => {
    applyTheme(host);
  });
}

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function findComposer() {
  const selectors = [
    "#prompt-textarea",
    '[data-testid="prompt-textarea"]',
    "form textarea",
    'form [contenteditable="true"]',
  ];

  for (const selector of selectors) {
    const elements = document.querySelectorAll(selector);

    for (const element of elements) {
      const rectangle = element.getBoundingClientRect();

      if (rectangle.width > 0 && rectangle.height > 0) {
        return element;
      }
    }
  }

  return null;
}

function getComposerText(element) {
  if (
    element instanceof HTMLTextAreaElement ||
    element instanceof HTMLInputElement
  ) {
    return element.value.trim();
  }

  return element.innerText.trim();
}

function setTextInputValue(element, text) {
  const prototype =
    element instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;

  const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");

  descriptor.set.call(element, text);

  element.dispatchEvent(
    new Event("input", {
      bubbles: true,
    }),
  );

  element.dispatchEvent(
    new Event("change", {
      bubbles: true,
    }),
  );
}

function setContentEditableValue(element, text) {
  element.focus();

  const selection = window.getSelection();

  const range = document.createRange();

  range.selectNodeContents(element);

  selection.removeAllRanges();

  selection.addRange(range);

  const inserted = document.execCommand("insertText", false, text);

  if (!inserted) {
    element.textContent = text;

    element.dispatchEvent(
      new InputEvent("input", {
        bubbles: true,
        inputType: "insertText",
        data: text,
      }),
    );
  }
}

function setComposerText(element, text) {
  if (
    element instanceof HTMLTextAreaElement ||
    element instanceof HTMLInputElement
  ) {
    setTextInputValue(element, text);

    return;
  }

  setContentEditableValue(element, text);
}

function extractOriginalQuery(text) {
  const originalIndex = text.indexOf(ORIGINAL_QUERY_MARKER);

  const contextIndex = text.indexOf(CONTEXT_MARKER);

  if (
    originalIndex === -1 ||
    contextIndex === -1 ||
    contextIndex <= originalIndex
  ) {
    return null;
  }

  return text
    .slice(originalIndex + ORIGINAL_QUERY_MARKER.length, contextIndex)
    .trim();
}

function normalizeQueryText(text) {
  return extractOriginalQuery(text) || text.trim();
}

async function requestContext(text) {
  return sendRuntimeMessage({
    type: "GET_KG_CONTEXT",
    text,
  });
}

async function requestAugmentation(text) {
  return sendRuntimeMessage({
    type: "GET_KG_AUGMENTATION",
    text,
  });
}

async function requestResponseVerification(question, response) {
  return sendRuntimeMessage({
    type: "VERIFY_KG_RESPONSE",
    question,
    response,
  });
}

function extractUserMessageText(element) {
  const content = element.querySelector(".whitespace-pre-wrap") || element;

  return content.innerText.trim();
}

function extractAssistantMessageText(element) {
  const content =
    element.querySelector(".markdown") ||
    element.querySelector("[data-message-content]") ||
    element.querySelector(".whitespace-pre-wrap");

  if (content) {
    return content.innerText.trim();
  }

  const clone = element.cloneNode(true);

  clone.querySelectorAll("[data-covid-kg-verification]").forEach((node) => {
    node.remove();
  });

  return clone.innerText.trim();
}

function textHasCovidContext(text) {
  if (!text) {
    return false;
  }

  return COVID_CONTEXT_PATTERNS.some((pattern) => pattern.test(text));
}

function getConversationMessages() {
  return Array.from(document.querySelectorAll("[data-message-author-role]"));
}

function getUserMessages() {
  return Array.from(
    document.querySelectorAll('[data-message-author-role="user"]'),
  );
}

function getAssistantMessages() {
  return Array.from(
    document.querySelectorAll('[data-message-author-role="assistant"]'),
  );
}

function getRelevantUserMessages(element = null) {
  const messages = getConversationMessages();

  let endIndex = messages.length;

  if (element) {
    const index = messages.indexOf(element);

    if (index >= 0) {
      endIndex = index + 1;
    }
  }

  return messages
    .slice(0, endIndex)
    .filter(
      (message) => message.getAttribute("data-message-author-role") === "user",
    )
    .slice(-CONTEXT_USER_MESSAGE_LIMIT);
}

function conversationHasCovidContext(element = null) {
  const userMessages = getRelevantUserMessages(element);

  return userMessages.some((message) =>
    textHasCovidContext(normalizeQueryText(extractUserMessageText(message))),
  );
}

function getLatestUserMessage() {
  const messages = getUserMessages();

  if (messages.length === 0) {
    return null;
  }

  return messages[messages.length - 1];
}

function getLatestUserQuery() {
  const message = getLatestUserMessage();

  if (message) {
    return normalizeQueryText(extractUserMessageText(message));
  }

  const composer = findComposer();

  if (!composer) {
    return "";
  }

  return normalizeQueryText(getComposerText(composer));
}

function elementComesBefore(first, second) {
  if (!first || !second || first === second) {
    return false;
  }

  return Boolean(
    first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING,
  );
}

function findUserMessageBeforeElement(element) {
  const users = getUserMessages();

  let result = null;

  for (const user of users) {
    if (elementComesBefore(user, element)) {
      result = user;

      continue;
    }

    break;
  }

  return result;
}

function findQuestionElementForAssistant(element) {
  return findUserMessageBeforeElement(element);
}

function findQuestionForElement(element) {
  const questionElement = findUserMessageBeforeElement(element);

  if (!questionElement) {
    return null;
  }

  const text = extractUserMessageText(questionElement);

  if (!text) {
    return null;
  }

  return normalizeQueryText(text);
}

function findQuestionForAssistant(element) {
  return findQuestionForElement(element);
}

function isLikelyContextualFollowUp(text) {
  const normalized = String(text || "")
    .trim()
    .replace(/\s+/g, " ");

  if (!normalized) {
    return false;
  }

  const words = normalized.split(" ").filter(Boolean);

  if (words.length > CONTEXTUAL_FOLLOW_UP_WORD_LIMIT) {
    return false;
  }

  return (
    CONTEXTUAL_FOLLOW_UP_PATTERN.test(normalized) ||
    CONTEXTUAL_REFERENCE_PATTERN.test(normalized)
  );
}

function previousTurnHasCovidContext(questionElement) {
  if (!questionElement) {
    return false;
  }

  const messages = getConversationMessages();

  const questionIndex = messages.indexOf(questionElement);

  if (questionIndex <= 0) {
    return false;
  }

  let checked = 0;

  for (let index = questionIndex - 1; index >= 0 && checked < 2; index -= 1) {
    const role = messages[index].getAttribute("data-message-author-role");

    if (role !== "user" && role !== "assistant") {
      continue;
    }

    checked += 1;

    const text =
      role === "user"
        ? normalizeQueryText(extractUserMessageText(messages[index]))
        : extractAssistantMessageText(messages[index]);

    if (textHasCovidContext(text)) {
      return true;
    }
  }

  return false;
}

function userTurnHasCovidContext(userElement) {
  if (!userElement) {
    return false;
  }

  const question = normalizeQueryText(extractUserMessageText(userElement));

  if (textHasCovidContext(question)) {
    return true;
  }

  return (
    isLikelyContextualFollowUp(question) &&
    previousTurnHasCovidContext(userElement)
  );
}

function responseSurfaceHasCovidContext(element, question, responseText = "") {
  if (textHasCovidContext(question)) {
    return true;
  }

  if (textHasCovidContext(responseText)) {
    return true;
  }

  const questionElement = findUserMessageBeforeElement(element);

  return (
    isLikelyContextualFollowUp(question) &&
    previousTurnHasCovidContext(questionElement)
  );
}

function turnHasCovidContext(element) {
  const question = findQuestionForAssistant(element) || "";

  const response = extractAssistantMessageText(element) || "";

  return responseSurfaceHasCovidContext(element, question, response);
}

function normalizeHostNonAnswerText(text) {
  return String(text || "")
    .replace(/’/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function isHostNonAnswer(text) {
  const normalized = normalizeHostNonAnswerText(text);

  if (!normalized) {
    return false;
  }

  const hasTitle =
    /this content can't be shown/i.test(normalized) ||
    /this content cannot be shown/i.test(normalized);

  if (!hasTitle) {
    return false;
  }

  let supportingMatches = 0;

  for (const pattern of HOST_NON_ANSWER_PATTERNS) {
    if (pattern.test(normalized)) {
      supportingMatches += 1;
    }
  }

  return supportingMatches >= 2;
}

function findHostNonAnswerSurfaces() {
  const root = document.querySelector("main") || document.body;

  if (!root) {
    return [];
  }

  const elements = Array.from(
    root.querySelectorAll(
      ['[data-testid^="conversation-turn-"]', "article", "section", "div"].join(
        ",",
      ),
    ),
  );

  const candidates = elements.filter((element) => {
    if (
      element.matches('[data-message-author-role="assistant"]') ||
      element.querySelector('[data-message-author-role="assistant"]')
    ) {
      return false;
    }

    const text = element.textContent?.trim() || "";

    if (text.length < 40 || text.length > 1800) {
      return false;
    }

    return isHostNonAnswer(text);
  });

  const minimal = candidates.filter(
    (candidate) =>
      !candidates.some(
        (other) => other !== candidate && candidate.contains(other),
      ),
  );

  const surfaces = [];

  const seen = new Set();

  for (const candidate of minimal) {
    const turn = candidate.closest(
      ['[data-testid^="conversation-turn-"]', "article"].join(","),
    );

    const surface =
      turn && isHostNonAnswer(turn.textContent || "") ? turn : candidate;

    if (seen.has(surface)) {
      continue;
    }

    seen.add(surface);

    surfaces.push(surface);
  }

  return surfaces.sort((first, second) => {
    if (elementComesBefore(first, second)) {
      return -1;
    }

    if (elementComesBefore(second, first)) {
      return 1;
    }

    return 0;
  });
}

function getNextUserMessage(userElement) {
  const users = getUserMessages();

  const index = users.indexOf(userElement);

  if (index === -1 || index >= users.length - 1) {
    return null;
  }

  return users[index + 1];
}

function elementBelongsToUserTurn(element, userElement) {
  if (!element || !userElement || !elementComesBefore(userElement, element)) {
    return false;
  }

  const nextUser = getNextUserMessage(userElement);

  if (!nextUser) {
    return true;
  }

  return elementComesBefore(element, nextUser);
}

function findAssistantForUserTurn(userElement) {
  const assistants = getAssistantMessages();

  for (const assistant of assistants) {
    if (elementBelongsToUserTurn(assistant, userElement)) {
      return assistant;
    }
  }

  return null;
}

function findNonAnswerForUserTurn(userElement) {
  const surfaces = findHostNonAnswerSurfaces();

  for (const surface of surfaces) {
    if (elementBelongsToUserTurn(surface, userElement)) {
      return surface;
    }
  }

  return null;
}

function getResponseSurfaces() {
  const surfaces = [];

  for (const element of getAssistantMessages()) {
    surfaces.push({
      kind: "assistant",
      element,
      question: findQuestionForElement(element),
      response: extractAssistantMessageText(element),
    });
  }

  for (const element of findHostNonAnswerSurfaces()) {
    surfaces.push({
      kind: "non_answer",
      element,
      question: findQuestionForElement(element),
      response: normalizeHostNonAnswerText(element.textContent),
    });
  }

  surfaces.sort((first, second) => {
    if (elementComesBefore(first.element, second.element)) {
      return -1;
    }

    if (elementComesBefore(second.element, first.element)) {
      return 1;
    }

    return 0;
  });

  return surfaces;
}

function assistantGenerationInProgress() {
  const selectors = [
    'button[data-testid="stop-button"]',
    'button[aria-label="Stop generating"]',
    'button[aria-label="Stop streaming"]',
  ];

  return selectors.some((selector) =>
    Boolean(document.querySelector(selector)),
  );
}

function statusClass(status) {
  switch (status) {
    case "SUPPORTED":
      return "supported";

    case "CONTRADICTED":
      return "contradicted";

    case "INSUFFICIENT_EVIDENCE":
      return "insufficient";

    case "NOT_VERIFIABLE_WITH_CURRENT_KG":
      return "not-verifiable";

    case "MIXED":
      return "mixed";

    default:
      return "neutral";
  }
}

function statusLabel(status) {
  switch (status) {
    case "INSUFFICIENT_EVIDENCE":
      return "INSUFFICIENT EVIDENCE";

    case "NOT_VERIFIABLE_WITH_CURRENT_KG":
      return "NOT VERIFIABLE";

    case "NO_FACTUAL_CLAIMS":
      return "NO FACTUAL CLAIMS";

    default:
      return status || "UNKNOWN";
  }
}

function humanStatusLabel(status) {
  switch (status) {
    case "SUPPORTED":
      return "Supported";

    case "CONTRADICTED":
      return "Contradicted";

    case "INSUFFICIENT_EVIDENCE":
      return "Insufficient evidence";

    case "NOT_VERIFIABLE_WITH_CURRENT_KG":
      return "Not verifiable";

    default:
      return statusLabel(status);
  }
}

function percent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return null;
  }

  return `${Math.round(Number(value) * 100)}%`;
}

function confidenceLevel(confidence) {
  const value = confidence?.level ? String(confidence.level) : "";

  if (!value) {
    return "Unknown";
  }

  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function displaySourceName(value) {
  if (!value) {
    return "Knowledge Graph";
  }

  const normalized = String(value).trim().toLowerCase();

  if (normalized.includes("who") || normalized.includes("sago")) {
    return "WHO";
  }

  if (normalized.includes("chembl")) {
    return "ChEMBL";
  }

  if (normalized.includes("monarch")) {
    return "Monarch";
  }

  return String(value);
}

function getNormalHostTarget(element) {
  const content =
    element.querySelector(".markdown") ||
    element.querySelector("[data-message-content]") ||
    element.querySelector(".whitespace-pre-wrap");

  return content && content.parentElement ? content.parentElement : element;
}

function placeHost(host, element, options = {}) {
  if (options.after) {
    if (host.previousElementSibling !== element) {
      element.insertAdjacentElement("afterend", host);
    }

    return;
  }

  const target = getNormalHostTarget(element);

  if (host.parentElement !== target) {
    target.appendChild(host);
  }
}

function createVerificationHost(element, options = {}) {
  const mapped = verificationHosts.get(element);

  if (mapped && mapped.isConnected) {
    placeHost(mapped, element, options);

    applyTheme(mapped);

    return mapped;
  }

  const descendant = element.querySelector?.("[data-covid-kg-verification]");

  if (descendant) {
    verificationHosts.set(element, descendant);

    applyTheme(descendant);

    return descendant;
  }

  if (element.nextElementSibling?.matches("[data-covid-kg-verification]")) {
    const sibling = element.nextElementSibling;

    verificationHosts.set(element, sibling);

    applyTheme(sibling);

    return sibling;
  }

  const host = document.createElement("div");

  host.setAttribute("data-covid-kg-verification", "true");

  host.style.display = "block";

  host.style.width = "100%";

  host.style.maxWidth = "50rem";

  host.style.marginTop = "14px";

  applyTheme(host);

  placeHost(host, element, options);

  verificationHosts.set(element, host);

  const shadow = host.attachShadow({
    mode: "open",
  });

  shadow.innerHTML = `
    <style>
      :host {
        --kg-bg: #ffffff;
        --kg-soft: #f7f7f7;
        --kg-text: #111111;
        --kg-muted: #666666;
        --kg-border: #e2e2e2;
        --kg-link: #3f3f3f;

        --kg-supported-bg: #dcfce7;
        --kg-supported-text: #166534;

        --kg-contradicted-bg: #fee2e2;
        --kg-contradicted-text: #991b1b;

        --kg-insufficient-bg: #fef3c7;
        --kg-insufficient-text: #92400e;

        --kg-mixed-bg: #ede9fe;
        --kg-mixed-text: #5b21b6;

        --kg-neutral-bg: #f1f1f1;
        --kg-neutral-text: #444444;

        font-family:
          -apple-system,
          BlinkMacSystemFont,
          "Segoe UI",
          sans-serif;
      }

      :host([data-theme="dark"]) {
        --kg-bg: #212121;
        --kg-soft: #2b2b2b;
        --kg-text: #f2f2f2;
        --kg-muted: #b8b8b8;
        --kg-border: #3b3b3b;
        --kg-link: #dddddd;

        --kg-supported-bg: #173d2c;
        --kg-supported-text: #9ee6b8;

        --kg-contradicted-bg: #4a2020;
        --kg-contradicted-text: #f3abab;

        --kg-insufficient-bg: #493713;
        --kg-insufficient-text: #f5d58c;

        --kg-mixed-bg: #33284c;
        --kg-mixed-text: #cbbcff;

        --kg-neutral-bg: #333333;
        --kg-neutral-text: #d6d6d6;
      }

      * {
        box-sizing: border-box;
      }

      button,
      textarea {
        font-family: inherit;
      }

      .card {
        position: relative;
        overflow: hidden;
        background: var(--kg-bg);
        color: var(--kg-text);
        border: 1px solid var(--kg-border);
        border-radius: 13px;
        box-shadow:
          0 1px 2px
          rgba(0, 0, 0, 0.08);
        transform-origin: top center;
      }

      .card.compact-state {
        overflow: visible;
        background: transparent;
        border-color: transparent;
        border-radius: 0;
        box-shadow: none;
      }

      .content-shell {
        width: 100%;
      }

      .compact-row {
        display: flex;
        align-items: center;
        width: fit-content;
        gap: 9px;
        padding: 5px 1px;
        color: var(--kg-muted);
      }

      .compact-logo {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 23px;
        height: 23px;
        flex: 0 0 23px;
      }

      .compact-logo .logo-wrapper {
        width: 23px;
        height: 23px;
        flex-basis: 23px;
      }

      .compact-logo .logo {
        width: 21px;
        height: 21px;
      }

      .compact-copy {
        display: flex;
        align-items: baseline;
        flex-wrap: wrap;
        gap: 5px;
        min-width: 0;
      }

      .compact-title {
        color: var(--kg-text);
        font-size: 12.5px;
        font-weight: 650;
        line-height: 1.4;
      }

      .compact-separator {
        color: var(--kg-muted);
        font-size: 11px;
      }

      .compact-status {
        color: var(--kg-muted);
        font-size: 11.5px;
        font-weight: 500;
        line-height: 1.4;
      }

      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        padding: 14px 16px;
        border-bottom:
          1px solid
          var(--kg-border);
      }

      .title-wrap {
        display: flex;
        align-items: center;
        min-width: 0;
        gap: 11px;
      }

      .logo-wrapper {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        flex: 0 0 32px;
      }

      .logo {
        display: block;
        width: 29px;
        height: 29px;
        object-fit: contain;
      }

      :host([data-theme="dark"]) .logo {
        filter: invert(1);
      }

      .title {
        font-size: 15px;
        font-weight: 700;
        line-height: 1.3;
      }

      .subtitle {
        margin-top: 2px;
        font-size: 12px;
        line-height: 1.35;
        color: var(--kg-muted);
      }

      .badge {
        display: inline-flex;
        align-items: center;
        flex: 0 0 auto;
        padding: 5px 9px;
        border-radius: 999px;
        font-size: 10.5px;
        font-weight: 800;
        letter-spacing: 0.04em;
        white-space: nowrap;
      }

      .supported {
        background:
          var(--kg-supported-bg);
        color:
          var(--kg-supported-text);
      }

      .contradicted {
        background:
          var(--kg-contradicted-bg);
        color:
          var(--kg-contradicted-text);
      }

      .insufficient {
        background:
          var(--kg-insufficient-bg);
        color:
          var(--kg-insufficient-text);
      }

      .mixed {
        background:
          var(--kg-mixed-bg);
        color:
          var(--kg-mixed-text);
      }

      .not-verifiable,
      .neutral {
        background:
          var(--kg-neutral-bg);
        color:
          var(--kg-neutral-text);
      }

      .loading {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 15px 16px;
      }

      .loading-copy {
        min-width: 0;
        flex: 1;
      }

      .loading-title {
        font-size: 14px;
        font-weight: 700;
        line-height: 1.35;
      }

      .loading-subtitle {
        margin-top: 2px;
        font-size: 12px;
        line-height: 1.4;
        color: var(--kg-muted);
      }

      .loading-progress {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 9px;
        font-size: 11.5px;
        font-weight: 500;
        line-height: 1.4;
        color: var(--kg-muted);
      }

      .loading-pulse {
        width: 7px;
        height: 7px;
        flex: 0 0 7px;
        border-radius: 50%;
        background:
          var(--kg-text);
        animation:
          kgPulse
          1.25s
          ease-in-out
          infinite;
      }

      .thinking-dots {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        min-width: 17px;
      }

      .thinking-dot {
        width: 3px;
        height: 3px;
        border-radius: 50%;
        background:
          currentColor;
        opacity: 0.3;
        animation:
          kgDot
          1.1s
          ease-in-out
          infinite;
      }

      .thinking-dot:nth-child(2) {
        animation-delay:
          140ms;
      }

      .thinking-dot:nth-child(3) {
        animation-delay:
          280ms;
      }

      .spinner {
        width: 17px;
        height: 17px;
        flex: 0 0 17px;
        border:
          2px solid
          var(--kg-border);
        border-top-color:
          var(--kg-text);
        border-radius: 50%;
        animation:
          spin
          0.8s
          linear
          infinite;
      }

      .aggregate {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 18px;
        padding: 11px 16px;
        border-bottom:
          1px solid
          var(--kg-border);
        font-size: 12px;
        color: var(--kg-muted);
      }

      .aggregate strong {
        color: var(--kg-text);
      }

      .assessment {
        padding: 16px;
      }

      .assessment-label {
        margin-bottom: 8px;
        color: var(--kg-text);
        font-size: 13px;
        font-weight: 700;
        line-height: 1.35;
      }

      .assessment-text {
        margin-top: 0;
        font-size: 15px;
        font-weight: 500;
        line-height: 1.6;
      }

      .meta {
        display: flex;
        flex-wrap: wrap;
        gap: 5px 11px;
        margin-top: 10px;
        font-size: 12px;
        line-height: 1.45;
        color: var(--kg-muted);
      }

      .meta strong {
        color: var(--kg-text);
      }

      .claim-summary {
        padding: 14px 16px 4px;
      }

      .claim-summary-title {
        color: var(--kg-text);
        font-size: 13px;
        font-weight: 700;
        line-height: 1.45;
      }

      .claim-summary-counts {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 8px;
      }

      .summary-chip {
        display: inline-flex;
        align-items: center;
        padding: 4px 7px;
        border-radius: 999px;
        font-size: 10.5px;
        font-weight: 650;
        line-height: 1.3;
      }

      .claims {
        padding: 0 16px;
      }

      .claim {
        padding: 15px 0;
        border-bottom:
          1px solid
          var(--kg-border);
      }

      .claim:last-child {
        border-bottom: 0;
      }

      .claim-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 13px;
      }

      .claim-text {
        min-width: 0;
        font-size: 15px;
        line-height: 1.55;
        font-weight: 600;
      }

      .claim-reason {
        margin-top: 9px;
        font-size: 13px;
        line-height: 1.6;
      }

      .disclosure {
        width: 100%;
      }

      .disclosure-toggle {
        display: flex;
        align-items: center;
        width: fit-content;
        gap: 6px;
        margin: 0;
        padding: 0;
        border: 0;
        background: transparent;
        color: var(--kg-muted);
        cursor: pointer;
        font-size: 12px;
        font-weight: 650;
        line-height: 1.45;
        text-align: left;
        transition:
          color
          100ms
          ease;
      }

      .disclosure-toggle:hover {
        color: var(--kg-text);
      }

      .disclosure-arrow {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 8px;
        transform-origin: center;
        transition:
          transform
          120ms
          ease;
      }

      .disclosure.open
      > .disclosure-toggle
      .disclosure-arrow {
        transform:
          rotate(90deg);
      }

      .disclosure-panel {
        height: 0;
        overflow: hidden;
        opacity: 0;
      }

      .disclosure-inner {
        min-height: 0;
      }

      .claim-disclosure {
        padding:
          10px 16px 14px;
      }

      .claim-disclosure
      > .disclosure-panel
      > .disclosure-inner {
        margin-left: -16px;
        margin-right: -16px;
      }

      .detail-disclosure {
        margin-top: 10px;
      }

      .detail-content {
        padding-top: 9px;
      }

      .evidence-list {
        max-height: 280px;
        overflow: auto;
        padding: 11px;
        border-radius: 9px;
        background:
          var(--kg-soft);
      }

      .evidence {
        padding: 9px 0;
        border-bottom:
          1px solid
          var(--kg-border);
        font-size: 12px;
        line-height: 1.55;
      }

      .evidence:first-child {
        padding-top: 0;
      }

      .evidence:last-child {
        padding-bottom: 0;
        border-bottom: 0;
      }

      .evidence-title {
        font-size: 12.5px;
        font-weight: 650;
        line-height: 1.5;
      }

      .source {
        margin-top: 4px;
        color: var(--kg-muted);
        font-size: 11.5px;
        line-height: 1.45;
      }

      .source a {
        color: var(--kg-link);
        text-underline-offset: 2px;
      }

      .confidence-box {
        padding: 11px;
        border-radius: 9px;
        background:
          var(--kg-soft);
      }

      .confidence-overall {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 10px;
        font-size: 12px;
      }

      .confidence-overall strong {
        font-size: 13px;
      }

      .confidence-row {
        margin-top: 9px;
      }

      .confidence-line {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        font-size: 11px;
        line-height: 1.4;
      }

      .confidence-label {
        color: var(--kg-muted);
      }

      .confidence-value {
        color: var(--kg-text);
        font-weight: 650;
        white-space: nowrap;
      }

      .confidence-bar {
        height: 5px;
        margin-top: 5px;
        overflow: hidden;
        border-radius: 999px;
        background:
          var(--kg-border);
      }

      .confidence-fill {
        height: 100%;
        border-radius: inherit;
        background:
          var(--kg-text);
        transform-origin:
          left center;
        animation:
          kgBarIn
          250ms
          ease-out;
      }

      .confidence-note {
        margin-top: 11px;
        color: var(--kg-muted);
        font-size: 11px;
        line-height: 1.5;
      }

      .feedback {
        padding: 12px 16px 14px;
        border-top:
          1px solid
          var(--kg-border);
      }

      .feedback-body {
        padding-top: 4px;
      }

      .feedback-question {
        margin-top: 13px;
        font-size: 12px;
        font-weight: 650;
        line-height: 1.45;
      }

      .feedback-help {
        margin-top: 3px;
        color: var(--kg-muted);
        font-size: 11px;
      }

      .rating-row,
      .choice-row {
        display: flex;
        flex-wrap: wrap;
        gap: 7px;
        margin-top: 9px;
      }

      .rating-button,
      .choice-button {
        border:
          1px solid
          var(--kg-border);
        border-radius: 7px;
        background:
          var(--kg-bg);
        color:
          var(--kg-text);
        cursor: pointer;
        font-size: 12px;
        font-weight: 600;
      }

      .rating-button {
        width: 35px;
        height: 33px;
      }

      .choice-button {
        padding: 7px 12px;
      }

      .rating-button.selected,
      .choice-button.selected {
        border-color:
          var(--kg-text);
        background:
          var(--kg-text);
        color:
          var(--kg-bg);
      }

      .feedback textarea {
        width: 100%;
        min-height: 72px;
        resize: vertical;
        margin-top: 9px;
        padding: 9px 10px;
        border:
          1px solid
          var(--kg-border);
        border-radius: 8px;
        background:
          var(--kg-bg);
        color:
          var(--kg-text);
        font: inherit;
        font-size: 12px;
        line-height: 1.5;
      }

      .feedback-actions {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 10px;
      }

      .save-feedback {
        border: 0;
        border-radius: 7px;
        padding: 7px 12px;
        background:
          var(--kg-text);
        color:
          var(--kg-bg);
        cursor: pointer;
        font-size: 12px;
        font-weight: 650;
      }

      .save-feedback:disabled {
        cursor: default;
        opacity: 0.55;
      }

      .feedback-status {
        color:
          var(--kg-muted);
        font-size: 11px;
      }

      .feedback-privacy {
        margin-top: 9px;
        color:
          var(--kg-muted);
        font-size: 11px;
        line-height: 1.5;
      }

      .non-answer {
        padding: 16px;
      }

      .non-answer-title {
        color:
          var(--kg-text);
        font-size: 15px;
        font-weight: 700;
        line-height: 1.4;
      }

      .non-answer-copy {
        margin-top: 6px;
        color:
          var(--kg-muted);
        font-size: 13px;
        line-height: 1.55;
      }

      .evidence-explorer-note {
        margin-top: 8px;
        color:
          var(--kg-muted);
        font-size: 11px;
        line-height: 1.5;
      }

      .inline-action {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        margin-top: 12px;
        padding: 0;
        border: 0;
        background: transparent;
        color:
          var(--kg-text);
        cursor: pointer;
        font-size: 12.5px;
        font-weight: 650;
        text-align: left;
      }

      .inline-action:hover {
        text-decoration: underline;
        text-underline-offset: 2px;
      }

      .inline-action:disabled {
        cursor: wait;
        opacity: 0.6;
        text-decoration: none;
      }

      .explorer {
        padding: 16px;
      }

      .explorer-heading {
        color:
          var(--kg-text);
        font-size: 15px;
        font-weight: 700;
        line-height: 1.4;
      }

      .explorer-copy {
        margin-top: 5px;
        color:
          var(--kg-muted);
        font-size: 12px;
        line-height: 1.55;
      }

      .explorer-list {
        margin-top: 12px;
        padding: 11px;
        border-radius: 9px;
        background:
          var(--kg-soft);
      }

      .footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 10px 16px;
        border-top:
          1px solid
          var(--kg-border);
        color:
          var(--kg-muted);
        font-size: 11px;
        line-height: 1.45;
      }

      .report-link {
        color:
          var(--kg-link);
        font-weight: 650;
        text-decoration: none;
        white-space: nowrap;
      }

      .report-link:hover {
        color:
          var(--kg-text);
        text-decoration: underline;
      }

      .empty,
      .error,
      .reconnect {
        padding: 16px;
        font-size: 13px;
        line-height: 1.6;
      }

      .error-title,
      .reconnect-title {
        font-size: 14px;
        font-weight: 700;
      }

      .error-copy,
      .reconnect-copy {
        margin-top: 5px;
        color:
          var(--kg-muted);
      }

      .retry,
      .refresh {
        margin-top: 11px;
        border:
          1px solid
          var(--kg-border);
        border-radius: 7px;
        padding: 8px 11px;
        background:
          var(--kg-bg);
        color:
          var(--kg-text);
        cursor: pointer;
        font-size: 12px;
        font-weight: 650;
      }

      @keyframes kgPulse {
        0%,
        100% {
          opacity: 0.35;
          transform:
            scale(0.8);
        }

        50% {
          opacity: 1;
          transform:
            scale(1);
        }
      }

      @keyframes kgDot {
        0%,
        60%,
        100% {
          opacity: 0.25;
          transform:
            translateY(0);
        }

        30% {
          opacity: 1;
          transform:
            translateY(-2px);
        }
      }

      @keyframes kgBarIn {
        from {
          transform:
            scaleX(0);
        }

        to {
          transform:
            scaleX(1);
        }
      }

      @keyframes spin {
        to {
          transform:
            rotate(360deg);
        }
      }

      @media (
        prefers-reduced-motion:
        reduce
      ) {
        *,
        *::before,
        *::after {
          animation-duration:
            0.01ms !important;
          animation-iteration-count:
            1 !important;
          transition-duration:
            0.01ms !important;
          scroll-behavior:
            auto !important;
        }
      }
    </style>

    <div class="card"></div>
  `;

  return host;
}

function getVerificationHost(element) {
  const mapped = verificationHosts.get(element);

  if (mapped && mapped.isConnected) {
    return mapped;
  }

  const descendant = element.querySelector?.("[data-covid-kg-verification]");

  if (descendant) {
    verificationHosts.set(element, descendant);

    return descendant;
  }

  if (element.nextElementSibling?.matches("[data-covid-kg-verification]")) {
    const sibling = element.nextElementSibling;

    verificationHosts.set(element, sibling);

    return sibling;
  }

  return null;
}

function removeVerificationHost(element) {
  const host = getVerificationHost(element);

  if (host) {
    host.remove();
  }

  verificationHosts.delete(element);
}

function transferVerificationHost(fromElement, toElement, options = {}) {
  if (!fromElement || !toElement || fromElement === toElement) {
    return null;
  }

  const host = getVerificationHost(fromElement);

  if (!host) {
    return null;
  }

  verificationHosts.delete(fromElement);

  verificationHosts.set(toElement, host);

  delete host.dataset.kgPending;

  placeHost(host, toElement, options);

  applyTheme(host);

  return host;
}

function adoptPendingHostForAssistant(assistantElement) {
  const questionElement = findQuestionElementForAssistant(assistantElement);

  if (!questionElement) {
    return;
  }

  const host = getVerificationHost(questionElement);

  if (!host || host.dataset.kgPending !== "true") {
    return;
  }

  transferVerificationHost(questionElement, assistantElement);
}

function adoptPendingHostForNonAnswer(surface) {
  const questionElement = findUserMessageBeforeElement(surface);

  if (!questionElement) {
    return;
  }

  const host = getVerificationHost(questionElement);

  if (!host || host.dataset.kgPending !== "true") {
    return;
  }

  transferVerificationHost(questionElement, surface, {
    after: true,
  });
}

function cancelCardAnimations(card) {
  card.getAnimations().forEach((animation) => {
    animation.cancel();
  });

  const child = card.firstElementChild;

  if (child) {
    child.getAnimations().forEach((animation) => {
      animation.cancel();
    });
  }
}

function swapCardContent(card, content, className = "card") {
  const oldContent = card.firstElementChild;

  if (!oldContent || prefersReducedMotion()) {
    cancelCardAnimations(card);

    card.style.height = "";

    card.style.transition = "";

    card.style.overflow = "";

    card.className = className;

    card.replaceChildren(content);

    return;
  }

  const compactToCompact =
    card.classList.contains("compact-state") &&
    className.includes("compact-state");

  if (compactToCompact) {
    card.className = className;

    card.replaceChildren(content);

    content.animate(
      [
        {
          opacity: 0.55,
        },
        {
          opacity: 1,
        },
      ],
      {
        duration: 100,
        easing: "ease-out",
      },
    );

    return;
  }

  const transitionId = Number(card.dataset.kgTransitionId || 0) + 1;

  card.dataset.kgTransitionId = String(transitionId);

  cancelCardAnimations(card);

  const oldHeight = card.getBoundingClientRect().height;

  card.style.transition = "none";

  card.style.height = `${oldHeight}px`;

  card.style.overflow = "hidden";

  const fadeOut = oldContent.animate(
    [
      {
        opacity: 1,
        transform: "translateY(0px)",
      },
      {
        opacity: 0,
        transform: "translateY(-2px)",
      },
    ],
    {
      duration: CONTENT_FADE_OUT_MS,
      easing: "ease-out",
      fill: "forwards",
    },
  );

  const replace = () => {
    if (Number(card.dataset.kgTransitionId) !== transitionId) {
      return;
    }

    card.className = className;

    content.style.opacity = "0";

    content.style.transform = "translateY(4px)";

    card.replaceChildren(content);

    const newHeight = card.scrollHeight;

    card.getBoundingClientRect();

    requestAnimationFrame(() => {
      if (Number(card.dataset.kgTransitionId) !== transitionId) {
        return;
      }

      card.style.transition =
        `height ${CARD_RESIZE_MS}ms ` +
        "cubic-bezier(0.2, 0.8, 0.2, 1), " +
        `border-radius ${CARD_RESIZE_MS}ms ease`;

      card.style.height = `${newHeight}px`;

      const fadeIn = content.animate(
        [
          {
            opacity: 0,
            transform: "translateY(4px)",
          },
          {
            opacity: 1,
            transform: "translateY(0px)",
          },
        ],
        {
          duration: CONTENT_FADE_IN_MS,
          delay: 20,
          easing: "cubic-bezier(0.2, 0.8, 0.2, 1)",
          fill: "forwards",
        },
      );

      fadeIn.finished
        .catch(() => {})
        .finally(() => {
          if (Number(card.dataset.kgTransitionId) !== transitionId) {
            return;
          }

          content.style.opacity = "";

          content.style.transform = "";
        });

      setTimeout(() => {
        if (Number(card.dataset.kgTransitionId) !== transitionId) {
          return;
        }

        card.style.height = "";

        card.style.transition = "";

        card.style.overflow = "";
      }, CARD_RESIZE_MS + 60);
    });
  };

  fadeOut.finished.then(replace).catch(replace);
}

function createThinkingDots() {
  const dots = createElement("span", "thinking-dots");

  for (let index = 0; index < 3; index += 1) {
    dots.appendChild(createElement("span", "thinking-dot"));
  }

  return dots;
}

function resetNestedDisclosures(wrapper) {
  wrapper.querySelectorAll(".disclosure.open").forEach((nested) => {
    if (nested === wrapper) {
      return;
    }

    nested.classList.remove("open");

    const button = nested.querySelector(":scope > .disclosure-toggle");

    const panel = nested.querySelector(":scope > .disclosure-panel");

    if (button) {
      button.setAttribute("aria-expanded", "false");
    }

    if (panel) {
      panel.style.height = "0px";

      panel.style.opacity = "0";

      panel.style.transition = "";
    }
  });
}

function setDisclosureOpen(
  wrapper,
  button,
  panel,
  labelElement,
  options,
  open,
) {
  const currentOpen = wrapper.classList.contains("open");

  if (currentOpen === open) {
    return;
  }

  if (options.openLabel && options.closedLabel) {
    labelElement.textContent = open ? options.openLabel : options.closedLabel;
  }

  button.setAttribute("aria-expanded", open ? "true" : "false");

  if (!open && options.resetChildrenOnClose) {
    resetNestedDisclosures(wrapper);
  }

  if (prefersReducedMotion()) {
    wrapper.classList.toggle("open", open);

    panel.style.height = open ? "auto" : "0px";

    panel.style.opacity = open ? "1" : "0";

    return;
  }

  panel.style.transition =
    `height ${DISCLOSURE_MS}ms ` +
    "cubic-bezier(0.2, 0.8, 0.2, 1), " +
    "opacity 85ms ease";

  if (open) {
    wrapper.classList.add("open");

    panel.style.height = "0px";

    panel.style.opacity = "0";

    panel.getBoundingClientRect();

    const targetHeight = panel.scrollHeight;

    requestAnimationFrame(() => {
      panel.style.height = `${targetHeight}px`;

      panel.style.opacity = "1";
    });

    const finish = (event) => {
      if (event.propertyName !== "height") {
        return;
      }

      panel.style.height = "auto";

      panel.style.transition = "";

      panel.removeEventListener("transitionend", finish);
    };

    panel.addEventListener("transitionend", finish);

    return;
  }

  const currentHeight = panel.getBoundingClientRect().height;

  panel.style.height = `${currentHeight}px`;

  panel.style.opacity = "1";

  panel.getBoundingClientRect();

  wrapper.classList.remove("open");

  requestAnimationFrame(() => {
    panel.style.height = "0px";

    panel.style.opacity = "0";
  });

  const finish = (event) => {
    if (event.propertyName !== "height") {
      return;
    }

    panel.style.transition = "";

    panel.removeEventListener("transitionend", finish);
  };

  panel.addEventListener("transitionend", finish);
}

function createDisclosure(label, content, options = {}) {
  const wrapper = createElement(
    "div",
    ("disclosure " + (options.className || "")).trim(),
  );

  const button = createElement("button", "disclosure-toggle");

  button.type = "button";

  button.setAttribute("aria-expanded", "false");

  const arrow = createElement("span", "disclosure-arrow", "›");

  const labelElement = createElement("span", "", label);

  button.appendChild(arrow);

  button.appendChild(labelElement);

  const panel = createElement("div", "disclosure-panel");

  panel.style.height = "0px";

  panel.style.opacity = "0";

  const inner = createElement("div", "disclosure-inner");

  inner.appendChild(content);

  panel.appendChild(inner);

  wrapper.appendChild(button);

  wrapper.appendChild(panel);

  button.addEventListener("click", () => {
    setDisclosureOpen(
      wrapper,
      button,
      panel,
      labelElement,
      options,
      !wrapper.classList.contains("open"),
    );
  });

  return wrapper;
}

function renderCompactState(element, state, text, options = {}) {
  const host = createVerificationHost(element, options);

  if (host.dataset.kgState === state) {
    return;
  }

  host.dataset.kgState = state;

  applyTheme(host);

  const card = host.shadowRoot.querySelector(".card");

  const shell = createElement("div", "content-shell");

  const row = createElement("div", "compact-row");

  const logo = createElement("span", "compact-logo");

  logo.appendChild(createLogo());

  row.appendChild(logo);

  const copy = createElement("div", "compact-copy");

  copy.appendChild(
    createElement("span", "compact-title", "Knowledge Graph Check"),
  );

  copy.appendChild(createElement("span", "compact-separator", "·"));

  copy.appendChild(createElement("span", "compact-status", text));

  copy.appendChild(createThinkingDots());

  row.appendChild(copy);

  shell.appendChild(row);

  swapCardContent(card, shell, "card compact-state");
}

function renderPendingForUser(userElement) {
  const host = createVerificationHost(userElement, {
    after: true,
  });

  host.dataset.kgPending = "true";

  renderCompactState(userElement, "waiting", "Waiting for response", {
    after: true,
  });
}

function renderAssistantWaiting(element) {
  adoptPendingHostForAssistant(element);

  renderCompactState(element, "waiting", "Waiting for response");
}

function renderPreparingVerification(element) {
  adoptPendingHostForAssistant(element);

  renderCompactState(element, "preparing", "Preparing verification");
}

function renderVerificationLoading(element, existing = false) {
  adoptPendingHostForAssistant(element);

  const host = createVerificationHost(element);

  if (host.dataset.kgState === "verifying") {
    return;
  }

  host.dataset.kgState = "verifying";

  delete host.dataset.kgPending;

  applyTheme(host);

  const card = host.shadowRoot.querySelector(".card");

  const shell = createElement("div", "content-shell");

  const wrapper = createElement("div", "loading");

  wrapper.appendChild(createLogo());

  const copy = createElement("div", "loading-copy");

  copy.appendChild(
    createElement("div", "loading-title", "Knowledge Graph Check"),
  );

  copy.appendChild(
    createElement(
      "div",
      "loading-subtitle",
      existing ? "Verifying this response..." : "Verifying response...",
    ),
  );

  const progress = createElement("div", "loading-progress");

  progress.appendChild(createElement("span", "loading-pulse"));

  progress.appendChild(
    createElement("span", "", "Checking source-backed evidence"),
  );

  progress.appendChild(createThinkingDots());

  copy.appendChild(progress);

  wrapper.appendChild(copy);

  wrapper.appendChild(createElement("div", "spinner"));

  shell.appendChild(wrapper);

  swapCardContent(card, shell);
}

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

async function verifyAssistantMessage(element, options = {}) {
  if (!element || !element.isConnected) {
    return {
      status: "skipped",
    };
  }

  adoptPendingHostForAssistant(element);

  const responseText =
    options.responseText || extractAssistantMessageText(element);

  const question = options.question || findQuestionForAssistant(element);

  if (!responseText || !question) {
    return {
      status: "skipped",
    };
  }

  if (!responseSurfaceHasCovidContext(element, question, responseText)) {
    removeVerificationHost(element);

    return {
      status: "skipped",
    };
  }

  if (isHostNonAnswer(responseText)) {
    renderNonAnswer(element, question);

    return {
      status: "non_answer",
    };
  }

  if (assistantVerifiedText.get(element) === responseText) {
    const data = assistantVerificationData.get(element);

    if (
      data &&
      (!getVerificationHost(element) ||
        getVerificationHost(element)?.dataset.kgState !== "result")
    ) {
      renderVerification(element, data);
    }

    return {
      status: "restored",
    };
  }

  if (assistantPendingText.get(element) === responseText) {
    return {
      status: "pending",
    };
  }

  if (!options.force) {
    try {
      const cached = await getCachedVerification(question, responseText);

      if (cached?.data) {
        assistantVerifiedText.set(element, responseText);

        assistantVerificationData.set(element, cached.data);

        renderVerification(element, cached.data);

        return {
          status: "restored",
        };
      }
    } catch (error) {
      if (isInvalidContextError(error)) {
        renderReconnect(element);

        return {
          status: "error",
        };
      }
    }
  }

  assistantPendingText.set(element, responseText);

  renderVerificationLoading(element, Boolean(options.existing));

  try {
    const response = await requestResponseVerification(question, responseText);

    if (!response || !response.ok) {
      throw new Error(response?.error || "Knowledge graph request failed");
    }

    const data = {
      ...response.data,
      question: response.data?.question || question,
      response: response.data?.response || responseText,
    };

    assistantVerifiedText.set(element, responseText);

    assistantVerificationData.set(element, data);

    try {
      await saveCachedVerification(question, responseText, data);
    } catch {}

    renderVerification(element, data);

    return {
      status: "verified",
    };
  } catch (error) {
    renderVerificationError(element, question, responseText, error);

    return {
      status: "error",
    };
  } finally {
    assistantPendingText.delete(element);
  }
}

function scheduleAssistantVerification(
  element,
  existing = false,
  delay = RESPONSE_SETTLE_MS,
) {
  if (!element || !element.isConnected) {
    return;
  }

  adoptPendingHostForAssistant(element);

  const currentText = extractAssistantMessageText(element);

  const question = findQuestionForAssistant(element);

  if (!currentText || !question) {
    return;
  }

  if (!responseSurfaceHasCovidContext(element, question, currentText)) {
    removeVerificationHost(element);

    return;
  }

  if (isHostNonAnswer(currentText)) {
    renderNonAnswer(element, question);

    return;
  }

  if (assistantVerifiedText.get(element) === currentText) {
    const data = assistantVerificationData.get(element);

    if (
      data &&
      (!getVerificationHost(element) ||
        getVerificationHost(element)?.dataset.kgState !== "result")
    ) {
      renderVerification(element, data);
    }

    return;
  }

  if (currentText && assistantPendingText.get(element) === currentText) {
    return;
  }

  if (assistantTimers.has(element)) {
    return;
  }

  if (assistantGenerationInProgress()) {
    renderAssistantWaiting(element);

    const timer = setTimeout(() => {
      assistantTimers.delete(element);

      scheduleAssistantVerification(element, existing, GENERATION_RECHECK_MS);
    }, GENERATION_RECHECK_MS);

    assistantTimers.set(element, timer);

    return;
  }

  renderPreparingVerification(element);

  const settledText = currentText;

  const timer = setTimeout(() => {
    assistantTimers.delete(element);

    if (assistantGenerationInProgress()) {
      scheduleAssistantVerification(element, existing, GENERATION_RECHECK_MS);

      return;
    }

    const latestText = extractAssistantMessageText(element);

    if (!latestText) {
      scheduleAssistantVerification(element, existing, GENERATION_RECHECK_MS);

      return;
    }

    if (latestText !== settledText) {
      scheduleAssistantVerification(element, existing, RESPONSE_SETTLE_MS);

      return;
    }

    verifyAssistantMessage(element, {
      existing,
    });
  }, delay);

  assistantTimers.set(element, timer);
}

function handleHostNonAnswerSurface(element) {
  const question = findQuestionForElement(element);

  if (!question) {
    return false;
  }

  const responseText = normalizeHostNonAnswerText(element.textContent);

  if (!responseSurfaceHasCovidContext(element, question, responseText)) {
    return false;
  }

  adoptPendingHostForNonAnswer(element);

  renderNonAnswer(element, question);

  return true;
}

function clearStalePendingHosts(keepHost = null) {
  document
    .querySelectorAll('[data-covid-kg-verification][data-kg-pending="true"]')
    .forEach((host) => {
      if (host !== keepHost) {
        host.remove();
      }
    });
}

function reconcileLatestUserTurn() {
  const latestUser = getLatestUserMessage();

  if (!latestUser) {
    clearStalePendingHosts();

    return;
  }

  if (!userTurnHasCovidContext(latestUser)) {
    clearStalePendingHosts();

    return;
  }

  const assistant = findAssistantForUserTurn(latestUser);

  if (assistant) {
    const pendingHost = getVerificationHost(latestUser);

    if (pendingHost && pendingHost.dataset.kgPending === "true") {
      transferVerificationHost(latestUser, assistant);
    }

    clearStalePendingHosts();

    scheduleAssistantVerification(assistant, false);

    return;
  }

  const nonAnswer = findNonAnswerForUserTurn(latestUser);

  if (nonAnswer) {
    const pendingHost = getVerificationHost(latestUser);

    if (pendingHost && pendingHost.dataset.kgPending === "true") {
      transferVerificationHost(latestUser, nonAnswer, {
        after: true,
      });
    }

    clearStalePendingHosts();

    handleHostNonAnswerSurface(nonAnswer);

    return;
  }

  renderPendingForUser(latestUser);

  clearStalePendingHosts(getVerificationHost(latestUser));
}

function scheduleLatestAssistantVerification(existing = false) {
  const latestUser = getLatestUserMessage();

  if (!latestUser) {
    return;
  }

  const assistant = findAssistantForUserTurn(latestUser);

  if (assistant) {
    scheduleAssistantVerification(assistant, existing);

    return;
  }

  if (assistantGenerationInProgress()) {
    return;
  }

  const nonAnswer = findNonAnswerForUserTurn(latestUser);

  if (nonAnswer) {
    handleHostNonAnswerSurface(nonAnswer);
  }
}

function cancelAssistantTimers() {
  for (const timer of assistantTimers.values()) {
    clearTimeout(timer);
  }

  assistantTimers.clear();
}

async function restoreCachedVerifications() {
  const startUrl = location.href;

  let cache;

  try {
    cache = await getVerificationCache();
  } catch {
    return;
  }

  if (startUrl !== location.href) {
    return;
  }

  const assistants = getAssistantMessages();

  for (const element of assistants) {
    const question = findQuestionForAssistant(element);

    const responseText = extractAssistantMessageText(element);

    if (!question || !responseText) {
      continue;
    }

    if (!responseSurfaceHasCovidContext(element, question, responseText)) {
      continue;
    }

    if (isHostNonAnswer(responseText)) {
      renderNonAnswer(element, question);

      continue;
    }

    const cached = cache[verificationCacheId(question, responseText)];

    if (!cached?.data) {
      continue;
    }

    assistantVerifiedText.set(element, responseText);

    assistantVerificationData.set(element, cached.data);

    renderVerification(element, cached.data);
  }

  for (const element of findHostNonAnswerSurfaces()) {
    handleHostNonAnswerSurface(element);
  }
}

async function inspectLatestRetrieval() {
  const text = getLatestUserQuery();

  if (!text) {
    throw new Error("No user query was found.");
  }

  const response = await requestContext(text);

  if (!response || !response.ok) {
    throw new Error(response?.error || "Knowledge graph request failed");
  }

  return response.data;
}

async function groundCurrentDraft() {
  const composer = findComposer();

  if (!composer) {
    throw new Error("ChatGPT prompt editor was not found.");
  }

  const currentText = getComposerText(composer);

  if (!currentText) {
    throw new Error("Enter a draft before grounding it.");
  }

  if (extractOriginalQuery(currentText)) {
    throw new Error("The current draft is already grounded.");
  }

  const response = await requestAugmentation(currentText);

  if (!response || !response.ok) {
    throw new Error(response?.error || "Knowledge graph request failed");
  }

  lastOriginalDraft = currentText;

  setComposerText(composer, response.data.augmentedPrompt);

  return {
    evidenceCount: (response.data.facts || []).length,
  };
}

function restoreOriginalDraft() {
  const composer = findComposer();

  if (!composer) {
    throw new Error("ChatGPT prompt editor was not found.");
  }

  const currentText = getComposerText(composer);

  const embeddedOriginal = extractOriginalQuery(currentText);

  const original = lastOriginalDraft || embeddedOriginal;

  if (!original) {
    throw new Error("There is no grounded draft to restore.");
  }

  setComposerText(composer, original);

  lastOriginalDraft = null;

  return {
    restored: true,
  };
}

async function checkPreviousResponses() {
  if (assistantGenerationInProgress()) {
    throw new Error("Wait for the current ChatGPT response to finish first.");
  }

  const surfaces = getResponseSurfaces();

  let verified = 0;
  let restored = 0;
  let skipped = 0;
  let nonAnswers = 0;
  let errors = 0;

  for (const surface of surfaces) {
    const question = surface.question || "";

    const response = surface.response || "";

    if (
      !question ||
      !responseSurfaceHasCovidContext(surface.element, question, response)
    ) {
      skipped += 1;

      continue;
    }

    if (surface.kind === "non_answer") {
      renderNonAnswer(surface.element, question);

      nonAnswers += 1;

      continue;
    }

    const result = await verifyAssistantMessage(surface.element, {
      existing: true,
    });

    switch (result.status) {
      case "verified":
        verified += 1;

        break;

      case "restored":
        restored += 1;

        break;

      case "non_answer":
        nonAnswers += 1;

        break;

      case "error":
        errors += 1;

        break;

      default:
        skipped += 1;

        break;
    }
  }

  return {
    total: surfaces.length,
    verified,
    restored,
    skipped,
    nonAnswers,
    errors,
  };
}

function currentPopupStatus() {
  const surfaces = getResponseSurfaces();

  const eligible = surfaces.filter(
    (surface) =>
      surface.question &&
      responseSurfaceHasCovidContext(
        surface.element,
        surface.question,
        surface.response,
      ),
  );

  const handled = eligible.filter((surface) => {
    const state = getVerificationHost(surface.element)?.dataset.kgState;

    return (
      state === "result" ||
      state === "non-answer" ||
      state === "evidence-explorer"
    );
  }).length;

  const composer = findComposer();

  const composerText = composer ? getComposerText(composer) : "";

  const embeddedOriginal = composerText
    ? extractOriginalQuery(composerText)
    : null;

  const latestQuery = getLatestUserQuery();

  return {
    url: location.href,
    covidContext: conversationHasCovidContext(),
    latestQuery,
    renderedChecks: handled,
    assistantResponses: eligible.length,
    groundedDraft: Boolean(lastOriginalDraft || embeddedOriginal),
    composerAvailable: Boolean(composer),
    composerHasDraft: Boolean(composerText),
    canGroundDraft: Boolean(composer && composerText && !embeddedOriginal),
    canRestoreDraft: Boolean(
      composer && (lastOriginalDraft || embeddedOriginal),
    ),
    canInspectLatest: Boolean(latestQuery),
    generationInProgress: assistantGenerationInProgress(),
  };
}

function handleConversationChange() {
  cancelAssistantTimers();

  clearStalePendingHosts();

  if (conversationChangeTimer) {
    clearTimeout(conversationChangeTimer);
  }

  conversationChangeTimer = setTimeout(async () => {
    conversationChangeTimer = null;

    await restoreCachedVerifications();

    reconcileLatestUserTurn();

    scheduleLatestAssistantVerification(true);
  }, CONVERSATION_SETTLE_MS);
}

function detectConversationChange() {
  if (location.href === lastConversationUrl) {
    return false;
  }

  lastConversationUrl = location.href;

  handleConversationChange();

  return true;
}

function reconcilePage() {
  syncThemes();

  if (detectConversationChange()) {
    return;
  }

  reconcileLatestUserTurn();

  scheduleLatestAssistantVerification(false);
}

function schedulePageReconciliation() {
  if (mutationFrame !== null) {
    return;
  }

  mutationFrame = requestAnimationFrame(() => {
    mutationFrame = null;

    reconcilePage();
  });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) {
    return false;
  }

  if (message.type === "KG_POPUP_STATUS") {
    sendResponse({
      ok: true,
      data: currentPopupStatus(),
    });

    return false;
  }

  if (message.type === "KG_POPUP_INSPECT_LATEST") {
    inspectLatestRetrieval()
      .then((data) => {
        sendResponse({
          ok: true,
          data,
        });
      })
      .catch((error) => {
        sendResponse({
          ok: false,
          error: error.message,
        });
      });

    return true;
  }

  if (message.type === "KG_POPUP_GROUND_DRAFT") {
    groundCurrentDraft()
      .then((data) => {
        sendResponse({
          ok: true,
          data,
        });
      })
      .catch((error) => {
        sendResponse({
          ok: false,
          error: error.message,
        });
      });

    return true;
  }

  if (message.type === "KG_POPUP_RESTORE_DRAFT") {
    try {
      sendResponse({
        ok: true,
        data: restoreOriginalDraft(),
      });
    } catch (error) {
      sendResponse({
        ok: false,
        error: error.message,
      });
    }

    return false;
  }

  if (message.type === "KG_POPUP_CHECK_PREVIOUS") {
    checkPreviousResponses()
      .then((data) => {
        sendResponse({
          ok: true,
          data,
        });
      })
      .catch((error) => {
        sendResponse({
          ok: false,
          error: error.message,
        });
      });

    return true;
  }

  return false;
});

const observer = new MutationObserver(schedulePageReconciliation);

observer.observe(document.documentElement, {
  childList: true,
  subtree: true,
  characterData: true,
});

const themeObserver = new MutationObserver(syncThemes);

themeObserver.observe(document.documentElement, {
  attributes: true,
  attributeFilter: ["class", "data-theme", "style"],
});

if (document.body) {
  themeObserver.observe(document.body, {
    attributes: true,
    attributeFilter: ["class", "data-theme", "style"],
  });
}

setTimeout(async () => {
  await restoreCachedVerifications();

  reconcileLatestUserTurn();

  scheduleLatestAssistantVerification(true);
}, INITIAL_DELAY_MS);
