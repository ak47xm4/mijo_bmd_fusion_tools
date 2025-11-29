# daily_h264_saver.py
# for blackmagic fusion 20.2.3

# by mijo 2025-11-29

# check a saver is naming like Solvfx_daily_h264_saver
# if Solvfx_daily_h264_saver exist, then pass create new one
# if not, then create new one

# when create new one. warning user to enter file path to daily folder with date
# like R:\project_name\251129\user_name\daily_h264.mov

# mov , mp4 are allowed
# other file type are not allowed

# when node is exist, auto check file path is correct
# check mov file is exist
# if not, then create new one ( overwrite is not allowed )
# if exist, then change path to today's date folder. and push mov's nunber of name to next one
# then change path to today's date folder. and push mov's nunber of name to next one

# then ask user to render locally
# if user click yes, then render locally
# if user click no, then pass

import os
import re
from datetime import datetime

comp.StartUndo('daily_h264_saver')

# Get today's date in format YYMMDD (e.g., 251129)
today_date = datetime.now().strftime('%y%m%d')

# Saver node name to check
saver_name = "Solvfx_daily_h264_saver"

# Get all Saver nodes
all_savers = comp.GetToolList(False, "Saver").values()

# Check if the saver node exists
existing_saver = None
for saver in all_savers:
    if saver.GetAttrs("TOOLS_Name") == saver_name:
        existing_saver = saver
        break

# If saver doesn't exist, create a new one
if existing_saver is None:
    # Get the current comp's output
    flow = comp.CurrentFrame.FlowView
    comp.Lock()

    # Create new Saver node
    new_saver = comp.AddTool("Saver", -1, -1)
    new_saver.SetAttrs({"TOOLS_Name": saver_name})

    # Connect to the last output (usually MediaOut or the selected tool)
    # Try to connect to MediaOut first
    media_outs = comp.GetToolList(False, "MediaOut").values()
    if media_outs:
        media_out = list(media_outs)[0]
        new_saver.Input.ConnectTo(media_out.Output)
    else:
        # If no MediaOut, try to connect to selected tool
        selected_tools = comp.GetToolList(True).values()
        if selected_tools:
            selected_tool = list(selected_tools)[0]
            if selected_tool.FindMainInput(1):
                new_saver.Input.ConnectTo(selected_tool.Output)

    comp.Unlock()
    existing_saver = new_saver
    print(f"Created new Saver node: {saver_name}")

# Get current file path from saver
current_path_attr = existing_saver.GetAttrs("TOOLST_Clip_Name")
if current_path_attr:
    current_path = current_path_attr[1]
else:
    current_path = ""

# Check if file path is valid and extract directory
file_dir = ""
file_name = ""
file_ext = ""

if current_path:
    # Normalize path separators
    current_path = current_path.replace('/', os.sep)
    file_dir = os.path.dirname(current_path)
    file_name_with_ext = os.path.basename(current_path)
    file_name, file_ext = os.path.splitext(file_name_with_ext)
    file_ext = file_ext.lower()

    # Validate file extension
    if file_ext not in ['.mov', '.mp4']:
        print(
            f"Warning: Invalid file extension {file_ext}. Only .mov and .mp4 are allowed."
        )
        file_ext = '.mov'  # Default to .mov
else:
    # If no path exists, ask user for input
    default_path = f"R:\\project_name\\{today_date}\\user_name\\daily_h264.mov"
    user_input = comp.AskUser(
        "Daily H264 Saver - Enter File Path",
        {"FilePath": {
            "Name": "File Path",
            "Text": default_path
        }})

    if user_input:
        current_path = user_input.get("FilePath", default_path)
        # Normalize path separators
        current_path = current_path.replace('/', os.sep)
        file_dir = os.path.dirname(current_path)
        file_name_with_ext = os.path.basename(current_path)
        file_name, file_ext = os.path.splitext(file_name_with_ext)
        file_ext = file_ext.lower()

        # Validate file extension
        if file_ext not in ['.mov', '.mp4']:
            print(
                f"Error: Invalid file extension {file_ext}. Only .mov and .mp4 are allowed."
            )
            comp.EndUndo(True)
            raise ValueError(
                f"Invalid file extension: {file_ext}. Only .mov and .mp4 are allowed."
            )
    else:
        print("User cancelled file path input.")
        comp.EndUndo(True)
        raise SystemExit("User cancelled operation.")

