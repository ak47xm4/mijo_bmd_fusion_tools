# Fisheye Equidistant 180° — reference

Formulas and mappings for the skill. Fusion pixel origin is bottom-left, Y up. `SamplePixelB` takes pixel coords. Point controls are 0–1 of the frame.

## Projection

**Equidistant:** `r = f · θ` with θ the angle from the optical axis (radians).

**180°** in this repo means the **image-circle diameter is 180°**, so centre → circle edge is **90°**:

```
θ_max = π/2
```

Camera frame: +Z through the lens, +X right, +Y up (matches Fusion Y-up).

```
f = R / θ_max
```

`R` is the image-circle radius **in pixels**.

### Circle Radius control

Let `m = 0.5 * min(Width, Height)`.

```
R = CircleRadius * 2 * m
```

With `CircleRadius` default **0.5**:

| CircleRadius | Meaning                                                                                  |
| ------------ | ---------------------------------------------------------------------------------------- |
| 0.5          | Inscribed circular 180°. Frame corners are outside the hemisphere.                       |
| > 0.5        | Cropped / full-frame: 180° circle larger than the inscribed circle; frame edge is < 90°. |
| < 0.5        | Circle smaller than the frame (letterboxed circular fisheye).                            |

`Fisheye Centre` `(cx, cy)` in pixels: `CenterX * Width`, `CenterY * Height`.

### unproject / project

```lua
local function fe_unproject(x, y, cx, cy, f, thetaMax)
    local dx, dy = x - cx, y - cy
    local r = math.sqrt(dx * dx + dy * dy)
    local theta = r / f
    if theta > thetaMax then
        return nil  -- outside FOV
    end
    local phi = math.atan2(dy, dx)
    local st, ct = math.sin(theta), math.cos(theta)
    return st * math.cos(phi), st * math.sin(phi), ct
end

local function fe_project(dx, dy, dz, cx, cy, f, thetaMax)
    local theta = math.atan2(math.sqrt(dx * dx + dy * dy), dz)
    if theta > thetaMax or dz < 0.0 then
        return nil
    end
    local phi = math.atan2(dy, dx)
    local r = f * theta
    return cx + r * math.cos(phi), cy + r * math.sin(phi)
end
```

Outside FOV: skip the sample. Do not clamp θ and keep sampling — that piles energy on the circle.

### Other fisheye r(θ) (do not mix)

Only the `r ↔ θ` line changes if a later mode is added:

| Model                    | r(θ)           |
| ------------------------ | -------------- |
| Equidistant (this skill) | `f · θ`        |
| Equisolid                | `2 f sin(θ/2)` |
| Stereographic            | `2 f tan(θ/2)` |
| Orthographic             | `f sin(θ)`     |

Stereographic is the one where great circles can look like circular arcs in the image. Equidistant does **not**.

## Sphere walks

### Rodrigues

Rotate unit vector `v` about unit axis `k` by angle `a` (right-hand):

```
v' = v cos a + cross(k, v) sin a + k * dot(k, v) * (1 - cos a)
```

### slerp

```
dot = clamp(dot(a, b), -1, 1)
omega = acos(dot)
if omega < 1e-6 then return a
return (sin((1-t)*omega) * a + sin(t*omega) * b) / sin(omega)
```

Use for Godrays dest→light. `t` is **equal angle**, not equal pixels.

Inside a 180° hemisphere `dot` should stay ≥ 0. If `dot < -0.999`, skip.

### Tangent basis at `dir`

Optical-axis meridians / parallels:

```
east = normalize((-dir.y, dir.x, 0))     -- +φ; degenerate on axis → use (1,0,0)
north = cross(dir, east)                 -- +θ toward the circle? check sign
-- +θ (away from +Z) is: (ct*cosφ, ct*sinφ, -st)
```

On the optical axis (`dir ≈ (0,0,1)`), pick `east = (1,0,0)`, `north = (0,1,0)`.

## Glint

### Mode A (current, Rectilinear)

```
ux, uy = normalize(cos(ang)*aspect, sin(ang))
sx = px - dist * ux
sy = py - dist * uy
```

`dist` in pixels. Perp tent: `(-uy, ux) * off`.

### Mode B camera-fixed (recommended)

Ray `i` at `ang = rot + i * 360/nRays` (Fusion CCW, degrees).

A **fixed** 3D axis gives a small circle of constant angle from that axis (parallels). The equator (`ang = 0` with axis = camera Y) is a great circle.

```
-- ray direction in the tangent plane at the optical axis:
-- (cos ang, sin ang, 0), then axis = that × (0,0,1) wait:
-- rotation axis for a streak along tangent T_axis = (cos ang, sin ang, 0):
A = normalize(cross((0,0,1), T_axis))  -- = (-sin ang, cos ang, 0)
-- walking from dir by rotating about A moves on the plane perpendicular to A.
```

Aspect: scale the **axis-plane** tangent before building `A`, same as today’s `dx *= aspect` then renormalise — but in camera XY, not after projection.

