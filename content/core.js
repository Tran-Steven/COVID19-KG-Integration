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
