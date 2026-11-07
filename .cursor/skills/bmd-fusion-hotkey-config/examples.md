# Hotkey .fu examples (community patterns)

Portable `Scripts:` paths, `nuke2fusion`-style layout, and Peter Loveday / BMD forum snippets. Restart Fusion after install unless you successfully reload hotkeys (see SKILL.md).

## 1) FlowView — AddTool + RunScript (Andrew Hazelden style)

```lua
{
	Hotkeys
	{
		Target = "FlowView",

		B = "AddTool{ id = 'Blur' }",
		L = "AddTool{ id = 'Loader' }",
		S = "AddTool{ id = 'Saver' }",
		TAB = "RunScript{ filename = 'Scripts:/Comp/PanoView.lua' }",
		D = "Execute{ cmd = 'obj:Comp():DisableSelectedTools()' }",
	}
}
```

Paths: prefer `Scripts:/Comp/...` over absolute `C:\...` or macOS Application Support paths.

## 2) GLView — Fit (F) + custom Action (nuke2fusion)

Custom Action lives in the **same** outer chunk as multiple `Hotkeys` blocks (Fusion config syntax, not plain Lua tables):

```lua
{
	Action
	{
		ID = "My_ShowHideControls",
		Category = "My Stuff",
		ShortName = "SHC",
		Args =
		{
			{ "show", Type = "boolean", Required = false },
		},
		Targets =
		{
			GLView =
			{
				Execute =
				[[
					local viewer = obj.CurrentViewer
					if args.show == nil then
						args.show = not viewer:AreControlsShown()
					end
					viewer:ShowControls(args.show)
					viewer:Redraw()
				]],
			},
		},
	},

	Hotkeys
	{
		Target = "FlowView",
		B = "AddTool{ id = 'Blur' }",
	},

	Hotkeys
	{
		Target = "GLView",
		F = "Viewer_Scale_Abs{ scale=0 }",
		Q = "My_ShowHideControls",
	},

	Hotkeys
	{
		Target = "FuFrame",
		J = "Playback_Mode{ play = true, reverse = true }",
		K = "Playback_Mode{ play = false }",
		L = "Playback_Mode{ play = true }",
	},
}
```

Source: Reactor **nuke2fusion** (`com.statixVFX.nuke2fusion` / GitHub statixVFX/nuke2fusion).

## 3) Toggle Inspector (Andrew Hazelden .fu pattern)

```lua
{
	Action
	{
		ID = "ToggleInspector",
		Category = "View Control",
		Name = "Toggle Inspector",
		Targets =
		{
			Composition =
			{
				Execute = _Lua [=[
					target:DoAction("Fusion_View_Show", {view = "Inspector"})
				]=],
			},
		},
	},
	Hotkeys
	{
		Target = "FlowView",
		SHIFT_ESCAPE = "ToggleInspector{}",
	},
}
```

Works in Fusion Studio and Resolve Fusion page (per author notes).

## 4) RunScript when PathMap is required (Peter Loveday workaround)

If `RunScript{ filename = 'Scripts:/...' }` does not resolve on your build:

```lua
SHIFT_TAB = "Execute{ cmd = [[ obj:RunScript(obj:MapPath('Scripts:/Comp/PanoView.lua')) ]] }",
```

## 5) Drop a macro / .setting on Flow

```lua
M = "AddSetting{ filename = 'Macros:/MyMacro.setting' }",
```

Use PathMaps for `filename` where possible.

## 6) Multi-target same combo (Eugene / ShadowMaker pattern)

Duplicate the binding in separate `Hotkeys` blocks — one per Target:

```lua
{
	Hotkeys {
		Target = "FlowView",
		SHIFT_CONTROL_ALT_1 = "RunScript{ filename = 'Scripts:/Comp/MultiFrameMaskNone.lua' }",
	},
}

{
	Hotkeys {
		Target = "GLView",
		SHIFT_CONTROL_ALT_1 = "RunScript{ filename = 'Scripts:/Comp/MultiFrameMaskNone.lua' }",
	},
}
```

## 7) Special key names

| Key | Name in .fu |
|-----|-------------|
| `.` (period) | `OEM_PERIOD` |
| `` ` `` | `QUOTE_LEFT` |
| `1`–`9` view-on | `['1']` … `['9']` or `NUMPAD1` |
| Numpad `+` / `-` | `NUMPADPLUS` / `NUMPADMINUS` |

Discover unknown keys: `fu:SetPrefs("Global.Tweaks.ShowKeys", true)` in Console (Fusion 8.1+; see WSL thread p724).

## 8) Install locations (pick one per deployment)

| Scope | Windows |
|-------|---------|
| Per-user (typical) | `%AppData%\Blackmagic Design\Fusion\Config\` |
| Resolve Fusion page | `%AppData%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Config\` |
| All users on machine | `C:\Program Files\Blackmagic Design\Fusion 20\Config\` (nuke2fusion documents this) |

Also loaded: `Profile:User.fu` from Hotkey Manager — treat as **generated**, copy lines into `Config/my_hotkeys.fu`.
