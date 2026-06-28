// Service worker — toolbar 클릭 시 content script에 toggle 메시지 전송

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ serverUrl: "https://pt.sagepontus.com" });
});

chrome.action.onClicked.addListener((tab) => {
  chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_PANEL" }, () => {
    void chrome.runtime.lastError; // chrome:// 등 접근 불가 탭에서 에러 억제
  });
});
