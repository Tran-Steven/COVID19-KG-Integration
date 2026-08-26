const overviewTab =
  document.getElementById(
    "overviewTab"
  );

const aboutTab =
  document.getElementById(
    "aboutTab"
  );

const advancedTab =
  document.getElementById(
    "advancedTab"
  );

const mainTabs =
  document.getElementById(
    "mainTabs"
  );

const overviewView =
  document.getElementById(
    "overviewView"
  );

const aboutView =
  document.getElementById(
    "aboutView"
  );

const advancedView =
  document.getElementById(
    "advancedView"
  );

const retrievalView =
  document.getElementById(
    "retrievalView"
  );

const retrievalBack =
  document.getElementById(
    "retrievalBack"
  );

const backendDot =
  document.getElementById(
    "backendDot"
  );

const backendStatus =
  document.getElementById(
    "backendStatus"
  );

const pageStatus =
  document.getElementById(
    "pageStatus"
  );

const verificationDetail =
  document.getElementById(
    "verificationDetail"
  );

const conversationDetail =
  document.getElementById(
    "conversationDetail"
  );

const inspectButton =
  document.getElementById(
    "inspectButton"
  );

const previousButton =
  document.getElementById(
    "previousButton"
  );

const groundDraftButton =
  document.getElementById(
    "groundDraftButton"
  );

const restoreDraftButton =
  document.getElementById(
    "restoreDraftButton"
  );

const labsInfoButton =
  document.getElementById(
    "labsInfoButton"
  );

const labsInfo =
  document.getElementById(
    "labsInfo"
  );

const actionStatus =
  document.getElementById(
    "actionStatus"
  );

const technicalStatus =
  document.getElementById(
    "technicalStatus"
  );

const technicalRoute =
  document.getElementById(
    "technicalRoute"
  );

const technicalRelation =
  document.getElementById(
    "technicalRelation"
  );

const technicalEvidence =
  document.getElementById(
    "technicalEvidence"
  );

const technicalConfidence =
  document.getElementById(
    "technicalConfidence"
  );

const technicalEntities =
  document.getElementById(
    "technicalEntities"
  );

const rawContext =
  document.getElementById(
    "rawContext"
  );

const versionText =
  document.getElementById(
    "versionText"
  );

const PAGE_REFRESH_MS =
  650;

const BACKEND_REFRESH_MS =
  3000;

let actionStatusTimer =
  null;

let pageRefreshInFlight =
  false;

function showMainView(
  name
) {
  mainTabs.style.display =
    "";

  retrievalView.classList
    .remove(
      "active"
    );

  overviewTab.classList
    .toggle(
      "is-active",
      name === "overview"
    );

  aboutTab.classList
    .toggle(
      "is-active",
      name === "about"
    );

  advancedTab.classList
    .toggle(
      "is-active",
      name === "advanced"
    );

  overviewView.classList
    .toggle(
      "active",
      name === "overview"
    );

  aboutView.classList
    .toggle(
      "active",
      name === "about"
    );

  advancedView.classList
    .toggle(
      "active",
      name === "advanced"
    );
}

function showRetrievalView() {
  overviewView.classList
    .remove(
      "active"
    );

  aboutView.classList
    .remove(
      "active"
    );

  advancedView.classList
    .remove(
      "active"
    );

  mainTabs.style.display =
    "none";

  retrievalView.classList
    .add(
      "active"
    );
}

overviewTab.addEventListener(
  "click",
  () => {
    showMainView(
      "overview"
    );
  }
);

aboutTab.addEventListener(
  "click",
  () => {
    showMainView(
      "about"
    );
  }
);

advancedTab.addEventListener(
  "click",
  () => {
    showMainView(
      "advanced"
    );
  }
);

retrievalBack.addEventListener(
  "click",
  () => {
    showMainView(
      "advanced"
    );
  }
);

labsInfoButton.addEventListener(
  "click",
  () => {
    labsInfo.classList
      .toggle(
        "visible"
      );
  }
);

