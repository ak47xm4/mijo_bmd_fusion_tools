# GPU 加速說明 (GPU Acceleration Guide)

## 當前狀況

Fusion 支援 GPU 加速（OpenCL/Metal/CUDA），但 Fuse 腳本中的 `MultiProcessPixels` 主要在 CPU 上執行。

## 啟用 GPU 加速的步驟

### 1. 在 Fusion 中啟用 OpenCL

1. 打開 Fusion → **Preferences** (首選項)
2. 找到 **OpenCL** 設置
3. 設置：
   - **OpenCL Tools**: 設為 **Enable** 或 **Auto**
   - **Device**: 選擇 **GPU** 或 **Auto**

### 2. 當前優化狀態

目前的 `noise_3D_mijo.fuse` 已經進行了以下優化：

- ✅ CPU 多線程優化（`MultiProcessPixels` 自動使用多線程）
- ✅ 減少數學函數調用（sin/cos）
- ✅ 優化 Worley Noise（避免重複 sqrt 計算）
- ✅ 移除調試輸出

## GPU 加速選項

### 選項 1: 使用 Fusion 內建 GPU 加速操作（推薦）

某些 Fusion 內建操作已經 GPU 加速，但對於自定義的 noise 算法，這可能不適用。

### 選項 2: OpenCL 內核實現（進階）

要真正實現 GPU 加速，需要：

1. 編寫 OpenCL 內核（.cl 文件）
2. 在 Fuse 中加載和執行 OpenCL 內核
3. 處理 GPU 內存管理

這需要更複雜的實現，超出了標準 Fuse 的範圍。

### 選項 3: 混合方法

- 使用 Fusion 的 GPU 加速操作處理簡單部分
- CPU 多線程處理複雜的 noise 計算

## 性能建議

1. **確保 Fusion OpenCL 已啟用**：這會讓 Fusion 的內建操作使用 GPU
2. **使用多線程**：當前代碼已經優化，充分利用 CPU 多核心
3. **降低解析度測試**：如果處理高解析度圖像，考慮降低解析度進行預覽
4. **使用代理模式**：Fusion 的代理模式可以加速預覽

## 預期性能

- **CPU 多線程優化後**：比原始版本快 20-50%
- **GPU 加速（如果實現 OpenCL）**：可能快 5-10 倍（取決於 GPU）

## 注意事項

- Fusion 主要使用 **OpenCL**，不是 CUDA
- `MultiProcessPixels` 是 CPU 多線程，不是 GPU
- 要真正使用 GPU，需要編寫 OpenCL/Metal 內核
