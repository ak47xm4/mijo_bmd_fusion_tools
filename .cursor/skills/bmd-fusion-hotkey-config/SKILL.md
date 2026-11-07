---
name: bmd-fusion-hotkey-config
description: >-
  Author and debug Blackmagic Fusion / DaVinci Resolve Fusion hotkeys in Config
  .fu files (Targets, Actions, RunScript, GLView zoom). Use for hotkey.fu,
  Customize Hotkeys, User.fu vs Config, shortcuts not working, nuke2fusion-style
  bindings, or FlowView/GLView/FuFrame targets.
---

# BMD Fusion hotkey config (.fu)

Fusion 8+ routes UI through **Actions**. User bindings live in `UserPaths:Config/*.fu` (and `Profile:User.fu` from the Hotkey Manager). Pre-F8 `Fusion.hotkeys` section names (`Flow`, `Frame`) are obsolete.

## Where files load

| Location                      | Windows (standalone Fusion)                            | Loaded?                         |
| ----------------------------- | ------------------------------------------------------ | ------------------------------- |
| **Config** (canonical)        | `%AppData%\Blackmagic Design\Fusion\Config\`           | Yes — all `*.fu` recursive      |
| Install-wide                  | `C:\Program Files\Blackmagic Design\Fusion XX\Config\` | Yes (documented by nuke2fusion) |
| **Resolve Fusion page**       | `%AppData%\...\DaVinci Resolve\Support\Fusion\Config\` | Yes — separate from standalone  |
| **User.fu**                   | `Profiles\Default\User.fu`                             | Yes — Hotkey Manager output     |
| **Profiles/Default/other.fu** | e.g. `hotkey.fu`                                       | **No** unless under `Config:`   |

This repo: source `Config/hotkey.fu` → `copy_test_mijo.cmd` → `FUSION_CONFIG_FOLDER`.

After edits: **restart Fusion** (safest). Try `fusion.HotkeyManager:LoadHotkeys()` or Ctrl+F12 (legacy docs) before restarting. Custom `Action` bodies often need restart + Reactor **RestartFusion** speeds iteration (WSL).

## Recommended workflows (community)

1. **Prototype** in View → Customize Hotkeys (Resolve: `app:CustomizeHotkeys()` or Resolve Essentials script).
2. **Persist** by copying generated lines from `User.fu` into `Config/my_hotkeys.fu` — **do not** rely on `User.fu` alone (WSL: bindings can disappear).
3. **Hand-author** using Action IDs from the Hotkey Manager right pane or [examples.md](examples.md).
4. **Split files** — `Actions` and `Hotkeys` may live in different `.fu` files under `Config/`.

## File layout patterns

### A — One Target per chunk (simple, IDE-friendly)

```lua
{
	Hotkeys {
		Target = "GLView",
		SHIFT_CONTROL_1 = "Viewer_Scale_Abs{ scale = 1 }",
	},
}

{
	Hotkeys {
		Target = "Fusion",
		F3 = "RunScript{ Name = 'toggle_nodes', filename = 'Scripts:/Comp/toggle_nodes.lua' }",
	},
}
```

**No comma** between top-level `{ ... }` chunks (`},` + `{` → Lua `Unexpected`).

### B — nuke2fusion chunk (Action + several Hotkeys siblings)

One outer `{ }` with `Action { }` then multiple `Hotkeys { }` blocks — valid **Fusion config syntax** (see [examples.md](examples.md)). Used by Reactor nuke2fusion, Toggle Inspector .fu, etc.

Do **not** assume two `Hotkeys` keys inside a plain Lua table without Fusion’s loader — pattern B is sibling blocks, not `Hotkeys =` twice.

### Binding styles

| Need             | Pattern                                                                                      |
| ---------------- | -------------------------------------------------------------------------------------------- |
| Add tool         | `B = "AddTool{ id = 'Blur' }"`                                                               |
| Disable selected | `D = "Execute{ cmd = 'obj:Comp():DisableSelectedTools()' }"`                                 |
| Script           | `F3 = "RunScript{ filename = 'Scripts:/Comp/foo.lua' }"`                                     |
| MapPath fix      | `Execute{ cmd = [[ obj:RunScript(obj:MapPath('Scripts:/Comp/foo.lua')) ]] }` (Peter Loveday) |
| Macro            | `AddSetting{ filename = 'Macros:/x.setting' }`                                               |
| Custom logic     | `Action { ID = "My_X", Targets = { GLView = { Execute = [[ ... ]] } } }` then `Q = "My_X"`   |

In `.fu` Actions use `obj` / `target`, not console globals `comp` — e.g. `obj:Comp():ActiveTool`.

## Syntax cheat sheet

- `Hotkeys {` call-style (BMD sugar), not required to be `Hotkeys = {`.
- Modifiers: `SHIFT_` → `CONTROL_` → `ALT_` (e.g. `SHIFT_CONTROL_1`).
- Special keys: `OEM_PERIOD`, `QUOTE_LEFT`, `['1']`, `NUMPADPLUS` — see [examples.md](examples.md).
- `ShowKeys`: `fu:SetPrefs("Global.Tweaks.ShowKeys", true)` (disable with `false`).
- Paths: prefer `Scripts:/` / `Config:/`; Windows absolutes need `\\\\` in quoted strings.
- `loadfile()` in `fuscript` on whole `.fu` often fails — Fusion uses a custom loader; test in-app.

## Focus & conflicts

Gray border = active UI region. `GLView` keys need viewer focus (click 2D viewer).

Same combo, different targets: repeat binding in separate `Hotkeys` blocks (`FlowView` vs `GLView`).

| Combo (default)   | FlowView   | GLView                    |
| ----------------- | ---------- | ------------------------- |
| `SHIFT_CONTROL_1` | Bookmark 1 | Your custom zoom if bound |

## 2D viewer zoom

| Intent          | Action                          | Default       |
| --------------- | ------------------------------- | ------------- |
| Fit             | `Viewer_Scale_Abs{ scale = 0 }` | Ctrl+F        |
| 100% + recenter | `Viewer_Reset`                  | Ctrl+1        |
| 100%, keep pan  | `Viewer_Scale_Abs{ scale = 1 }` | bind yourself |

Target: **`GLView`** for scale/reset. `GLImageViewer` = ROI/layers; `GLViewer` = channels/guides.

## Resolve vs Fusion Studio

- Deploy to the profile actually running (Resolve `Support\Fusion\Config` vs `%AppData%\...\Fusion\Config`).
- Hotkey Manager is easy to miss in Resolve; `.fu` in `Config` is the durable approach (forum + WSL consensus).

## Debug checklist

1. File under **`Config:`** (not only repo / wrong profile).
2. Restart or `LoadHotkeys()`.
3. Correct **Target** + UI focus.
4. Conflict — remap in Hotkey Manager or temporarily use unused key.
5. `ShowKeys` for internal key token names.
6. Compare with builtins in [reference.md](reference.md).

## Repo

- `Config/hotkey.fu` — source
- `copy_test_mijo.cmd` — deploy to live Config

Deep tables, links, defaults: [reference.md](reference.md). Copy-paste recipes: [examples.md](examples.md).
