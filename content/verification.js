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
