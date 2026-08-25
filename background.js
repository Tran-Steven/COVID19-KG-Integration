const API_BASE_URL =
  "http://localhost:8000";

const routes = {
  GET_KG_CONTEXT: {
    path: "/kg/context",
    type: "text",
  },
  GET_KG_AUGMENTATION: {
    path: "/kg/augment",
    type: "text",
  },
  VERIFY_KG_RESPONSE: {
    path: "/kg/verify-response",
    type: "verification",
  },
};

function buildTextBody(message) {
  const text =
    typeof message.text === "string"
      ? message.text.trim()
      : "";

  if (!text) {
    throw new Error(
      "Query text is required"
    );
  }

  return {
    text,
  };
}

function buildVerificationBody(
  message
) {
  const question =
    typeof message.question ===
    "string"
      ? message.question.trim()
      : "";

  const response =
    typeof message.response ===
    "string"
      ? message.response.trim()
      : "";

  if (!question) {
    throw new Error(
      "Question text is required"
    );
  }

  if (!response) {
    throw new Error(
      "Response text is required"
    );
  }

  return {
    question,
    response,
  };
}

function buildBody(
  route,
  message
) {
  if (
    route.type ===
    "verification"
  ) {
    return buildVerificationBody(
      message
    );
  }

  return buildTextBody(
    message
  );
}

chrome.runtime.onMessage.addListener(
  (
    message,
    sender,
    sendResponse
  ) => {
    if (!message) {
      return false;
    }

    const route =
      routes[message.type];

    if (!route) {
      return false;
    }

    let body;

    try {
      body = buildBody(
        route,
        message
      );
    } catch (error) {
      sendResponse({
        ok: false,
        error: error.message,
      });

      return false;
    }

    fetch(
      `${API_BASE_URL}${route.path}`,
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify(
          body
        ),
      }
    )
      .then(
        async (response) => {
          const responseBody =
            await response
              .json()
              .catch(
                () => null
              );

          if (!response.ok) {
            const detail =
              responseBody &&
              responseBody.detail
                ? responseBody
                    .detail
                : (
                    `Backend returned ` +
                    `${response.status}`
                  );

            throw new Error(
              detail
            );
          }

          return responseBody;
        }
      )
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