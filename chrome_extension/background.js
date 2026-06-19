// Service worker — toolbar 클릭 시 content script에 toggle 메시지 전송

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ serverUrl: "https://sagepontus-284182376290.us-east4.run.app" });
});

chrome.action.onClicked.addListener((tab) => {
  chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_PANEL" }, () => {
    if (chrome.runtime.lastError) {
      // 탭에 content script가 아직 없으면 주입 후 재시도
      chrome.scripting.executeScript(
        { target: { tabId: tab.id }, files: ["content.js"] },
        () => chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_PANEL" })
      );
    }
  });
});
