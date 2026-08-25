const API_BASE_URL = "http://localhost:8000";

const routes = {
  GET_KG_CONTEXT: "/kg/context",
  GET_KG_AUGMENTATION: "/kg/augment",
};

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (!message) {
      return false;
    }

    const route = routes[message.type];

    if (!route) {
      return false;
    }

    const text =
      typeof message.text === "string"
        ? message.text.trim()
        : "";

    if (!text) {
      sendResponse({
        ok: false,
        error: "Query text is required",
      });

      return false;
    }

    fetch(
      `${API_BASE_URL}${route}`,
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify({
          text,
        }),
      }
    )
      .then(async (response) => {
        const body = await response
          .json()
          .catch(() => null);

        if (!response.ok) {
          const detail =
            body && body.detail
              ? body.detail
              : `Backend returned ${response.status}`;

          throw new Error(detail);
        }

        return body;
      })
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
);