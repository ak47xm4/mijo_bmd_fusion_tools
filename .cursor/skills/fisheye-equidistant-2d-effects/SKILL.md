---
name: fisheye-equidistant-2d-effects
description: >-
  QC'd plan for rewriting mijo 2D Fusion fuses (Glint, Godrays, Godrays CA)
  so smear/distort follows Fisheye Equidistant 180° instead of image-plane
  straight lines. Use when adding a fisheye/equidistant/180° projection mode
  to glint_mijo, godrays_mijo, or godrays_chroma_aberration_mijo, or when the
  user mentions geodesic rays, spherical glint, lens-center vs light, or
  "follow the fisheye" on a 2D effect.
---

# Fisheye Equidistant 180° — 2D effect fuses

Read [reference.md](reference.md) for projection formulas, Rodrigues/slerp, and the Godrays affine map.

Do **not** implement from the first-pass chat idea of “replace every walk with slerp”. That over-simplified Godrays and Glint.

## QC verdict (do this, not the naive port)

The gather architecture stays. Only the **path** changes, and only when the effect is meant to live **on the sphere**.

Three different meanings of “follow fisheye” — pick one per feature, name it in UI/comments:

| Mode              | Meaning                                     | Path                                                                                          |
| ----------------- | ------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **A Sensor**      | Star filter / anamorphic streak on the chip | Keep image-space straight lines (`p - dist*(ux,uy)`). **Do not** convert.                     |
| **B Sphere**      | Dome / 180 plate / 3D light                 | `unproject → walk on sphere → project`                                                        |
| **C Field angle** | TCA / radial CA / falloff vs θ              | Parameterize by θ. Equidistant already has `r ∝ θ`; calibrate `R`, do not invent a new curve. |

Default ask in this repo (“distort 不要像 godray 直線射出”) is **B** for Glint + Godrays-toward-a-point, **C** for GCA radial, **A** left as the existing path behind a Projection control.

Radial lines **through the optical centre** are already geodesics. A centre-only scale Godray will look almost the same after the port. The mismatch is **off-axis vanish**, **fixed-angle Glint streaks**, and **CA falloff using the frame half-diagonal**.

## Hard rules

1. **Never undistort → 2D effect → redistort** as the primary path (pole, seams, extra filter). Sphere walk inside `processPixel` only.
2. **Never assume the projected geodesic is a circular arc.** Stereographic maps circles to circles; equidistant does not. Always `unproject / rotate / project`.
3. **Do not replace Godrays’ full affine inverse with one slerp.** Map intent (see [reference.md](reference.md) § Godrays). v1 fisheye Godrays = geodesic smear toward **Light**; scale/rotate around **Lens Centre** as θ/φ; skip Skew.
4. **Split Lens Centre and Light.** Today `Center` is both. Fisheye needs Lens Centre for unproject/project (default 0.5, 0.5) and Light as the 3D vanish (`unproject(Center)` of the existing control).
5. **Glint gather is not “the same unit vector in pixels”.** Walking constant `(ux,uy)` is Mode A. Mode B: from the output `dir`, take a tangent, Rodrigues-rotate. Two sub-modes — pick explicitly:
   - **Camera-fixed** (recommended for anamorphic-on-dome): each ray is rotation about a **fixed 3D axis** (e.g. camera Y = horizontal parallels; equator is the only great-circle horizontal).
   - **Local bearing**: rebuild east/north at the output pixel, geodesic in that heading. Stars twist around the circle.
6. **Length / Ray Width stay in pixels in the UI.** Internally they are arc length **at the optical centre**: `f = R / (π/2)`, `dθ = length_px / f`. Do not force the user onto a Degrees slider as the only unit.
7. **Sample in equal Δθ**, not equal pixel distance. Reuse Smooth’s “~1 sample per pixel at centre” as `n = max(1, round(dθ * f))`.
8. **Clip θ > θ_max.** Outside the image circle, skip the sample (black / no emit). Do not SamplePixel into garbage past 180°.
9. **Keep fuses self-contained.** Copy the same `fe_unproject` / `fe_project` / `fe_rodrigues` block into each `.fuse`. No shared Lua module.
10. **Preserve existing fuse contracts:** `*_gen` worker closure, no reading userData globals from the long-lived closure, four-way control wiring (`AddInput` / `GetValue` / `userData` / pixel), `REG_SupportsDoD`, Fusion Y-up pixel coords, `SamplePixelB`.
11. **Do not drop Glint quality knobs** (AA dest SSAA, Ray Width tent, Soft, Color input, Weight, Normalize Steps, DenseAlong). Width is a **tangent-plane** offset, then project; not `sx += pxp * off` in pixels after a geodesic walk.
12. New tools stay `REGS_Category = "mijo"` and `*_mijo` names.

## When _not_ to change the path

