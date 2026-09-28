# A_mj_relight_bind_lights.py
# ------------------------------------------------------------------------
# Bind Fusion 3D lights (and a camera) onto Relight 2.5D mijo.
#
# Fuse tools cannot take a Scene input, so the relight lives on eight light
# slots. This script ConnectTo's the slot sliders to the light's own
# Translate / Rotate / Color / Intensity / Decay / Cone, which keeps the
# fuse cache live when those controls move.
#
# Limitation: the link is the light's own Translate and Rotate. A parent
# Merge3D transform is NOT folded in. Put the light's world position on the
# light itself, in the same numeric space as the position pass. If a parent
# is animated, move that animation onto the light before binding.
#
# 限制：連的是燈自己的 Translate / Rotate，不疊加父層 Merge3D 的位移。
# 燈的數字要與 position pass 同一個 world 空間。
#
# How to run (inside Fusion):
#   Select one Relight 2.5D mijo, and either
#     - a Merge3D that contains the lights / camera, or
#     - the Point / Spot / Directional / Ambient lights and a Camera3D.
#   Then run this script from the Scripts menu.
#
# Self-contained: drop this file anywhere in Fusion's Scripts menu tree.
# Script IDs must match fuse/relight_25d_mijo.fuse (L1..L8, Amb*, Cam*).
# ------------------------------------------------------------------------

MAX_LIGHTS = 8

LIGHT_IDS = ("LightPoint", "LightSpot", "LightDirectional")
AMBIENT_ID = "LightAmbient"
CAMERA_ID = "Camera3D"
MERGE_ID = "Merge3D"
RELIGHT_ID = "Relight25D_mijo"

# Fuse Type combo: 0 Point, 1 Directional, 2 Spot.
TYPE_VALUE = {
    "LightPoint": 0,
    "LightDirectional": 1,
    "LightSpot": 2,
}

# Fuse slider suffix -> light input id. Decay / cone are added per type.
COMMON_LINKS = (
    ("PosX", "Transform3DOp.Translate.X"),
    ("PosY", "Transform3DOp.Translate.Y"),
    ("PosZ", "Transform3DOp.Translate.Z"),
    ("RotX", "Transform3DOp.Rotate.X"),
    ("RotY", "Transform3DOp.Rotate.Y"),
    ("RotZ", "Transform3DOp.Rotate.Z"),
    ("Red", "Red"),
    ("Green", "Green"),
    ("Blue", "Blue"),
    ("Intensity", "Intensity"),
)

DECAY_LINK = ("Decay", "DecayType")
SPOT_LINKS = (
    ("Cone", "ConeAngle"),
    ("Penumbra", "PenumbraAngle"),
    ("Dropoff", "Dropoff"),
)

SLOT_SUFFIXES = (
    "On",
    "Type",
    "PosX",
    "PosY",
    "PosZ",
    "RotX",
    "RotY",
    "RotZ",
    "Red",
    "Green",
    "Blue",
    "Intensity",
    "Decay",
    "Cone",
    "Penumbra",
    "Dropoff",
)


def _attr(obj, key):
    try:
        attrs = obj.GetAttrs()
        if isinstance(attrs, dict) and key in attrs:
            return attrs[key]
    except Exception:
        pass
    try:
        return obj.GetAttrs(key)
    except Exception:
        return None


def _tool_id(tool):
    value = None
    try:
        value = tool.ID
    except Exception:
        value = _attr(tool, "TOOLS_RegID")
    if value is None:
        return ""
    return str(value)


def _tool_name(tool):
    try:
        name = tool.Name
        if name:
            return str(name)
    except Exception:
        pass
    name = _attr(tool, "TOOLS_Name")
    return str(name) if name else "?"


def _get_input(tool, name):
    try:
        inp = tool.GetInput(name)
        if inp is not None:
            return inp
    except Exception:
        pass
    obj = tool
    for part in name.split("."):
        obj = getattr(obj, part)
    return obj


def _connected_tool(inp):
    if inp is None:
        return None
    try:
        out = inp.GetConnectedOutput()
    except Exception:
        return None
    if not out:
        return None
    try:
        return out.GetTool()
    except Exception:
        return None


