console.log("Script loaded");
let currentTurn = 0;
// Function to check if the turn is even based on the 'data-testid' attribute
function isEvenTurn(dataTestId) {
  let turnNumber = parseInt(dataTestId.replace("conversation-turn-", ""), 10);
  return turnNumber % 2 === 0;
}

function findLargestEvenDiv(allDivs) {
  let largestEvenDiv = null;
  let maxEvenId = 0;
  allDivs.forEach(function (div) {
    let dataTestId = div.getAttribute("data-testid");
    if (dataTestId && isEvenTurn(dataTestId)) {
      let turnNumber = parseInt(
        dataTestId.replace("conversation-turn-", ""),
        10
      );
      if (turnNumber > maxEvenId) {
        largestEvenDiv = div;
        maxEvenId = turnNumber;
      }
    }
  });
  return largestEvenDiv;
}

function extractLatestEvenTurnText() {
  let allDivs = document.querySelectorAll("div[data-testid]");
  let latestEvenDiv = findLargestEvenDiv(allDivs);
  if (latestEvenDiv) {
    let Query = latestEvenDiv.textContent.trim().replace(/^You/, "").trim();
    return Query;
  }
  return "";
}
function handleChatUpdate() {
  let latestEvenTurnText = extractLatestEvenTurnText();
  if (
    currentTurn !==
    findLargestEvenDiv(document.querySelectorAll("div[data-testid]"))
  ) {
    async function fetchContext() {
      //todo
      const response = await fetch("localhost:7474");
      console.log(response);
    }
  }
  console.log("Latest Query:", latestEvenTurnText);
}
function mutationCallback(mutations) {
  mutations.forEach(function (mutation) {
    console.log("Mutation observed:", mutation);
    handleChatUpdate();
  });
}

let observer = new MutationObserver(mutationCallback);
let config = { childList: true, subtree: true };

let targetNodeSelector = '[role="presentation"]';
let observationAttempts = 0;
let observationInterval = setInterval(function () {
  let targetNode = document.querySelector(targetNodeSelector);
  if (targetNode) {
    console.log("Found target node, starting observation.");
    observer.observe(targetNode, config);
    clearInterval(observationInterval);
  } else if (observationAttempts++ > 20) {
    // Stop trying after 20 attempts
    console.error("Failed to find the target node after multiple attempts.");
    clearInterval(observationInterval);
  } else {
    console.log("Target node not found, trying again...");
  }
}, 1000); // Check Target Node Every Second