function setActionStatus(
  text,
  error = false
) {
  if (
    actionStatusTimer
  ) {
    clearTimeout(
      actionStatusTimer
    );

    actionStatusTimer =
      null;
  }

  actionStatus.textContent =
    text || "";

  actionStatus.classList
    .toggle(
      "error",
      error
    );

  if (!text) {
    return;
  }

  actionStatusTimer =
    setTimeout(
      () => {
        actionStatus.textContent =
          "";

        actionStatus.classList
          .remove(
            "error"
          );

        actionStatusTimer =
          null;
      },
      4500
    );
}

function actionIsBusy(
  button
) {
  return (
    button.dataset.busy ===
    "true"
  );
}

function setTextActionBusy(
  button,
  busy,
  busyText = ""
) {
  if (busy) {
    if (
      !button.dataset
        .originalText
    ) {
      button.dataset
        .originalText =
          button.textContent;
    }

    button.dataset.busy =
      "true";

    button.disabled =
      true;

    if (busyText) {
      button.textContent =
        busyText;
    }

    return;
  }

  delete button.dataset
    .busy;

  button.disabled =
    false;

  if (
    button.dataset
      .originalText
  ) {
    button.textContent =
      button.dataset
        .originalText;

    delete button.dataset
      .originalText;
  }
}

function setActionAvailability(
  button,
  available,
  enabledText,
  unavailableText,
  unavailableReason
) {
  if (
    actionIsBusy(
      button
    )
  ) {
    return;
  }

  button.dataset.available =
    available
      ? "true"
      : "false";

  button.classList.toggle(
    "is-unavailable",
    !available
  );

  button.setAttribute(
    "aria-disabled",
    available
      ? "false"
      : "true"
  );

  button.tabIndex =
    available
      ? 0
      : -1;

  button.textContent =
    available
      ? enabledText
      : unavailableText;

  button.title =
    available
      ? ""
      : unavailableReason;
}

function setInspectState(
  data
) {
  setActionAvailability(
    inspectButton,
    Boolean(
      data.canInspectLatest
    ),
    "View details →",
    "View details",
    (
      "Open a conversation or " +
      "enter a prompt to enable."
    )
  );
}

function setGroundDraftState(
  data
) {
  let reason =
    "";

  if (
    data.groundedDraft
  ) {
    reason =
      (
        "The current draft is " +
        "already grounded."
      );
  } else if (
    data.composerAvailable
  ) {
    reason =
      (
        "Enter a draft in ChatGPT " +
        "to enable."
      );
  } else {
    reason =
      (
        "The ChatGPT composer is " +
        "not available on this page."
      );
  }

  setActionAvailability(
    groundDraftButton,
    Boolean(
      data.canGroundDraft
    ),
    (
      "Ground draft with " +
      "Knowledge Graph →"
    ),
    (
      "Ground draft with " +
      "Knowledge Graph"
    ),
    reason
  );
}

async function getActiveTab() {
  const currentWindowTabs =
    await chrome.tabs.query({
      active:
        true,
      currentWindow:
        true,
    });

  const currentTab =
    currentWindowTabs[0];

  if (
    currentTab &&
    isChatGPTTab(
      currentTab
    )
  ) {
    return currentTab;
  }

  const activeTabs =
    await chrome.tabs.query({
      active:
        true,
    });

  const chatGPTTab =
    activeTabs.find(
      (tab) =>
        isChatGPTTab(
          tab
        )
    );

  return (
    chatGPTTab ||
    currentTab ||
    activeTabs[0] ||
    null
  );
}

function isChatGPTTab(
  tab
) {
  if (
    !tab ||
    !tab.url
  ) {
    return false;
  }

  return (
    tab.url.startsWith(
      "https://chatgpt.com/"
    ) ||
    tab.url.startsWith(
      "https://chat.openai.com/"
    )
  );
}

