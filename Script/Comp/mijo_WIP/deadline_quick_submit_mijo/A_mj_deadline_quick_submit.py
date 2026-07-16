# A_mj_deadline_quick_submit.py
# for blackmagic fusion 18 - 20.2 / Deadline 10

# by mijo 2026-07-17

# One-click Deadline submission. No dialog, no manual verify, no manual submit.
# 一鍵下算：自動存檔 -> QC -> 寫 job/plugin info -> 背景 submit。
# deadlinecommand 在背景 process 執行，不佔用 Fusion 前景資源。

import os
import re
import subprocess
import sys
import tempfile
import threading

# ---------------------------------------------------------------------------
# Settings. 覆寫優先序: fusion:SetData("MIJO_DEADLINE_<key>") > 這裡的預設值。
# ---------------------------------------------------------------------------

DEFAULTS = {
    "Pool": "none",
    "SecondaryPool": "",
    "Group": "none",
    "Priority": 50,
    "ChunkSize": 5,
    "MachineLimit": 0,
    "Department": "",
    "TaskTimeoutMinutes": 0,
    "EnableAutoTimeout": 0,
    "LimitGroups": "",
    "Comment": "quick submit by mijo",
    # Fusion 的 render node 版本。0 = 用本機 Fusion 版本 (FUSIONS_Version)。
    "Version": 0,
    "HighQuality": 1,
    "Proxy": 1,
    "CheckOutput": 1,
}

# Movie 格式一台機器包全部 frame，不能切 chunk。與原廠 submitter 同一份清單。
MOVIE_EXTENSIONS = (
    "avi", "vdr", "wav", "dvs", "fb", "omf", "omfi", "stm", "tar", "vpv", "mov",
)

# QC 判定為 local drive 的碟。算圖機看不到這些路徑，一律擋下。
LOCAL_DRIVES = ("c:", "d:", "e:")


def get_setting(key):
    """Read an override from fusion:SetData, else fall back to DEFAULTS."""
    value = fusion.GetData("MIJO_DEADLINE_" + key)
    return DEFAULTS[key] if value is None else value


# ---------------------------------------------------------------------------
# Deadline location
# ---------------------------------------------------------------------------


def find_deadline_command():
    """Locate deadlinecommand.exe / deadlinecommand."""
    exe = "deadlinecommand.exe" if sys.platform == "win32" else "deadlinecommand"

    deadline_path = os.environ.get("DEADLINE_PATH")
    if deadline_path:
        candidate = os.path.join(deadline_path, exe)
        if os.path.isfile(candidate):
            return candidate

    fallbacks = [
        r"C:\Program Files\Thinkbox\Deadline10\bin",
        "/opt/Thinkbox/Deadline10/bin",
        "/Applications/Thinkbox/Deadline10/Resources",
    ]
    for folder in fallbacks:
        candidate = os.path.join(folder, exe)
        if os.path.isfile(candidate):
            return candidate

    return None


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def path_is_movie_format(path):
    extension = os.path.splitext(path)[1].lstrip(".").lower()
    return extension in MOVIE_EXTENSIONS


def replace_frame_no(filename):
    """Swap the trailing frame number for '?' padding, as Deadline expects.

    beauty_0000.exr -> beauty_????.exr / beauty.exr -> beauty????.exr
    """
    file_no_ext, file_ext = os.path.splitext(filename)

    match = re.search(r"(\d+)$", file_no_ext)
    if match:
        digit_count = len(match.group(1))
        file_no_numbers = file_no_ext[:match.start()]
    else:
        digit_count = 4
        file_no_numbers = file_no_ext

    return file_no_numbers + ("?" * digit_count) + file_ext


def is_local_drive(path):
    return path[:2].lower() in LOCAL_DRIVES


def is_absolute_network_path(path):
    """A render node can only resolve a mapped drive or a UNC path."""
    normalized = path.replace("\\", "/")
    return bool(re.match(r"^[A-Za-z]:", normalized)) or normalized.startswith("//")