- Plate is rectilinear; user just wants “bendier” rays → that is a look, not this projection.
- Physical star-filter / sensor anamorphic → Mode A.
- Only on-axis radial scale / on-axis radial CA → geometry already compatible; at most retarget `rRef` to the image circle.

## Implementation shape

Add a Projection control rather than forking three new class files, unless the control set diverges so far that one node is unusable:

```
Rectilinear | Equidistant 180
```

Shared new inputs (all three tools that need B/C):

- `Fisheye Centre` — Point, default (0.5, 0.5), optical axis. Hide when Rectilinear.
- `Circle Radius` — 0.5 = inscribed (`0.5 * min(W,H)` in normalised half-min-dim, see reference). Distinguishes circular 180 vs full-frame / cropped.

Godrays extra: existing `Center` = **Light** (vanish). Do not reuse it as the lens axis.

Keep `processPixel` gather. Inside `GLT_gen` / `GRY_gen` / `GCA_gen`, branch once:

```lua
if proj < 0.5 then
    -- existing image-space walk
else
    -- unproject(px,py) -> walk -> project -> SamplePixelB
end
```

Helpers are defined **inside** the worker `if not GEN then` block, same as today’s `inv` / `weightMul`. Pass `cxLens, cyLens, R, f, thetaMax` as arguments, never as closed-over globals.

### Glint Mode B walk (camera-fixed)

Per ray `i`, axis `A_i` is fixed in camera space (see reference). From output `dir`:

```
dir_s = Rodrigues(dir, A_i, -s)    -- s in radians, s = 0..dθ
if dir_s.z < 0 then skip           -- behind camera / past hemisphere
sample project(dir_s)
```

Perpendicular width: `perp = normalize(cross(A_i, dir_s))`, offset angle `off / f`, extra Rodrigues about `dir_s` or add `perp * (off/f)` then renormalise, then project.

### Godrays Mode B walk

```
dirP = unproject(px, py)
dirL = unproject(lightX, lightY)   -- existing Center
dir_t = slerp(dirP, dirL, t)       -- t = 0..1, equal angle
-- optional: apply θ-scale / φ-rotate about lens axis on dir_t
sample project(dir_t)
```

If `dirP ≈ dirL`, copy the source pixel (identity). If `dot < -0.999`, skip or perturb; slerp is unstable at antipodes (should not happen inside a 180° hemisphere).

### GCA Mode C

Keep the inverse scale/rotate/translate **in (θ, φ)** (and anamorphic in the local east/north tangent), not in `(x - cx, y - cy)` pixels.

- `rRef = R` (image-circle radius in pixels), not half-diagonal.
- Inner/Outer stay 0–1 but **of the circle**, i.e. of θ_max.
- `Power` still `u^pwr`.
- Axial plus-taps: offset in the tangent plane by `axial / f`, not `±axial` in x/y.
- Allow Minify still applies: minify samples toward larger θ (toward the circle edge / off the circle). Same solid-primary-border problem; keep the lift-to-min-scale=1 default.

## DoD / RoI

Rectilinear Glint AABB of the straight segment is wrong for a curve. For Equidistant 180, intersect the usual DoD/RoI with the **image circle** (or use the input DataWindow). Do not shrink to the straight-ray bbox.

## QA (Fusion, not fuscript)

fuscript can syntax-check; it cannot validate SamplePixel / DoD.

- [ ] On-axis radial Godray, Light = Lens Centre, Scale only: bit-similar to rectilinear (straight meridians).
- [ ] Light in a corner: streaks **curve** toward the circle, not straight to the point.
- [ ] Glint 2-ray anamorphic, highlight at centre: still a straight horizontal (equator / camera-Y orbit through axis).
- [ ] Same glint, highlight near the circle: streak bends; length in pixels is shorter than at centre for the same Length value.
- [ ] Sample with θ > θ_max is skipped; no wrap from the opposite side of the circle.
- [ ] Circle Radius < 0.5 (cropped) vs 0.5 (inscribed) vs > 0.5 (full-frame 180 on the width): FOV at the frame edge changes, centre scale stays `r ∝ θ`.
- [ ] Projection toggle Rectilinear restores current look (regression on a 1080p checker + 1px dots).
- [ ] Glint AA 2x2 + Ray Width still catches 1px sources on a curved path.
- [ ] Weight / Color inputs still sampled at the **source** geodesic point, not the dest pixel.
- [ ] worker wipe of `GLT_gen` / `GRY_gen` still bit-identical (rebuild guard).

## Priority if implementing

1. Shared unproject/project/Rodrigues block + Projection control on **Glint** (biggest visual win).
2. Godrays geodesic-toward-Light; Scale/Rotate around Lens Centre; Skew ignored with a status note.
3. GCA: `rRef = R`, inverse in (θ, φ), axial in the tangent plane.
