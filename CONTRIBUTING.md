# 開發與檢視指南

安裝、啟動與資料來源說明請先閱讀 [README.md](README.md)，安全限制請見 [SECURITY.md](SECURITY.md)。

## 程式碼地圖

- `backend/app/api/`：HTTP 與 SSE 端點。
- `backend/app/services/`：PSN、PSNProfiles、名稱解析、推薦與圖片處理。
- `backend/app/models.py`：後端資料模型。
- `backend/tests/`：測試與匿名化 HTML 範例。
- `frontend/src/pages/`：主要頁面。
- `frontend/src/components/`：共用介面、圖表與 Overview Hero。
- `frontend/src/lib/`：API client、查詢設定、型別與純資料轉換。
- `frontend/src/index.css`：Trophy Gold 主題與共用樣式。

## 修改原則

- 不把帳號憑證放入前端、原始碼、測試或提交訊息。
- 不混用 PSN 與 PSNProfiles 的稀有度和排名；缺少資料時保留 unavailable 狀態。
- 保持請求有上限、按需載入與快取行為；不要在測試中消耗真實 API 額度或啟動全庫爬取。
- 變更資料結構時同步更新後端模型、前端型別與測試。
- UI 採繁體中文；遊戲與獎盃名稱保留來源文字。尊重鍵盤操作與 reduced motion（減少動畫的系統偏好）。
- 保留原始專案署名與 MIT 授權。

## 本機驗證

分別在對應目錄執行：

```powershell
cd frontend
npm run lint
npm run build
```

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

前端 `build` 會執行 TypeScript 型別檢查。目前沒有獨立的前端 `test` 或 `typecheck` script。後端測試應使用本地範例、臨時目錄與模擬服務；通過測試不等於即時確認所有外站資料。

介面變更另請檢查窄螢幕、長 PSN ID、空資料、載入／失敗狀態、鍵盤焦點與減少動畫模式。

## 提交前

```powershell
git status --short
git diff --check
git diff --cached
git remote -v
```

確認提交只有必要程式碼與公開文件，不含快取、日誌、憑證、個人筆記或產生檔。依需求更新 README 或 Roadmap；PR（合併請求）應說明修改原因、行為差異、驗證結果及尚未驗證的限制。

請明確選擇自己有意提交的倉庫，不要因為存在 `upstream` 就自動向原始專案開 PR。
