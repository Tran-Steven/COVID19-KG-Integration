
function isEvenTurn(dataTestId) {
  const turnNumber: number = parseInt(dataTestId.replace('conversation-turn-', ''), 10);
  return turnNumber % 2 === 0;
}

// Function to find the largest even-numbered data-testid
function findLargestEvenDiv(allDivs){
  let largestEvenDiv: = null;
  let maxEvenId = 0;
  allDivs.forEach(div => {
    const dataTestId = div.getAttribute('data-testid');
    if (dataTestId && isEvenTurn(dataTestId)) {
      const turnNumber = parseInt(dataTestId.replace('conversation-turn-', ''), 10);
      if (turnNumber > maxEvenId) {
        largestEvenDiv = div;
        maxEvenId = turnNumber;
      }
    }
  });
  return largestEvenDiv;
}

// Function to extract text from the latest even-numbered turn
function extractLatestEvenTurnText(){
  const allDivs = document.querySelectorAll('div[data-testid]');
  const latestEvenDiv= findLargestEvenDiv(allDivs);
  return latestEvenDiv ? latestEvenDiv.textContent?.trim() || '' : '';
}

const handleChatUpdate = () => {
  const latestEvenTurnText= extractLatestEvenTurnText();
  console.log('Latest even turn text:', latestEvenTurnText);
};

// MutationObserver callback to handle mutations
const mutationCallback = (mutations) => {
  for (const mutation of mutations) {
    if (mutation.type === 'childList') {
      handleChatUpdate();
    }
  }
};

// MutationObserver instance to observe for changes
const observer = new MutationObserver(mutationCallback);

// Configuration for the observer (which mutations to observe)
const config= { childList: true, subtree: true };

// Select the node that will be observed for mutations
const targetNode = document.querySelector('div[role="presentation"][tabindex="0"].flex.h-full.flex-col');

// Start observing the target node for configured mutations
if (targetNode) {
  observer.observe(targetNode, config);
} else {
  console.error('Chat container not found');
}

