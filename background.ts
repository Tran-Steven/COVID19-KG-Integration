chrome.tabs.onUpdated.addListener((tabId, tab) => {
  if (tab.url && tab.url.includes("https://chat.openai.com")) {
    const queryParameters = new URLSearchParams(tab.url.split("?")[1]);
    const urlParameters = new URLSearchParams(queryParameters);
    
  }
});