# Update path to today's date folder
# Extract project path (everything before the date folder)
# Handle both Windows and Unix-style paths
if file_dir:
    # Normalize path separators
    normalized_dir = file_dir.replace('/', os.sep).replace('\\', os.sep)

    # Split path into parts
    if os.sep in normalized_dir:
        path_parts = normalized_dir.split(os.sep)
        # Remove empty parts but preserve structure
        path_parts = [p for p in path_parts if p]

        # Handle Windows drive letter (e.g., "C:")
        if len(path_parts) > 0 and len(
                path_parts[0]) == 2 and path_parts[0][1] == ':':
            # Keep drive letter as first part
            pass
    else:
        path_parts = [file_dir] if file_dir else []

    date_folder_index = -1

    # Find the date folder (format: YYMMDD)
    for i, part in enumerate(path_parts):
        if re.match(r'^\d{6}$', part):  # Match 6-digit date format
            date_folder_index = i
            break

    if date_folder_index >= 0:
        # Replace date folder with today's date
        path_parts[date_folder_index] = today_date
        # Reconstruct path
        if len(path_parts) > 0 and len(
                path_parts[0]) == 2 and path_parts[0][1] == ':':
            # Windows path with drive letter
            file_dir = path_parts[0] + os.sep + os.sep.join(path_parts[1:])
        else:
            file_dir = os.sep.join(path_parts)
    else:
        # If no date folder found, append today's date folder
        file_dir = os.path.join(file_dir, today_date)
else:
    # If no directory, create a default one
    file_dir = os.path.join("R:", "project_name", today_date, "user_name")

