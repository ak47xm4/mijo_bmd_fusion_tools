--[[
  force_re_render_mijo
  ---------------------------------------------------------------------------
  貼進 Fusion 工具的 FrameRenderScript 欄位。放著即可讓該工具「每一幀」都被
  強制重新渲染,用來繞過 Fusion 的 stale cache。

  原理:
    Fusion 只有在 FrameRenderScript 的「內容」與上一次不同時,才會把工具標記為
    dirty 並讓快取失效。因此這段腳本用 quine 的方式,每一幀都把自己重寫一次,並在
    結尾附上一個唯一時間戳(os.clock()),確保每一幀寫回的內容都必定不同 → 快取必定
    失效 → 持續強制重算。

  與舊版差異:
    舊版每次寫回的內容固定不變,只有第一次會讓快取失效;之後每幀內容相同,便不再
    持續強制重算。此版每幀內容都帶新的時間戳,才是真正的「持續強制更新」。
]]

local tmpl = "local tmpl = %q self.FrameRenderScript = string.format(tmpl, tmpl, os.clock()) print('[mijo] force re-render') -- %s"
self.FrameRenderScript = string.format(tmpl, tmpl, os.clock())