# ---------------------------------------------------------------------------
# QC
# ---------------------------------------------------------------------------


def get_active_tools(tool_type):
    """Every tool of tool_type that is not passed through."""
    tools = comp.GetToolList(False, tool_type).values()
    return [t for t in tools if not t.GetAttrs()["TOOLB_PassThrough"]]


def sanity_check(savers, loaders):
    """Return (errors, warnings). Errors abort; warnings only print."""
    errors = []
    warnings = []

    if not savers:
        errors.append("Comp has no enabled Saver - nothing to render.")

    for saver in savers:
        name = saver.GetAttrs()["TOOLS_Name"]
        clip = saver.GetAttrs()["TOOLST_Clip_Name"]
        path = clip[1] if clip else ""

        if not path:
            errors.append('Saver "%s" has no output path specified.' % name)
            continue
        if is_local_drive(path):
            errors.append('Saver "%s" is saving to the local %s drive: %s'
                          % (name, path[0].upper(), path))
            continue
        if not is_absolute_network_path(comp.MapPath(path)):
            errors.append('Saver "%s" has a relative output path: %s' % (name, path))

    for loader in loaders:
        name = loader.GetAttrs()["TOOLS_Name"]
        clip = loader.GetAttrs()["TOOLST_Clip_Name"]
        if not clip:
            warnings.append('Loader "%s" has no input path specified.' % name)
            continue
        for path in clip.values():
            if path and is_local_drive(path):
                warnings.append('Loader "%s" is loading from the local %s drive: %s'
                                % (name, path[0].upper(), path))

    return errors, warnings


# ---------------------------------------------------------------------------
# Info files
# ---------------------------------------------------------------------------


def write_info_files(job_name, savers, start_frame, end_frame, is_movie):
    temp_dir = tempfile.gettempdir()

    job_info_path = os.path.join(temp_dir, "mijo_fusion_submit_info.job")
    with open(job_info_path, "w") as fh:
        fh.write("Plugin=Fusion\n")
        fh.write("Name=%s\n" % job_name)
        fh.write("Comment=%s\n" % get_setting("Comment"))
        fh.write("Frames=%d-%d\n" % (start_frame, end_frame))
        fh.write("Priority=%s\n" % get_setting("Priority"))
        fh.write("Pool=%s\n" % get_setting("Pool"))
        fh.write("SecondaryPool=%s\n" % get_setting("SecondaryPool"))
        fh.write("Group=%s\n" % get_setting("Group"))
        fh.write("Department=%s\n" % get_setting("Department"))
        fh.write("TaskTimeoutMinutes=%s\n" % get_setting("TaskTimeoutMinutes"))
        fh.write("EnableAutoTimeout=%s\n" % get_setting("EnableAutoTimeout"))
        fh.write("LimitGroups=%s\n" % get_setting("LimitGroups"))

        if is_movie:
            # 整段 movie 必須在同一台機器上連續寫出。
            fh.write("MachineLimit=1\n")
            fh.write("ChunkSize=1000000\n")
        else:
            fh.write("MachineLimit=%s\n" % get_setting("MachineLimit"))
            fh.write("ChunkSize=%s\n" % get_setting("ChunkSize"))

        for index, saver in enumerate(savers):
            path = saver.GetAttrs()["TOOLST_Clip_Name"][1]
            if not path_is_movie_format(path):
                path = replace_frame_no(path)
            fh.write("OutputFilename%d=%s\n" % (index, comp.MapPath(path)))

    plugin_info_path = os.path.join(temp_dir, "mijo_fusion_plugin_info.job")
    with open(plugin_info_path, "w") as fh:
        version = get_setting("Version")
        if not version:
            match = re.match(r"(\d+\.\d+)", fusion.GetAttrs()["FUSIONS_Version"])
            version = match.group(1) if match else "20"
        fh.write("Version=%s\n" % version)
        fh.write("Build=None\n")
        fh.write("FlowFile=%s\n" % comp_file_name)
        fh.write("HighQuality=%s\n" % get_setting("HighQuality"))
        fh.write("Proxy=%s\n" % get_setting("Proxy"))
        fh.write("CheckOutput=%s\n" % get_setting("CheckOutput"))

    return job_info_path, plugin_info_path


