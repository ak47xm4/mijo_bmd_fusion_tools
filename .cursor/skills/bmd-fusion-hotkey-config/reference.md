# Fusion hotkey reference

Targets, defaults, APIs. Cookbook: [examples.md](examples.md).

## Architecture (Fusion 8+)

- UI events invoke **Actions** (built-in or custom `Action { ID = ... }`).
- **Hotkeys** blocks map `KEYNAME = "ActionName{ args }"` for one **Target** each.
- **Menus** / toolbars use the same Action IDs (`Menus { Target = ..., After 'Help' { ... } }`).
- Legacy pre-F8 `Fusion.hotkeys` (`Flow = { B = "..." }`) is obsolete; translate to `FlowView` + `AddTool` / `Execute`.

Split `Action` and `Hotkeys` across files under `Config/` — no requirement they share one file (Peter Loveday, WSL).

## Common Hotkeys targets

| Target | Use when |
|--------|----------|
| `GLView` | Viewer frame: zoom, reset, lock, quad, buffers, subview |
| `GLViewer` | Viewer instance: RGBA channels, guides, on-screen controls |
| `GLImageViewer` | 2D: ROI enable, layer page up/down, default layer |
| `GL3DViewer` | 3D: centre selected, fit selected/all |
| `FlowView` | Node editor, bookmarks, AddTool, many scripts |
| `FuFrame` | Comp window: undo, view-on 1–9, save, render, playback on frame |
| `Fusion` | App with no comp: new/open, bins, utilities |
| `TimelineView` / `SplineEditorView` | Editor zoom / key navigation |
| `PlaybackManager` / `GLPreview` | Flipbook / player transport |
| `ConsoleView` | Console-only |

**Not found** in Fusion 20 defaults: `Target = "FuView"` (appears in old forum `User.fu` — verify in Hotkey Manager; prefer `FuFrame` or specific view).

Built-in Flow bookmark keys use `Hotkeys (ordered())` for `SHIFT_CONTROL_1` … `0` — custom Flow keys can conflict.

## Built-in GLView defaults (Fusion 20)

```
CONTROL_1   = Viewer_Reset
CONTROL_2   = Viewer_Reset{ scale = 2.0 }
CONTROL_F   = Viewer_Scale_Abs{ scale=0 }
CONTROL_L   = Viewer_Lock
SHIFT_Q     = Viewer_QuadView
EQUAL / NUMPADPLUS  = Viewer_Scale_Rel{ scale≈√2 }
MINUS / NUMPADMINUS = Viewer_Scale_Rel{ scale≈1/√2 }
COMMA / PERIOD / SLASH = Viewer_Buffer{ index = 0|1|2 }
CONTROL_P   = Viewer_Tools_Disable
QUOTE_LEFT  = Viewer_Unview_All
V           = Viewer_SubView_Enable
```

Menu presets: `Viewer_Scale_Abs{ scale = 0 | 0.25 | 0.5 | 1.0 | 2.0 | 4.0 }`.

## Action binding styles

| Style | Example | Notes |
|-------|---------|--------|
| Built-in | `AddTool{ id = 'Blur' }` | Prefer over raw Lua |
| Execute | `Execute{ cmd = [[ obj:Comp():DisableSelectedTools() ]] }` | `obj` = target context; use `obj:Comp()` not bare `comp` in .fu Actions |
| RunScript | `RunScript{ filename = 'Scripts:/Comp/x.lua' }` | Optional `Name = '...'` for logging |
| Custom | `My_Action{ arg = 1 }` | Requires `Action { ID = "My_Action", Targets = { ... } }` |
| Macro | `AddSetting{ filename = '...' }` | .setting / macro path |
| Legacy script | `@Scripts:Comp/foo.lua` | pre-F8 `Fusion.hotkeys` only |

**Composition** vs **GLView** in `Action.Targets.Execute`: `target` is the object for that target table; `obj` is the UI object receiving the hotkey (e.g. `obj.CurrentViewer` in GLView Actions).

