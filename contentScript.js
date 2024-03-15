console.log('Script loaded');

// Function to check if the turn is even based on the 'data-testid' attribute
function isEvenTurn(dataTestId) {
  var turnNumber = parseInt(dataTestId.replace('conversation-turn-', ''), 10);
  return turnNumber % 2 === 0;
}

// Function to find the largest even-numbered data-testid
function findLargestEvenDiv(allDivs) {
  var largestEvenDiv = null;
  var maxEvenId = 0;
  allDivs.forEach(function (div) {
    var dataTestId = div.getAttribute('data-testid');
    if (dataTestId && isEvenTurn(dataTestId)) {
      var turnNumber = parseInt(dataTestId.replace('conversation-turn-', ''), 10);
      if (turnNumber > maxEvenId) {
        largestEvenDiv = div;
        maxEvenId = turnNumber;
      }
    }
  });
  return largestEvenDiv;
}

// Function to extract text from the latest even-numbered turn
function extractLatestEvenTurnText() {
  var allDivs = document.querySelectorAll('div[data-testid]');
  var latestEvenDiv = findLargestEvenDiv(allDivs);
  return latestEvenDiv && latestEvenDiv.textContent ? latestEvenDiv.textContent.trim() : '';
}

var handleChatUpdate = function () {
  var latestEvenTurnText = extractLatestEvenTurnText();
  console.log('Latest even turn text:', latestEvenTurnText);
};

// MutationObserver callback to handle mutations
var mutationCallback = function (mutations) {
  mutations.forEach(function (mutation) {
    if (mutation.type === 'childList') {
      handleChatUpdate();
    }
  });
};

// MutationObserver instance to observe for changes
var observer = new MutationObserver(mutationCallback);

// Configuration for the observer (which mutations to observe)
var config = { childList: true, subtree: true };

// Select the node that will be observed for mutations
var targetNode = document.querySelector('div[role="presentation"][tabindex="0"].flex.h-full.flex-col');

// Start observing the target node for configured mutations
if (targetNode) {
  observer.observe(targetNode, config);
} else {
  console.error('Chat container not found');
}