async function sendToPage(
  message
) {
  const tab =
    await getActiveTab();

  if (
    !isChatGPTTab(
      tab
    )
  ) {
    throw new Error(
      "Open ChatGPT to use this feature."
    );
  }

  try {
    return await chrome.tabs
      .sendMessage(
        tab.id,
        message
      );
  } catch {
    throw new Error(
      (
        "Refresh ChatGPT to reconnect " +
        "the extension."
      )
    );
  }
}

async function checkBackend() {
  try {
    const response =
      await fetch(
        "http://localhost:8000/health",
        {
          cache:
            "no-store",
        }
      );

    if (
      !response.ok
    ) {
      throw new Error();
    }

    const data =
      await response.json();

    if (
      data.status !==
      "ok"
    ) {
      throw new Error();
    }

    backendDot.classList
      .add(
        "connected"
      );

    backendDot.classList
      .remove(
        "error"
      );

    backendStatus.textContent =
      "Backend connected";
  } catch {
    backendDot.classList
      .remove(
        "connected"
      );

    backendDot.classList
      .add(
        "error"
      );

    backendStatus.textContent =
      "Backend unavailable";
  }
}

function updateConversationSection(
  data
) {
  if (
    !data.covidContext
  ) {
    conversationDetail.textContent =
      "No active COVID-19 conversation.";

    previousButton.style.display =
      "none";

    return;
  }

  if (
    data.assistantResponses ===
    0
  ) {
    conversationDetail.textContent =
      "No previous responses to check.";

    previousButton.style.display =
      "none";

    return;
  }

  if (
    data.renderedChecks >=
    data.assistantResponses
  ) {
    conversationDetail.textContent =
      (
        "All currently eligible responses " +
        "have been checked."
      );

    previousButton.style.display =
      "none";

    return;
  }

  if (
    data.renderedChecks ===
    0
  ) {
    conversationDetail.textContent =
      (
        "Previous responses may be " +
        "available to check."
      );
  } else {
    conversationDetail.textContent =
      (
        `${data.renderedChecks} Knowledge Graph ` +
        `Check${
          data.renderedChecks ===
            1
            ? ""
            : "s"
        } currently shown.`
      );
  }

  previousButton.style.display =
    "inline-flex";

  if (
    !actionIsBusy(
      previousButton
    )
  ) {
    previousButton.disabled =
      false;

    previousButton.dataset.available =
      "true";

    previousButton.classList
      .remove(
        "is-unavailable"
      );

    previousButton.textContent =
      "Check previous responses →";
  }
}

async function refreshPageStatus() {
  if (
    pageRefreshInFlight
  ) {
    return null;
  }

  pageRefreshInFlight =
    true;

  try {
    const response =
      await sendToPage({
        type:
          "KG_POPUP_STATUS",
      });

    if (
      !response ||
      !response.ok
    ) {
      throw new Error(
        response?.error ||
        "Unable to read ChatGPT."
      );
    }

    const data =
      response.data;

    pageStatus.textContent =
      data.covidContext
        ? "COVID-19 context detected"
        : "No active COVID-19 context";

    if (
      data.generationInProgress
    ) {
      verificationDetail.textContent =
        (
          "ChatGPT is responding. " +
          "Verification will run when " +
          "the answer finishes."
        );
    } else if (
      data.renderedChecks > 0
    ) {
      verificationDetail.textContent =
        (
          `${data.renderedChecks} Knowledge Graph ` +
          `Check${
            data.renderedChecks ===
              1
              ? ""
              : "s"
          } currently shown in this conversation.`
        );
    } else if (
      data.covidContext
    ) {
      verificationDetail.textContent =
        (
          "COVID-19 responses are " +
          "checked automatically."
        );
    } else {
      verificationDetail.textContent =
        (
          "COVID-19 responses are checked " +
          "automatically when relevant " +
          "context is detected."
        );
    }

    setInspectState(
      data
    );

    setGroundDraftState(
      data
    );

    updateConversationSection(
      data
    );

    restoreDraftButton.style.display =
      data.canRestoreDraft
        ? "inline-flex"
        : "none";

    return data;
  } catch (error) {
    pageStatus.textContent =
      "ChatGPT not connected";

    verificationDetail.textContent =
      error.message;

    conversationDetail.textContent =
      "Conversation controls unavailable.";

    previousButton.style.display =
      "none";

    setActionAvailability(
      inspectButton,
      false,
      "View details →",
      "View details",
      "Refresh ChatGPT to reconnect."
    );

    setActionAvailability(
      groundDraftButton,
      false,
      (
        "Ground draft with " +
        "Knowledge Graph →"
      ),
      (
        "Ground draft with " +
        "Knowledge Graph"
      ),
      "Refresh ChatGPT to reconnect."
    );

    restoreDraftButton.style.display =
      "none";

    return null;
  } finally {
    pageRefreshInFlight =
      false;
  }
}