def _disconnect(inp):
    if inp is None:
        return
    if _connected_tool(inp) is None:
        return
    try:
        inp.ConnectTo(None)
        return
    except Exception:
        pass
    try:
        inp.ConnectTo()
    except Exception as exc:
        print("Relight bind: could not disconnect an input (%s)" % exc)


def _set_number(inp, value):
    _disconnect(inp)
    inp[fusion.TIME_UNDEFINED] = value


def _connect(dst, src, label):
    _disconnect(dst)
    try:
        dst.ConnectTo(src)
    except Exception as exc:
        print("Relight bind: failed to connect %s (%s)" % (label, exc))


def _input_id(inp):
    value = _attr(inp, "INPS_ID")
    return str(value) if value else ""


def _scene_children(tool):
    kids = []
    try:
        inputs = list(tool.GetInputList().values())
    except Exception:
        return kids
    for inp in inputs:
        iid = _input_id(inp)
        if iid == "SceneInput" or iid.startswith("SceneInput"):
            child = _connected_tool(inp)
            if child is not None:
                kids.append(child)
    return kids


def _collect(tool, seen, ambients, lights, cameras):
    if tool is None:
        return
    key = _tool_name(tool)
    if key in seen:
        return
    seen.add(key)
    tid = _tool_id(tool)
    if tid == MERGE_ID:
        for child in _scene_children(tool):
            _collect(child, seen, ambients, lights, cameras)
        return
    if tid == AMBIENT_ID:
        ambients.append(tool)
    elif tid in LIGHT_IDS:
        lights.append(tool)
    elif tid == CAMERA_ID:
        cameras.append(tool)


def _slot_input(relight, index, suffix):
    return _get_input(relight, "L%d%s" % (index, suffix))


def _clear_slot(relight, index):
    for suffix in SLOT_SUFFIXES:
        _disconnect(_slot_input(relight, index, suffix))
    _set_number(_slot_input(relight, index, "On"), 0)


def _link_pairs(relight, index, light, pairs):
    light_name = _tool_name(light)
    for suffix, src_id in pairs:
        dst = _slot_input(relight, index, suffix)
        src = _get_input(light, src_id)
        _connect(dst, src, "%s -> %s.%s" % (light_name, "L%d" % index, suffix))


def _bind_light(relight, index, light):
    tid = _tool_id(light)
    _set_number(_slot_input(relight, index, "On"), _enabled_now(light))
    _set_number(_slot_input(relight, index, "Type"), TYPE_VALUE[tid])
    _link_pairs(relight, index, light, COMMON_LINKS)

    # Directional lights have no decay or cone. Point lights have decay only.
    # Disconnect whatever the slot is not taking so a previous bind cannot linger.
    if tid == "LightDirectional":
        _disconnect(_slot_input(relight, index, "Decay"))
        _set_number(_slot_input(relight, index, "Decay"), 0)
        for suffix, _src in SPOT_LINKS:
            _disconnect(_slot_input(relight, index, suffix))
    elif tid == "LightPoint":
        _link_pairs(relight, index, light, (DECAY_LINK, ))
        for suffix, _src in SPOT_LINKS:
            _disconnect(_slot_input(relight, index, suffix))
    else:
        _link_pairs(relight, index, light, (DECAY_LINK, ) + SPOT_LINKS)


def _enabled_now(tool):
    try:
        value = float(tool.Enabled[comp.CurrentTime])
    except Exception:
        return 1
    return 1 if value > 0.5 else 0


def _bind_ambient(relight, light):
    light_name = _tool_name(light)
    for suffix, src_id in (("Red", "Red"), ("Green", "Green"),
                           ("Blue", "Blue"), ("Intensity", "Intensity")):
        dst_id = "Amb" + suffix if suffix != "Intensity" else "AmbIntensity"
        _connect(_get_input(relight, dst_id), _get_input(light, src_id),
                 "%s -> %s" % (light_name, dst_id))


def _clear_ambient(relight):
    for dst_id in ("AmbRed", "AmbGreen", "AmbBlue", "AmbIntensity"):
        _disconnect(_get_input(relight, dst_id))
    _set_number(_get_input(relight, "AmbIntensity"), 0)