Length: `dθ = (length * oddMul * mag * weightMul) / f`.

Along-path samples: `n = ceil(dθ * f)` capped like today’s `SMOOTH_CAP`.

Width: at `dir_s`, `perp = normalize(cross(A, dir_s))`. Offset `off` pixels → angle `off / f` (equidistant: `dr/dθ = f` everywhere, so a purely radial offset is uniform; a purely azimuthal offset is `off / (f sin θ)` in φ. Using a 3D unit-sphere offset of `off/f` along `perp` is the consistent “pixel size at centre” convention).

**Gather caveat:** this finds highlights that lie on the **same small circle / geodesic through the output pixel** for that axis. It is the spherical analogue of “walk a constant screen direction”. It is **not** “each highlight emits in its own local tangent with a globally parallel 3D direction” unless the axis is camera-fixed, which this is.

### Mode B local bearing (only if asked)

At the output pixel, `T = cos(ang)*east + sin(ang)*north`, `A = normalize(cross(dir, T))`, then Rodrigues. Stars appear to rotate around the fisheye circle.

## Godrays

Current inverse (Rectilinear) at smear `t ∈ [0,1]`:

```
v = dest - C - T*t
v = rotate(v, -rot*t)
v = v / lerp(1, scale, t)
v.x -= (skew*t) * v.y
sample v + C
```

`C` is both lens axis and vanish point.

### Mode B v1 mapping (intent, not a 1:1 affine)

| 2D control           | Sphere                                                                                                                                                                                    |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Center`             | **Light** = `unproject(Center)` using **Lens Centre** + `R`                                                                                                                               |
| new `Fisheye Centre` | Lens axis for unproject/project                                                                                                                                                           |
| Translate            | Fold into Light (image-space vanish = Centre+Translate, then unproject). Or keep as an extra image offset **before** unproject of Light only — do not add `T*t` in pixels along the walk. |
| Scale                | `θ' = θ / lerp(1, scale, t)` about the lens axis (multiply the XY of `dir` and renormalise, or slerp toward/away from `+Z`)                                                               |
| Rotate               | `φ' = φ - rot*t` about `+Z`                                                                                                                                                               |
| Skew                 | **Ignore in v1.** No clean spherical analogue. Status text when Projection is Equidistant.                                                                                                |

Primary smear (the “godray toward a point” look):

```
dir_t = slerp(unproject(dest), lightDir, t)
```

Then apply Scale/Rotate about `+Z` if those sliders are off identity.

Do **not** slerp toward Lens Centre unless Light is on-axis. On-axis Light + Scale-only → meridians → still straight in the image.

## GCA

Current radial weight:

```
rn = hypot(field-rotated, aspect-scaled offset) / rRef
```

`rRef` today is the **half-diagonal**. For Mode C:

```
rRef = R
```

Inner/Outer are fractions of the **circle**, i.e. of `θ_max`.

Inverse of a radial scale `sc` around the lens axis in equidistant:

```
θ_src = θ_dest / lerp(1, sc, t)
```

which is the same as `r_src = r_dest / lerp(1, sc, t)` **in pixels from the lens centre**, because `r = f θ`. So on-axis spherical radial CA **is** the current divide-by-scale, once `cx,cy` is the lens centre and coordinates are circular (aspect applied in tangent east/north, not with the frame half-diagonal).

Anamorphic CA: scale east vs north in the tangent basis, then project — not `x *= aspect` in frame pixels unless Lens Centre is frame centre and the plate is already circular.

Linear (prism) translate: a constant pixel shift is Mode A. Mode C analogue is a constant **angular** prism: add a tangent offset `lin / f` before project. Decide per control; default keep Linear in pixels (cheap-filter look) unless Linear Falloff is on, then use angular.

Axial LoCA: four taps at `±(axial/f)` along east and north of the **sample dir**, then project.

Allow Minify: minify → larger θ → samples toward / past the circle. Same lift-so-min(RGB scale)=1 default.

## Fuse wiring reminder

Adding a control is four edits: `Create` `AddInput`, `Process` `GetValue`, `userData` key, use inside `processPixel` / `*_gen` **arguments**. Miss userData → silent `nil` in the pixel loop.

Long-lived `*_gen` must not read `Cx`, `R`, `Proj`, … as globals. Pass them in.

`threadinitfunc` still allocates `Pixel()` for each `SamplePixel*` target.

## What the first-pass chat got wrong

- “Replace the walk with slerp” for all three tools — only Godrays-toward-Light is a slerp. Glint is Rodrigues about a ray axis. GCA is θ-scale.
- “Length must be degrees” — UI stays pixels at centre; convert with `f`.
- “Projected path is an arc” — not for equidistant; do not fit circles.
- “Radial CA formula unchanged” — only after `rRef = R` and lens centre, not the frame half-diagonal.
- Ignored then-current Glint AA / Ray Width / Soft / Color — those survive; width becomes a tangent offset.
- Conflated sensor streaks (A) with dome geodesics (B).