function parseContextValue(
  context,
  key
) {
  const expression =
    new RegExp(
      `^${key}=(.+)$`,
      "m"
    );

  const match =
    String(
      context || ""
    ).match(
      expression
    );

  return match
    ? match[1].trim()
    : null;
}

function formatConfidence(
  context
) {
  const score =
    parseContextValue(
      context,
      "confidence_score"
    );

  const level =
    parseContextValue(
      context,
      "confidence_level"
    );

  const calibrated =
    parseContextValue(
      context,
      "confidence_calibrated"
    );

  const parts =
    [];

  if (score) {
    const numeric =
      Number(score);

    parts.push(
      Number.isNaN(
        numeric
      )
        ? score
        : `${Math.round(
            numeric * 100
          )}%`
    );
  }

  if (level) {
    parts.push(
      (
        level.charAt(0)
          .toUpperCase() +
        level.slice(1)
          .toLowerCase()
      )
    );
  }

  if (
    calibrated ===
    "false"
  ) {
    parts.push(
      "uncalibrated"
    );
  }

  return parts.length
    ? parts.join(
        " · "
      )
    : "—";
}

function renderTechnicalData(
  data
) {
  const context =
    data.context ||
    "";

  technicalStatus.textContent =
    parseContextValue(
      context,
      "status"
    ) ||
    "—";

  technicalRoute.textContent =
    parseContextValue(
      context,
      "method"
    ) ||
    "—";

  technicalRelation.textContent =
    (
      data.relationships &&
      data.relationships.length >
        0
    )
      ? (
          data.relationships[0]
            .relationship ||
          "—"
        )
      : "—";

  const evidenceCount =
    (
      data.facts ||
      []
    ).length;

  technicalEvidence.textContent =
    (
      `${evidenceCount} ` +
      `record${
        evidenceCount ===
          1
          ? ""
          : "s"
      }`
    );

  technicalConfidence.textContent =
    formatConfidence(
      context
    );

  const entities =
    (data.entities || [])
      .map(
        (entity) => {
          const candidate =
            entity.candidates
              ?.length
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
      .filter(
        Boolean
      );

  technicalEntities.textContent =
    entities.length
      ? entities.join(
          ", "
        )
      : "None required";

  rawContext.textContent =
    context ||
    "No raw grounding context returned.";

  showRetrievalView();
}

inspectButton.addEventListener(
  "click",
  async () => {
    if (
      inspectButton.dataset.available !==
      "true"
    ) {
      return;
    }

    setTextActionBusy(
      inspectButton,
      true,
      "Loading details…"
    );

    setActionStatus(
      ""
    );

    try {
      const response =
        await sendToPage({
          type:
            "KG_POPUP_INSPECT_LATEST",
        });

      if (
        !response ||
        !response.ok
      ) {
        throw new Error(
          response?.error ||
          "Inspection failed."
        );
      }

      renderTechnicalData(
        response.data
      );
    } catch (error) {
      setActionStatus(
        error.message,
        true
      );
    } finally {
      setTextActionBusy(
        inspectButton,
        false
      );

      await refreshPageStatus();
    }
  }
);

previousButton.addEventListener(
  "click",
  async () => {
    if (
      previousButton.dataset.available !==
      "true"
    ) {
      return;
    }

    setTextActionBusy(
      previousButton,
      true,
      "Checking previous responses…"
    );

    setActionStatus(
      ""
    );

    try {
      const response =
        await sendToPage({
          type:
            "KG_POPUP_CHECK_PREVIOUS",
        });

      if (
        !response ||
        !response.ok
      ) {
        throw new Error(
          response?.error ||
          "Unable to check previous responses."
        );
      }

      const data =
        response.data;

      const parts =
        [];

      if (
        data.verified
      ) {
        parts.push(
          `${data.verified} newly checked`
        );
      }

      if (
        data.restored
      ) {
        parts.push(
          `${data.restored} restored`
        );
      }

      if (
        data.errors
      ) {
        parts.push(
          `${data.errors} failed`
        );
      }

      setActionStatus(
        parts.length
          ? parts.join(
              " · "
            )
          : (
              "No additional responses " +
              "needed checking."
            ),
        data.errors > 0
      );
    } catch (error) {
      setActionStatus(
        error.message,
        true
      );
    } finally {
      setTextActionBusy(
        previousButton,
        false
      );

      await refreshPageStatus();
    }
  }
);

groundDraftButton.addEventListener(
  "click",
  async () => {
    if (
      groundDraftButton.dataset.available !==
      "true"
    ) {
      return;
    }

    setTextActionBusy(
      groundDraftButton,
      true,
      "Grounding draft…"
    );

    setActionStatus(
      ""
    );

    try {
      const response =
        await sendToPage({
          type:
            "KG_POPUP_GROUND_DRAFT",
        });

      if (
        !response ||
        !response.ok
      ) {
        throw new Error(
          response?.error ||
          "Unable to ground draft."
        );
      }

      const count =
        response.data
          ?.evidenceCount ||
        0;

      setActionStatus(
        (
          `Draft grounded with ${count} ` +
          `evidence record${
            count ===
              1
              ? ""
              : "s"
          }.`
        )
      );
    } catch (error) {
      setActionStatus(
        error.message,
        true
      );
    } finally {
      setTextActionBusy(
        groundDraftButton,
        false
      );

      await refreshPageStatus();
    }
  }
);

restoreDraftButton.addEventListener(
  "click",
  async () => {
    setTextActionBusy(
      restoreDraftButton,
      true,
      "Restoring…"
    );

    setActionStatus(
      ""
    );

    try {
      const response =
        await sendToPage({
          type:
            "KG_POPUP_RESTORE_DRAFT",
        });

      if (
        !response ||
        !response.ok
      ) {
        throw new Error(
          response?.error ||
          "Unable to restore draft."
        );
      }

      setActionStatus(
        "Original draft restored."
      );
    } catch (error) {
      setActionStatus(
        error.message,
        true
      );
    } finally {
      setTextActionBusy(
        restoreDraftButton,
        false
      );

      await refreshPageStatus();
    }
  }
);

chrome.tabs.onActivated.addListener(
  () => {
    refreshPageStatus();
  }
);

chrome.tabs.onUpdated.addListener(
  (
    tabId,
    changeInfo
  ) => {
    if (
      changeInfo.url ||
      changeInfo.status
    ) {
      refreshPageStatus();
    }
  }
);

document.addEventListener(
  "DOMContentLoaded",
  async () => {
    const manifest =
      chrome.runtime
        .getManifest();

    versionText.textContent =
      `v${manifest.version}`;

    await Promise.all([
      checkBackend(),
      refreshPageStatus(),
    ]);

    setInterval(
      refreshPageStatus,
      PAGE_REFRESH_MS
    );

    setInterval(
      checkBackend,
      BACKEND_REFRESH_MS
    );
  }
);