# version_switch_mijo
# ------------------------------------------------------------------------
# Retarget the selected (or all) Loader clip paths that contain a  vNNN
# version folder to a different EXISTING version on disk, then reload the
# footage and fix the frame range.
#
# Self-contained by design: drop this file anywhere in Fusion's Scripts menu
# tree and it just runs (no shared module, no fixed path assumptions).
#
# There are THREE of these scripts (Down / Up / Latest). They are IDENTICAL
# except for the single  MODE = "..."  line below. If you change the logic,
# copy everything below the MODE line to the other two files verbatim.
#
#     MODE = "down"    -> previous existing version
#     MODE = "up"      -> next existing version
#     MODE = "latest"  -> newest existing version
#
# Reload / duration-fix trick adapted from AlbertoGZ's ReloadLoaders.
# Runs inside Fusion's Python console; uses the injected globals comp / fusion.
# ------------------------------------------------------------------------

MODE = "latest"

# ===== shared body (keep identical across Down / Up / Latest) ============
import os
import re

# Matches a  <sep>v<digits><sep>  path segment: any separator, any padding,
# case-insensitive.  e.g.  \v001\   /v0001/   \v12\   \V5\
VERSION_RE = re.compile(r'([\\/])v(\d+)([\\/])', re.IGNORECASE)
# A bare version-folder NAME on disk, e.g.  v001 / v0001 / V5
FOLDER_RE = re.compile(r'v(\d+)$', re.IGNORECASE)


def _list_versions(path, match):
    """Return {version_int: real_folder_name} for every vNNN sibling folder
    that actually exists next to the current version folder on disk."""
    # Parent dir = everything up to and including the separator before vNNN.
    parent = path[:match.start() + 1]
    parent_mapped = comp.MapPath(parent)
    versions = {}
    try:
        entries = os.listdir(parent_mapped)
    except OSError:
        return versions
    for name in entries:
        m = FOLDER_RE.match(name)
        if m and os.path.isdir(os.path.join(parent_mapped, name)):
            versions[int(m.group(1))] = name
    return versions


def _pick_version(versions, current, mode):
    """Choose the target version number from the existing ones, or None."""
    if not versions:
        return None
    keys = sorted(versions)
    if mode == "up":
        higher = [v for v in keys if v > current]
        return higher[0] if higher else None
    if mode == "down":
        lower = [v for v in keys if v < current]
        return lower[-1] if lower else None
    # latest
    return keys[-1]


def _retarget_path(path, match, target_folder):
    """Swap the matched vNNN segment for target_folder, keeping the original
    separators and the rest of the path untouched (Fusion path format)."""
    sep_before, sep_after = match.group(1), match.group(3)
    return (path[:match.start()] + sep_before + target_folder
            + sep_after + path[match.end():])


def switch_versions(mode):
    comp.StartUndo('version_switch_' + mode)

    selLoaders = comp.GetToolList(True, "Loader").values()
    allLoaders = comp.GetToolList(False, "Loader").values()
    toollist = selLoaders if selLoaders else allLoaders

    comp.Lock()

    # Clip length is only reliable at the comp's global start frame.
    currentTime = comp.CurrentTime
    comp.CurrentTime = comp.GetAttrs('COMPN_GlobalStart')

    try:
        for tool in toollist:
            loaderName = tool.GetAttrs("TOOLS_Name")
            loaderPath = tool.GetAttrs("TOOLST_Clip_Name")[1]

            match = VERSION_RE.search(loaderPath)
            if not match:
                print(loaderName + ": no  vNNN  version folder in path, skipped.")
                continue

            current = int(match.group(2))
            versions = _list_versions(loaderPath, match)
            target = _pick_version(versions, current, mode)

            if target is None:
                print(loaderName + ": no " + mode + " version found "
                      "(current v" + match.group(2) + "), skipped.")
                continue

            new_path = _retarget_path(loaderPath, match, versions[target])

            # Force a reload by re-setting the clip name.
            tool.Clip = new_path + ""
            tool.Clip = new_path
            durationNew = tool.GetAttrs("TOOLIT_Clip_Length")[1]

            # Disable/enable to flush the clip cache.
            tool.SetAttrs({"TOOLB_PassThrough": True})
            tool.SetAttrs({"TOOLB_PassThrough": False})

            # Re-derive the sequence start frame from the filename ( ...NNNN.exr ).
            try:
                filePathFrame = int(loaderPath.split('.')[-2])
            except (ValueError, IndexError):
                filePathFrame = 0

            tool.GlobalIn[fusion.TIME_UNDEFINED] = filePathFrame
            tool.GlobalOut[fusion.TIME_UNDEFINED] = filePathFrame + durationNew - 1
            tool.ClipTimeStart[fusion.TIME_UNDEFINED] = 0
            tool.ClipTimeEnd[fusion.TIME_UNDEFINED] = durationNew

            print(loaderName + ": v" + match.group(2) + " -> " + versions[target])
    finally:
        comp.CurrentTime = currentTime
        comp.Unlock()
        comp.EndUndo(True)


switch_versions(MODE)
