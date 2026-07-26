# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal collection of tools for **Blackmagic Fusion / DaVinci Resolve** (targeting Fusion ~18–20.2). There is no build system, test suite, or package manager. Everything here is either a Fusion plugin (`.fuse`) or a script executed *inside* Fusion's Python/Lua console. Code "runs" only when loaded by Fusion — you cannot execute it standalone.

Two artifact types:
- **Fuse plugins** (`fuse/*.fuse`) — self-contained Fusion tools written in **Lua** (VS Code maps `*.fuse` → lua via `.vscode/settings.json`, which is gitignored).
- **Scripts** (`Script/**`, `davinci/*.lua`) — Python or Lua run from Fusion's scripting console; they rely on Fusion's injected globals (`comp`, `fusion`, `tool`, `self`) with no imports.

## Commands

There is nothing to build and no tests. The only checks available outside Fusion:

```bash
# Syntax-check the Python scripts (they never execute at import time on their own —
# py_compile only compiles, so the missing `comp`/`fusion` globals don't matter).
py -m py_compile Script/Comp/mijo_WIP/*/*.py Script/fusion_daily_tools/*.py Script/DCC_3D_intergrate/*.py
# note: `python` is not on PATH here; use the `py` launcher. Delete the __pycache__ dirs afterwards
# with `rm -rf`/`Remove-Item` — NOT `git clean -X`, which would also wipe the gitignored PDFs and
# `copy_test_mijo.cmd` (see "Local reference material" below).
```

No Lua interpreter is installed, so `.fuse` files can only be validated by loading them in Fusion.

**Deploy / test loop:** copy the artifact into a live Fusion install and reload. `copy_test_mijo.cmd` (Windows, **gitignored**, machine-specific Afanasy render-farm paths) does this:

```
copy /y "fuse\noise_3D_mijo_openCL.fuse" "F:\Z_Afanasy_farm\bmd_fusion\Fuses\"
```

Uncomment the relevant `copy` line for whichever artifact you changed (it also has commented lines for the CPU fuse and for scripts, which go to `...\bmd_fusion\Script\Comp\...`). After copying, reload the tool in Fusion — re-add the node, or restart Fusion — to pick up the new source. Fuse edits are **not** hot-reloaded into existing nodes. One commented line points at `fuse\fill_pixels_mijo.fuse`, which does not exist in the repo — it is a leftover, not a missing file.

### Local reference material (all gitignored — present on this machine, absent from a fresh clone)

- `fuse/Fusion 18 Fuse Manual.pdf` — the authoritative Fuse API reference (`AddInput` control types, `Image`/`Pixel` methods, `Process`/request lifecycle). Read this before guessing at a fuse API.
- `Script/Fusion8_Scripting_Guide.pdf` — the scripting-side counterpart (comp/tool/attribute names).
- `fuse_example/Grade.fuse` — a stock Blackmagic fuse kept purely as a worked example of idiomatic fuse structure.

Because these are in `.gitignore`, they will not appear in CI, on another machine, or in a clean checkout — never make code depend on them, and don't be surprised when `git status` ignores them.

## Fuse plugin architecture

A `.fuse` is a Lua module Fusion loads to register a tool. Lifecycle callbacks (all optional except the first two):

- `FuRegisterClass(name, CT_Tool, {...})` — registers the class. `REGS_Category = "mijo"` groups these tools under the "mijo" menu; `REGS_Name` is the display name.
- `Create()` — declares inputs/outputs via `self:AddInput` / `self:AddOutput`. Input controls (`SliderControl`, `ComboControl`, etc.) become the tool's UI. Names/IDs here are read back in `Process`.
- `Process(req)` — the render function. Reads control values with `Input:GetValue(req).Value`, works with `Image{}` objects, and writes pixels. `req.Time` drives animation (both noise fuses only read `req.Time` when `Seethe Rate > 0`, so a static setup stays cacheable).
- `OnAddToFlow()` / `OnRemoveFromFlow()` — used by the OpenCL variant to compile the GPU program and release cached GPU resources.

### `MultiProcessPixels` and the userData rule (applies to both noise fuses)

`out:MultiProcessPixels(nil, userData, left, bottom, w, h, srcImage, processPixel)` runs `processPixel(x, y, p)` in Fusion's **worker context**, where module-scope functions and `Process` locals are *not* visible — only the keys of the `userData` table, injected as globals. Consequences:

- Every helper the pixel function needs is **re-inlined inside it** (`localHash3`, `lPerlin`, …). The module-scope copies in `noise_3D_mijo.fuse` (`hash`, `perlinNoise3D`, `getNoiseValue`, …) are effectively **dead code** kept for reference — `Process` never calls them.
- Inside `processPixel`, controls are referenced by their **userData key** (`Scale`, `NoiseType`, `CurrentTime`), not by the `Process` local (`scale`, `noiseType`, `currentTime`).
- **Adding a control means four edits:** `AddInput` in `Create()`, a `GetValue` in `Process()`, an entry in the `userData` table, and its use inside `processPixel`. Miss the userData entry and the value silently reads as `nil` in the pixel loop.

