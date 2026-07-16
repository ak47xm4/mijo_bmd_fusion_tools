# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal collection of tools for **Blackmagic Fusion / DaVinci Resolve** (targeting Fusion ~18–20.2). There is no build system, test suite, or package manager. Everything here is either a Fusion plugin (`.fuse`) or a script executed *inside* Fusion's Python/Lua console. Code "runs" only when loaded by Fusion — you cannot execute or lint it standalone.

Two artifact types:
- **Fuse plugins** (`fuse/*.fuse`) — self-contained Fusion tools written in **Lua** (VS Code maps `*.fuse` → lua via `.vscode/settings.json`).
- **Scripts** (`Script/**`, `davinci/*.lua`) — Python or Lua run from Fusion's scripting console; they rely on Fusion's injected globals (`comp`, `fusion`, `tool`, `self`) with no imports.

## Deploying / testing changes

Changes are tested by copying the artifact into a live Fusion install and reloading. `copy_test_mijo.cmd` (Windows) copies fuses to a hard-coded farm path:

```
copy /y "fuse\noise_3D_mijo_openCL.fuse" "F:\Z_Afanasy_farm\bmd_fusion\Fuses\"
```

This `.cmd` is **gitignored** and its paths are machine-specific (an Afanasy render-farm layout). Uncomment the relevant `copy` line for whichever artifact you changed. Scripts go to `...\bmd_fusion\Script\Comp\...`. After copying, reload the tool in Fusion (re-add the node, or restart Fusion) to pick up the new source.

## Fuse plugin architecture

A `.fuse` is a Lua module Fusion loads to register a tool. Lifecycle callbacks (all optional except the first two):

- `FuRegisterClass(name, CT_Tool, {...})` — registers the class. `REGS_Category = "mijo"` groups these tools under the "mijo" menu; `REGS_Name` is the display name.
- `Create()` — declares inputs/outputs via `self:AddInput` / `self:AddOutput`. Input controls (`SliderControl`, `ComboControl`, etc.) become the tool's UI. Names/IDs here are read back in `Process`.
- `Process(req)` — the render function. Reads control values with `Input:GetValue(req).Value`, works with `Image{}` objects, and writes pixels. `req.Time` drives animation.
- `OnAddToFlow()` / `OnRemoveFromFlow()` — used by the OpenCL variant to compile/release the GPU kernel.

### The Noise 3D tool (two variants, keep in sync)

`noise_3D_mijo.fuse` and `noise_3D_mijo_openCL.fuse` are the **same tool** — they interpret an input image's R/G/B as an XYZ position and generate noise (Perlin / Simplex / Value / Worley / FBM) from it. Both expose the same control set (Noise Type, Output Mode, Scale X/Y/Z, Octaves/Lacunarity/Persistence, Offsets, Seethe, Min/Max). **When you change controls or noise behaviour in one, mirror it in the other.**

- **CPU variant** (`noise_3D_mijo.fuse`): pure-Lua. Pixel loop runs via `out:MultiProcessPixels(...)` (CPU multithreaded — *not* GPU despite the name). Noise helpers are defined both at module scope and re-inlined inside the pixel function for speed. Hash uses `sin`-based fract tricks.
- **OpenCL variant** (`noise_3D_mijo_openCL.fuse`): embeds an OpenCL kernel as the `clsource` string at the top of the file. `OnAddToFlow` compiles it via `OCLManager():BuildCachedProgram(...)`. `Process` dispatches to the GPU when the "Processing Mode" control is Auto/GPU and **falls back to the CPU `MultiProcessPixels` path** otherwise or on failure. The kernel is deliberately **trig-free** (integer hash + Perlin bit-selection gradients) for GPU throughput — see the commit history and `fuse/GPU_ACCELERATION_README.md`. Keep GPU-kernel math and CPU-fallback math producing the same result.

`fuse/GPU_ACCELERATION_README.md` (in Traditional Chinese) explains enabling OpenCL in Fusion Preferences and the CPU-vs-GPU reality of fuses.

## Scripts

Fusion console scripts assume globals are already present. Common idioms seen throughout:
- Wrap mutations in `comp.StartUndo('label')` … `comp.EndUndo(True)`.
- `comp.GetToolList(selectedOnly, "Loader")`, `tool.GetAttrs("TOOLST_Clip_Name")` / `tool.SetAttrs({...})`, `comp.MapPath(path)`, `fusion.TIME_UNDEFINED`.

### version_switch_mijo (`Script/Comp/mijo_WIP/version_switch_mijo/`)

`B_mj_version_Down.py`, `C_mj_version_up.py`, `D_mj_version_latest.py` are **near-identical** — they retarget Loader clip paths containing a `\vNNN\` version folder to a different existing version on disk. The **only** meaningful difference between the three is the scan-loop direction (down / up / newest-existing). A behaviour change to the path logic must be applied to all three.

### deadline_quick_submit_mijo (`Script/Comp/mijo_WIP/deadline_quick_submit_mijo/`)

`A_mj_deadline_quick_submit.py` is a no-dialog replacement for Deadline's stock Fusion submitter (`<repo>/submission/Fusion/Main/SubmitToDeadline.eyeonscript`). It auto-saves the comp, runs QC, writes job/plugin info files to the temp dir, and shells out to `deadlinecommand` **on a daemon thread** so Fusion's UI never blocks.

The job/plugin info keys and the `?`-padding of saver output paths mirror the stock submitter — **if you change either, diff against that eyeonscript first**, since the `Fusion` Deadline plugin parses these keys (`plugins/Fusion/Fusion.options` lists the plugin-info side). QC splits into *errors* (no enabled Saver, saver output on a local C/D/E drive, relative saver path) which abort, and *warnings* (loader issues) which only print. Settings live in the `DEFAULTS` dict and are overridable per-user via `fusion:SetData("MIJO_DEADLINE_<key>", ...)` without editing the file.

### Other scripts
- `Script/fusion_daily_tools/daily_h264_saver.py` — creates/updates a Saver node named `Solvfx_daily_h264_saver` pointing at a dated daily-review folder (`.../<project>/<YYMMDD>/<user>/`), auto-detecting project/user from the path, env vars, or comp file.
- `Script/FrameRenderScript/force_re_render_v00010001.lua` — one-liner that sets `self.FrameRenderScript` to bust a stale render cache.
- `davinci/media_version_control.lua` — currently empty (placeholder).

## Conventions

- Tool/file names carry a `_mijo` (or `mj_`) suffix marking them as this author's; Fusion category is `mijo`. Keep new tools consistent.
- Comments and README docs mix English and Traditional Chinese — match the surrounding file.
