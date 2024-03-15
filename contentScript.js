// Log to indicate that the script has been loaded
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
    allDivs.forEach(function(div) {
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
    return latestEvenDiv ? latestEvenDiv.textContent.trim() || '' : '';
}

// Handler function to log the latest even turn text
function handleChatUpdate() {
    var latestEvenTurnText = extractLatestEvenTurnText();
    console.log('Latest even turn text:', latestEvenTurnText);
}

// Callback for the MutationObserver to handle mutations
function mutationCallback(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.type === 'childlist') {
      console.log("found subtree")
            handleChatUpdate();
        } else{
      console.log("did not find update")
    }
    });
}

// Create an instance of MutationObserver and pass the callback function
var observer = new MutationObserver(mutationCallback);

// Configuration for the observer (which mutations to observe)
var config = { childList: true, subtree: true };

// Select the node that will be observed for mutations
const targetNode = document.querySelector('[role="presentation"]');
 

// Wait for the DOM to be fully loaded
window.addEventListener('DOMContentLoaded', function() {
    // Check if the target node is available in the DOM
    if (targetNode) {
        // Start observing the target node for configured mutations
    console.log("Found node");
        observer.observe(targetNode, config);
    } else {
        // Output an error if the target node is not found in the DOM
        console.error('Chat container not found');
    }
});