Both fuses build a float `img_temp` copy of the input (`IMG_Depth_Float`, `IMG_CopyChannels`) before processing, and force float output — the input's R/G/B are read as XYZ *positions*, so 8/16-bit input would clip them.

### The Noise 3D tools (two files, three code paths)

`noise_3D_mijo.fuse` and `noise_3D_mijo_openCL.fuse` are the same idea — read the input image's R/G/B as an XYZ position and generate noise (Perlin / Simplex / Value / Worley / FBM) from it — but they register as **two separate tools that coexist** in Fusion:

| File | Class | Display name |
|---|---|---|
| `noise_3D_mijo.fuse` | `Noise3D_mijo` | Noise 3D mijo |
| `noise_3D_mijo_openCL.fuse` | `Noise3D_mijo_CL` | Noise 3D mijo CL |

Shared controls: Noise Type, Output Mode, Scale + Scale X/Y/Z, Octaves / Lacunarity / Persistence, Offset X/Y/Z, Seethe, Seethe Rate, Min/Max Value. The **CL variant adds two controls the CPU one does not have**: `Process Mode` (Auto (GPU→CPU) / GPU (OpenCL) / CPU) and `Bounding Box` (None / Domain / Frame). When you change a *shared* control or its behaviour, mirror it in both files.

There are three distinct pixel paths, and **they do not produce identical noise** — this is the most important thing to know before "fixing" a mismatch:

1. `noise_3D_mijo.fuse` CPU — `sin`-based fract hash + **trig** gradient (`cos/sin` of an angle).
2. `noise_3D_mijo_openCL.fuse` CPU fallback — `sin`-based fract hash + **trig-free** Perlin bit-selection gradient.
3. `noise_3D_mijo_openCL.fuse` GPU kernel — **integer** hash (`ihash`, pure ALU) + the same bit-selection gradient.

Paths 2 and 3 share structure and gradient but use different hashes, so flipping `Process Mode` between GPU and CPU **changes the pattern**, not just the speed. Treat "GPU and CPU look different" as known behaviour; only report it as a bug if the *structure* (scale, octaves, range remap) diverges.

### OpenCL variant specifics

- The kernel is the `clsource` string at the top of the file; `OnAddToFlow` compiles it with `OCLManager():BuildCachedProgram("Noise3D_mijo_CL", path, clsource)` (path comes from `debug.getinfo(1).source`). If `prog` is nil the tool silently uses the CPU path.
- **Argument packing:** 17 scalars are packed into 8 kernel args (`int2 imgsize`, `int4 intParams`, four `float4`s) to cut `SetArg` calls. The kernel signature, its unpack block, and the `prog:SetArg*` indices in `Process` must be edited **in lockstep**; there is no name-based binding to catch a mismatch.
- **Cached GPU state** lives in module-scope globals: `_cached_kernel` (created once, `SetWorkgroupSize(16,16)`), and `_cached_srccl` / `_cached_src_img` (the uploaded source image, re-uploaded only when the input `Image` object identity changes — this is what keeps slider drags from re-sending ~33 MB over PCIe each frame). `OnRemoveFromFlow` must `Release()` `_cached_srccl` and clear all of them; anything new you cache belongs in both places.
- **DoD/RoI:** the GPU path processes the **full image** (`img.Width/Height`) and honours `Bounding Box` only by choosing the output `Image`'s DataWindow (Frame = full frame, None/Domain = `IMG_Like` the input). The CPU fallback additionally intersects `req:GetInputDoD()` / `req:GetRoI()`. So GPU and CPU can differ in the *region* rendered as well as the pattern.

`fuse/GPU_ACCELERATION_README.md` (Traditional Chinese) covers enabling OpenCL in Fusion Preferences and the CPU-vs-GPU reality of fuses. Note it **predates the OpenCL variant** and still says a real OpenCL kernel is out of scope for a fuse — that part is now obsolete.

## Scripts

Fusion console scripts assume globals are already present. Common idioms seen throughout:
- Wrap mutations in `comp.StartUndo('label')` … `comp.EndUndo(True)`, and bracket bulk edits with `comp.Lock()` / `comp.Unlock()` (release both in a `finally` / before any `raise`).
- `comp.GetToolList(selectedOnly, "Loader")`, `tool.GetAttrs("TOOLST_Clip_Name")` / `tool.SetAttrs({...})`, `comp.MapPath(path)` (always map before touching the filesystem — comps use Fusion PathMaps), `fusion.TIME_UNDEFINED`, `comp.AskUser(title, {...})`.

### version_switch_mijo (`Script/Comp/mijo_WIP/version_switch_mijo/`)

`B_mj_version_Down.py`, `C_mj_version_up.py`, `D_mj_version_latest.py` retarget Loader clip paths containing a `vNNN` version folder to a different **existing** version on disk, then reload the footage and fix the frame range.

