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
