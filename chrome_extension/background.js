// Service worker — 최소 구현 (MV3 필수)
// 향후: 알람 배지 업데이트, push notification 처리

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ serverUrl: "https://sagepontus-284182376290.asia-northeast1.run.app" });
});