The three files are **byte-identical except for the single `MODE = "down" | "up" | "latest"` line near the top** (C and D also carry a UTF-8 BOM). Any change below that line must be copied verbatim into the other two — the header comment in each file says the same. Deliberately self-contained (no shared module) so each file can be dropped anywhere in Fusion's Scripts menu tree.

Details worth preserving when editing: `VERSION_RE` accepts any separator/padding/case (`\v001\`, `/v0001/`, `\V5\`); only sibling folders that exist on disk are candidates; the reload trick is re-setting `tool.Clip` twice plus a `TOOLB_PassThrough` toggle; clip length is read at `COMPN_GlobalStart` because it is unreliable elsewhere; the sequence start frame is re-derived from the filename's `...NNNN.exr` field.

### deadline_quick_submit_mijo (`Script/Comp/mijo_WIP/deadline_quick_submit_mijo/`)

`A_mj_deadline_quick_submit.py` is a no-dialog replacement for Deadline's stock Fusion submitter (`<repo>/submission/Fusion/Main/SubmitToDeadline.eyeonscript`). It auto-saves the comp, runs QC, writes job/plugin info files to the temp dir, and shells out to `deadlinecommand` **on a daemon thread** so Fusion's UI never blocks.

The job/plugin info keys and the `?`-padding of saver output paths mirror the stock submitter — **if you change either, diff against that eyeonscript first**, since the `Fusion` Deadline plugin parses these keys (`plugins/Fusion/Fusion.options` lists the plugin-info side). QC splits into *errors* (no enabled Saver, saver with no output path, saver output on a local C/D/E drive, relative saver path) which abort with an `AskUser` report, and *warnings* (loader issues) which only print. Movie-format outputs force `MachineLimit=1` / `ChunkSize=1000000`. Settings live in the `DEFAULTS` dict and are overridable per-user via `fusion:SetData("MIJO_DEADLINE_<key>", ...)` without editing the file.

### Other scripts
- `Script/fusion_daily_tools/daily_h264_saver.py` — creates or updates a Saver named `Solvfx_daily_h264_saver` pointing at a dated daily-review folder (`.../<project>/<YYMMDD>/<user>/`). Project/user are auto-detected in priority order (existing saver path → env vars → comp path → system user → placeholder); the filename auto-increments a `_NNN` suffix so an existing file is never overwritten; `.mov`/`.mp4` only; finally it offers a local `comp.Render`.
- `Script/FrameRenderScript/force_re_render_v00010001.lua` — one-liner that sets `self.FrameRenderScript` to bust a stale render cache.
- `davinci/media_version_control.lua` — currently empty (placeholder).

### Sketch-tier scripts (untracked / not hardened)

Two files are early one-offs rather than finished tools. **Do not read them as examples of the conventions above**, and don't "fix" them into the hardened style unless asked — but do expect to harden them if asked to extend them:

- `Script/fusion_daily_tools/fusion_export_template.py` — drops three Savers (JPEG q97, EXR DWAA, ProRes 422 MOV, the last created with `TOOLB_PassThrough` on) onto the comp. Derives output paths from `COMPS_FileName` by **slicing a fixed 11 characters off the comp stem** (`shot_name[:-11]`), so it only works for one studio's naming. It also mixes two entry conventions: `main()` re-fetches its own `fusion` via `bmd.scriptapp("Fusion")`, while the `__main__` block calls `comp.Lock()`/`Unlock()` on the *injected* `comp` global.
- `Script/DCC_3D_intergrate/Blender_csv_to_transform.py` — reads a Blender-exported CSV (`frame,shift_x,shift_y`) chosen via `fusion.RequestFile` and bakes it into a Transform's Center as keyframes. The animation idiom here appears nowhere else in the repo: assign `transform.Center = comp.XYPath()` **first**, then write `transform.Center[frame] = (x, y)` per row. No `MapPath`, no undo block, and `Unlock()` is not in a `finally`.

## Conventions

- Tool/file names carry a `_mijo` (or `mj_`) suffix marking them as this author's; Fusion category is `mijo`. Keep new tools consistent.
- Scripts carry an `A_`/`B_`/`C_`/`D_` prefix (apparently to pin their order in Fusion's alphabetically-sorted Scripts menu — `B`=down, `C`=up, `D`=latest is not meaning-alphabetical). Follow the pattern when adding a sibling. The prefix+suffix convention applies to the `Script/Comp/mijo_WIP/**` tools that ship into Fusion's menu; the loose scripts in `Script/fusion_daily_tools/` and `Script/DCC_3D_intergrate/` don't carry it, and `DCC_3D_intergrate` is spelled that way (not `integrate`) on disk — match the existing spelling in paths rather than correcting it.
- Comments and README docs mix English and Traditional Chinese — match the surrounding file.
- Work happens on dated branches (`YYMMDD_X`, e.g. `260712_A`), each continuing from the last. **`main` is stale** — it has not moved since `de302d0` and the dated branches were never merged back, so never treat `main` as the current state or diff against it.