# Ensure directory exists
try:
    mapped_dir = comp.MapPath(file_dir)
    os.makedirs(mapped_dir, exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create directory {file_dir}: {str(e)}")

# Check if file exists and increment number if needed
# Look for pattern like daily_h264_001.mov or daily_h264_1.mov
number_match = re.search(r'_(\d+)$', file_name)
if number_match:
    base_name = file_name[:number_match.start()]
    start_number = int(number_match.group(1))
else:
    base_name = file_name
    start_number = 0

# Check current file path first
current_file_path = os.path.join(file_dir, f"{file_name}{file_ext}")
current_mapped_path = comp.MapPath(current_file_path)
file_exists = os.path.exists(current_mapped_path)

# Find the next available file number
final_path = ""
if file_exists:
    # File exists, start from start_number + 1
    search_start = start_number + 1
else:
    # File doesn't exist, start from start_number
    search_start = start_number

for i in range(search_start, 1000):  # Max 1000 versions
    if i == 0:
        test_name = base_name
    else:
        test_name = f"{base_name}_{i:03d}"

    test_path = os.path.join(file_dir, f"{test_name}{file_ext}")
    mapped_path = comp.MapPath(test_path)

    if not os.path.exists(mapped_path):
        final_path = test_path
        break

if not final_path:
    # If we couldn't find an available number, use search_start
    if search_start == 0:
        final_path = os.path.join(file_dir, f"{base_name}{file_ext}")
    else:
        final_path = os.path.join(file_dir,
                                  f"{base_name}_{search_start:03d}{file_ext}")

# Set the file path to saver
existing_saver.Clip = final_path
print(f"Saver file path set to: {final_path}")

# Try to set H.264 encoding if possible (Fusion 20.2.3)
try:
    # Set codec to H.264 if available
    if hasattr(existing_saver, 'Codec'):
        existing_saver.Codec = "H.264"
    # Alternative attribute names for different Fusion versions
    elif hasattr(existing_saver, 'GetAttrs'):
        attrs = existing_saver.GetAttrs()
        # Try to set via attributes if available
        # Note: Codec setting may vary by Fusion version
except Exception as e:
    print(f"Note: Could not set H.264 codec automatically: {str(e)}")
    print("Please manually set the codec to H.264 in the Saver settings.")

# Render the saver directly
print("=" * 60)
print("Daily H264 Saver - Starting render")
print(f"Output file: {final_path}")
print("=" * 60)

# Use Checkbox format for reliable dialog handling in Fusion
# According to Fusion 8 Scripting Guide, Checkbox returns 1 (checked) or 0 (unchecked)
# Default value 1 means checkbox is checked by default
dialog_result = comp.AskUser(
    "Daily H264 Saver - Render Confirmation",
    {"Render": {
        "Name": "Render now?",
        "Default": 1,
        "Checkbox": True
    }})

print(f"Dialog result: {dialog_result}")
print(f"Dialog result type: {type(dialog_result)}")

# Handle dialog result according to Fusion API
# If user clicks Cancel, dialog_result is None or False
# If user clicks OK, dialog_result is a dict with the checkbox value
should_render = False

# Check if user clicked Cancel (None or False)
if dialog_result is None or dialog_result is False:
    print("User clicked Cancel - skipping render")
    should_render = False
elif isinstance(dialog_result, dict):
    # User clicked OK - get the checkbox value
    print(f"Dialog keys: {list(dialog_result.keys())}")

    # Get the checkbox value (try different key variations)
    render_value = None
    if "Render" in dialog_result:
        render_value = dialog_result["Render"]
    elif "render" in dialog_result:
        render_value = dialog_result["render"]
    else:
        # Try case-insensitive search
        for key in dialog_result.keys():
            if key.lower() == "render":
                render_value = dialog_result[key]
                break

    print(f"Render value: {render_value}, type: {type(render_value)}")

    if render_value is not None:
        # Checkbox returns 1 for checked, 0 for unchecked
        if isinstance(render_value, bool):
            should_render = render_value
            print(f"Boolean value: {should_render}")
        elif isinstance(render_value, (int, float)):
            should_render = (render_value == 1)
            print(
                f"Numeric value: {render_value}, should_render: {should_render}"
            )
        else:
            # Handle string values if any
            render_str = str(render_value).strip().lower()
            should_render = (render_str in ["1", "true", "yes", "y"])
            print(
                f"String value: {render_str}, should_render: {should_render}")
    else:
        print("Warning: Could not find 'Render' key in dialog result")
        print(f"Available keys: {list(dialog_result.keys())}")
        # If we can't find the key but dialog_result exists, assume user clicked OK
        # and default to True (since checkbox default is 1/checked)
        should_render = True
        print(
            "Defaulting to should_render = True (checkbox was checked by default)"
        )
elif isinstance(dialog_result, bool):
    # Direct boolean result
    should_render = dialog_result
    print(f"Direct boolean result: {should_render}")
elif isinstance(dialog_result, (int, float)):
    # Direct numeric result
    should_render = (dialog_result == 1)
    print(
        f"Direct numeric result: {dialog_result}, should_render: {should_render}"
    )
else:
    # Unknown result type
    print(f"Unknown dialog result type: {type(dialog_result)}")
    print(f"Dialog result value: {dialog_result}")
    should_render = False

print(f"Final decision - Should render: {should_render}")

# Only render if user confirmed
if should_render:
    # Render directly without dialog confirmation
    print("Starting local render...")
    comp.Lock()

    # Get render range
    start_frame = comp.GetAttrs("COMPN_RenderStart")
    end_frame = comp.GetAttrs("COMPN_RenderEnd")

    print(f"Render range: {start_frame} to {end_frame}")

    # Render using comp.Render() method
    try:
        # Use comp.Render() with tool reference
        # Wait: True allows user to cancel render through Fusion's Render Queue window
        # User can open Render Queue (Ctrl+Shift+R) and click Cancel button
        render_settings = {"Tool": existing_saver, "Wait": True}
        comp.Render(render_settings)
        print(f"Render completed: {final_path}")
    except Exception as e:
        # Check if render was cancelled by user
        error_msg = str(e).lower()
        if "cancel" in error_msg or "abort" in error_msg or "user" in error_msg:
            print("Render was cancelled by user.")
        else:
            print(f"Render error: {str(e)}")
        comp.Unlock()
        comp.EndUndo(True)
        raise

    comp.Unlock()
else:
    print("Render cancelled by user - skipping render.")

comp.EndUndo(True)
print("Daily H264 Saver setup completed.")