## PathMaps (Windows)

| Alias | Typical path |
|-------|----------------|
| `Config:` | `%AppData%\Blackmagic Design\Fusion\Config` |
| `Profile:` | `%AppData%\Blackmagic Design\Fusion\Profiles\Default` |
| `Scripts:` | User + `ProgramData\...\Fusion\Scripts` |
| Resolve `Config:` | `%AppData%\...\DaVinci Resolve\Support\Fusion\Config` |

Program install `Fusion XX\Config\` also loads (nuke2fusion install docs).

## Hotkey Manager & reload

| Entry | Notes |
|-------|--------|
| Fusion Studio | View → Customize Hotkeys |
| Resolve Fusion page | Often hidden; console `app:CustomizeHotkeys()` or Reactor **Resolve Essentials** → Fusion Hotkey Manager |
| Reload | `fusion.HotkeyManager:LoadHotkeys()` or legacy **Ctrl+F12** (pre-F8 `Fusion.hotkeys`; try after editing `Config` .fu) |
| Discover Action IDs | Hotkey Manager right pane; WSL **Dynamic Hotkeys.lua** |
| List modifiers/keys | `fusion.HotkeyManager:GetKeyNames()` etc. (Scripting Guide) |

Community: GUI often cannot bind everything; durable setups use `Config/*.fu` (WSL *Customizing Hotkeys / Hidden Editor*).

## Reload iteration

- Custom `Action` edits: expect **full restart** per try unless `LoadHotkeys()` works on your build.
- Reactor **RestartFusion** atom (Menus) avoids manual quit/relaunch.

## User.fu vs Config

| Source | Role |
|--------|------|
| `Profile:User.fu` | Hotkey Manager saves here — **ephemeral**; artists report lost bindings |
| `Config:/my_hotkeys.fu` | Version-controlled canonical copy |

Workflow (statixVFX / WSL): bind once in Manager → copy line(s) to `Config/Hotkeys.fu` → restart → never edit only `User.fu`.

## Verify viewer scale (console)

```lua
left = comp:GetPreviewList().Left.View
left:SetScale(1)    -- 100%, keep pan
left:ResetView(1)   -- 100% + recenter (Viewer_Reset family)
left:SetScale(0)    -- Fit
```

## Sources (links)

- [Hotkey Configuration in Fusion 8](https://www.steakunderwater.com/wesuckless/viewtopic.php?t=724) — Peter Loveday, `Config`, `AddTool`, custom `Action`
- [Where does Fusion store default hotkeys?](https://www.steakunderwater.com/wesuckless/viewtopic.php?t=1896) — Targets, `RunScript`, multi-target
- [Menu configuration in Fusion 8.1](https://www.steakunderwater.com/wesuckless/viewtopic.php?t=1246) — Menus + Actions
- [How do I hotkey a Lua script?](https://www.steakunderwater.com/wesuckless/viewtopic.php?t=7885) — nuke2fusion, User.fu warning
- [Customizing Hotkeys / Hidden Editor](https://www.steakunderwater.com/wesuckless/viewtopic.php?t=5238) — `CustomizeHotkeys()`, Resolve
- [BMD Forum: .fu in Resolve Fusion Config](https://forum.blackmagicdesign.com/viewtopic.php?f=21&t=191657) — `Execute` on FlowView
- [VFXPedia Fusion class Fusion](https://www.steakunderwater.com/VFXPedia/96.0.243.189/index5522.html) — `HotkeyManager:LoadHotkeys()`
- [Administrators FAQ — legacy hotkeys](https://www.steakunderwater.com/VFXPedia/96.0.243.189/indexa105.html?title=Administrators_FAQ) — Ctrl+F12, `Flow`/`Frame` tables
- nuke2fusion: GitLab Reactor / GitHub statixVFX/nuke2fusion — full multi-target `.fu`
