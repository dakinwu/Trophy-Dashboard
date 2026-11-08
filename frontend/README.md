# Trophy Hunter Dashboard — Frontend

Vite + React + TypeScript 前端，使用 Tailwind CSS v4、HeroUI v3、Recharts 與 Motion。完整安裝、資料來源與快取說明請見 [專案 README](../README.md)。

## 開發

需要 Node.js 20.19+（20.x）或 22.12+，在此目錄執行：

```powershell
npm ci
npm run dev
```

前端固定在 `http://localhost:5174`；`/api` 由開發伺服器轉送至 `http://localhost:8001`。後端請依根目錄說明另行啟動。連接埠占用時會直接失敗，不會自動改用其他連接埠。

## 驗證

```powershell
npm run lint
npm run build
```

`build` 包含 TypeScript 型別檢查；目前沒有獨立 `test` 或 `typecheck` script。

## 主要目錄

- `src/pages/`：各功能頁面。
- `src/components/`：共用元件、圖表與 Overview Hero。
- `src/lib/`：既有 API client、查詢與資料轉換。
- `src/index.css`：主題與全域樣式。

介面使用繁體中文，遊戲／獎盃名稱保留原文。新增動態效果時需支援減少動畫偏好，且不應造成重複資料請求。

不要在 `VITE_*` 變數或前端程式放入 NPSSO、Gemini key 或其他機密。此專案沒有多使用者權限控管，不可直接當成公開網站部署；詳見 [安全說明](../SECURITY.md)。
