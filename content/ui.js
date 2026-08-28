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