# ---------------------------------------------------------------------------
# Background submission
# ---------------------------------------------------------------------------


def submit_in_background(deadline_command, job_info_path, plugin_info_path):
    """Run deadlinecommand off the main thread so Fusion stays responsive."""

    def worker():
        # CREATE_NO_WINDOW: 不要在 artist 臉上閃一個 console 視窗。
        creation_flags = 0x08000000 if sys.platform == "win32" else 0
        try:
            process = subprocess.Popen(
                [deadline_command, job_info_path, plugin_info_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
            )
            output = process.communicate()[0].decode("utf-8", "replace")
        except Exception as exc:
            print("[mijo quick submit] Submission failed to launch: %s" % exc)
            return

        job_id = next(
            (line.split("=", 1)[1].strip()
             for line in output.splitlines() if line.startswith("JobID=")),
            None,
        )
        if job_id:
            print("[mijo quick submit] Submitted. JobID=%s" % job_id)
        else:
            print("[mijo quick submit] Submission failed:\n%s" % output.strip())

    thread = threading.Thread(target=worker, name="mijo_deadline_submit")
    thread.daemon = True
    thread.start()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

print("=" * 60)
print("mijo Deadline quick submit")

deadline_command = find_deadline_command()
if not deadline_command:
    raise SystemExit(
        "Could not find deadlinecommand. Set the DEADLINE_PATH environment "
        "variable to the Deadline bin folder.")

comp_file_name = comp.GetAttrs()["COMPS_FileName"]
if not comp_file_name:
    raise SystemExit("Save the comp before submitting.")

# 沒存檔就先存 —— 算圖機讀的是硬碟上的檔，不是記憶體裡的 comp。
if comp.GetAttrs()["COMPB_Modified"]:
    comp.Save(comp_file_name)
    print("Comp had unsaved changes - saved before submitting.")

savers = get_active_tools("Saver")
loaders = get_active_tools("Loader")

errors, warnings = sanity_check(savers, loaders)

for warning in warnings:
    print("  WARNING: %s" % warning)

if errors:
    message = "\n".join("- " + e for e in errors)
    print("QC failed:\n%s" % message)
    comp.AskUser("Deadline quick submit - QC failed", {
        1: {
            1: "Errors",
            2: "Text",
            "Lines": max(len(errors) + 1, 3),
            "ReadOnly": True,
            "Default": message,
        }
    })
    raise SystemExit("QC failed - nothing submitted.")

start_frame = int(comp.GetAttrs()["COMPN_RenderStart"])
end_frame = int(comp.GetAttrs()["COMPN_RenderEnd"])
is_movie = any(
    path_is_movie_format(s.GetAttrs()["TOOLST_Clip_Name"][1]) for s in savers)

job_name = os.path.splitext(os.path.basename(comp_file_name))[0]

job_info_path, plugin_info_path = write_info_files(job_name, savers, start_frame,
                                                   end_frame, is_movie)

print("Job    : %s" % job_name)
print("Frames : %d-%d%s" % (start_frame, end_frame,
                            " (movie - single machine)" if is_movie else ""))
print("Pool   : %s   Group: %s   Priority: %s"
      % (get_setting("Pool"), get_setting("Group"), get_setting("Priority")))
for saver in savers:
    print("Output : %s" % saver.GetAttrs()["TOOLST_Clip_Name"][1])
print("Submitting in background...")
print("=" * 60)

submit_in_background(deadline_command, job_info_path, plugin_info_path)
