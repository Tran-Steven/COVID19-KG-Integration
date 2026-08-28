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