def _bind_camera(relight, camera):
    name = _tool_name(camera)
    for axis in ("X", "Y", "Z"):
        _connect(
            _get_input(relight, "Cam" + axis),
            _get_input(camera, "Transform3DOp.Translate." + axis),
            "%s -> Cam%s" % (name, axis),
        )


def _unbind_camera(relight):
    # Drop the link but keep the number that was already on the slider,
    # so specular still has a manual eye position.
    for axis in ("X", "Y", "Z"):
        _disconnect(_get_input(relight, "Cam" + axis))


def _apply(relight, ambients, lights, cameras):
    ambients = sorted(ambients, key=_tool_name)
    lights = sorted(lights, key=_tool_name)
    cameras = sorted(cameras, key=_tool_name)

    used = lights[:MAX_LIGHTS]
    skipped = lights[MAX_LIGHTS:]

    if ambients:
        _bind_ambient(relight, ambients[0])
        if _enabled_now(ambients[0]) == 0:
            print(
                "  %s is disabled on the node; its Intensity is still linked."
                % _tool_name(ambients[0]))
        for extra in ambients[1:]:
            print("  skipped extra ambient %s (only the first is used)." %
                  _tool_name(extra))
    else:
        _clear_ambient(relight)
        print("  no Ambient Light; ambient intensity set to 0.")

    for index, light in enumerate(used, start=1):
        _bind_light(relight, index, light)
        if _enabled_now(light) == 0:
            print("  %s is disabled; Light %d Enable was set off." %
                  (_tool_name(light), index))

    for index in range(len(used) + 1, MAX_LIGHTS + 1):
        _clear_slot(relight, index)

    if cameras:
        _bind_camera(relight, cameras[0])
        if len(cameras) > 1:
            print("  skipped extra camera %s (only the first is used)." %
                  _tool_name(cameras[1]))
            for extra in cameras[2:]:
                print("  skipped extra camera %s." % _tool_name(extra))
    else:
        _unbind_camera(relight)
        print(
            "  no Camera3D. Specular uses the manual Camera X/Y/Z on the tool."
        )

    print("Relight bind: %s" % _tool_name(relight))
    if ambients:
        print("  ambient: %s" % _tool_name(ambients[0]))
    if cameras:
        print("  camera: %s" % _tool_name(cameras[0]))
    print("  lights: %d bound, %d skipped" % (len(used), len(skipped)))
    for index, light in enumerate(used, start=1):
        print("    Light %d <- %s (%s)" %
              (index, _tool_name(light), _tool_id(light)))
    for light in skipped:
        print("    skipped %s (only %d slots)" %
              (_tool_name(light), MAX_LIGHTS))


def bind_relight():
    selected = list(comp.GetToolList(True).values())
    relights = [tool for tool in selected if _tool_id(tool) == RELIGHT_ID]
    if not relights:
        print("Select one Relight 2.5D mijo, plus lights or a Merge3D.")
        return
    relights = sorted(relights, key=_tool_name)
    if len(relights) > 1:
        print("More than one Relight 2.5D selected; using %s." %
              _tool_name(relights[0]))
    relight = relights[0]

    merges = [tool for tool in selected if _tool_id(tool) == MERGE_ID]
    ambients = []
    lights = []
    cameras = []
    seen = set()

    if merges:
        print("Reading lights from %d Merge3D." % len(merges))
        for merge in merges:
            _collect(merge, seen, ambients, lights, cameras)
        if not cameras:
            for tool in selected:
                if _tool_id(tool) == CAMERA_ID:
                    cameras.append(tool)
    else:
        for tool in selected:
            tid = _tool_id(tool)
            if tid == AMBIENT_ID or tid in LIGHT_IDS or tid == CAMERA_ID:
                _collect(tool, seen, ambients, lights, cameras)

    if not ambients and not lights and not cameras:
        print(
            "No Point, Spot, Directional, Ambient, or Camera3D found in the selection."
        )
        return

    comp.StartUndo("Bind Relight Lights")
    comp.Lock()
    try:
        _apply(relight, ambients, lights, cameras)
    finally:
        comp.Unlock()
        comp.EndUndo(True)


bind_relight()
