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
saver_name = "Solvfx_daily_h264_saver"
ALLOWED_EXTENSIONS = ['.mov', '.mp4']


# Helper function to extract project_name and user_name from path
def extract_project_and_user_from_path(path):
    """Extract project_name and user_name from a file path.
    Expected format: R:\\project_name\\YYMMDD\\user_name\\filename.mov
    Returns: (project_name, user_name) or (None, None) if not found
    """
    if not path:
        return None, None

    normalized_path = path.replace('/', os.sep).replace('\\', os.sep)
    path_parts = [p for p in normalized_path.split(os.sep) if p]

    project_name = None
    user_name = None

    # Look for date folder pattern (YYMMDD) - project_name should be before it, user_name after
    date_folder_index = next(
        (i for i, p in enumerate(path_parts) if re.match(r'^\d{6}$', p)), -1)

    if date_folder_index > 0:
        # Project name is typically the folder before date folder
        project_name = path_parts[date_folder_index - 1]

    if date_folder_index >= 0 and date_folder_index < len(path_parts) - 1:
        # User name is typically the folder after date folder
        user_name = path_parts[date_folder_index + 1]

    return project_name, user_name


# Helper function to auto-detect project_name and user_name
def get_project_and_user_names(existing_path=None):
    """Auto-detect project_name and user_name from multiple sources.
    Priority:
    1. Extract from existing saver path
    2. Environment variables (PROJECT_NAME, USERNAME)
    3. Extract from comp file path (if comp is saved)
    4. System username
    5. Default placeholders
    
    Returns: (project_name, user_name)
    """
    project_name = None
    user_name = None

    # 1. Try to extract from existing path
    if existing_path:
        project_name, user_name = extract_project_and_user_from_path(
            existing_path)
        if project_name and user_name:
            print(
                f"Extracted from existing path - Project: {project_name}, User: {user_name}"
            )
            return project_name, user_name

    # 2. Try environment variables
    if not project_name:
        project_name = os.getenv('PROJECT_NAME') or os.getenv('PROJECT')
    if not user_name:
        user_name = os.getenv('USERNAME') or os.getenv('USER') or os.getenv(
            'USERPROFILE')
        # Extract username from USERPROFILE if it's a path
        if user_name and os.sep in user_name:
            user_name = os.path.basename(user_name)

    if project_name and user_name:
        print(
            f"Using environment variables - Project: {project_name}, User: {user_name}"
        )
        return project_name, user_name

    # 3. Try to extract from comp file path (if comp is saved)
    try:
        comp_path = comp.GetAttrs("COMPN_FileName")
        if comp_path:
            comp_dir = os.path.dirname(comp_path)
            # Look for project folder in comp path
            comp_parts = [p for p in comp_dir.split(os.sep) if p]
            # Common patterns: .../project_name/... or .../Projects/project_name/...
            for i, part in enumerate(comp_parts):
                if part.lower() in ['projects', 'project', 'proj'
                                    ] and i < len(comp_parts) - 1:
                    project_name = comp_parts[i + 1]
                    break
            # If not found, try using a parent folder as project name
            if not project_name and len(comp_parts) > 0:
                # Use a meaningful folder name (skip common folders)
                skip_folders = ['comp', 'comps', 'scenes', 'render', 'renders']
                for part in reversed(comp_parts):
                    if part.lower() not in skip_folders and not re.match(
                            r'^\d{6}$', part):
                        project_name = part
                        break
    except Exception as e:
        print(f"Could not extract from comp path: {str(e)}")

    # 4. Get system username if still not found
    if not user_name:
        user_name = os.getenv('USERNAME') or os.getenv('USER')
        if not user_name:
            try:
                import getpass
                user_name = getpass.getuser()
            except Exception:
                pass

    # 5. Use defaults if still not found
    if not project_name:
        project_name = "project_name"
        print(
            "Warning: Could not detect project_name, using default placeholder"
        )

    if not user_name:
        user_name = "user_name"
        print("Warning: Could not detect user_name, using default placeholder")

    print(f"Final detection - Project: {project_name}, User: {user_name}")
    return project_name, user_name


# Helper function to auto-detect default filename
def get_default_filename(existing_path=None, all_savers=None):
    """Auto-detect default filename from multiple sources.
    Priority:
    1. Extract from existing saver path
    2. Extract from other saver nodes in comp
    3. Extract from comp filename
    4. Environment variable (DAILY_FILENAME)
    5. Default: "daily_h264"
    
    Returns: default filename (without extension)
    """
    default_filename = None

    # 1. Try to extract from existing path
    if existing_path:
        try:
            _, file_name, _ = parse_file_path(existing_path)
            # Remove number suffix if exists (e.g., "daily_h264_001" -> "daily_h264")
            number_match = re.search(r'_(\d+)$', file_name)
            if number_match:
                default_filename = file_name[:number_match.start()]
            else:
                default_filename = file_name
            if default_filename:
                print(
                    f"Extracted filename from existing path: {default_filename}"
                )
                return default_filename
        except Exception:
            pass

    # 2. Try to extract from other saver nodes
    if all_savers and not default_filename:
        for saver in all_savers:
            try:
                saver_path_attr = saver.GetAttrs("TOOLST_Clip_Name")
                saver_path = saver_path_attr[1] if saver_path_attr else ""
                if saver_path and saver_path != existing_path:
                    _, file_name, _ = parse_file_path(saver_path)
                    # Remove number suffix if exists
                    number_match = re.search(r'_(\d+)$', file_name)
                    if number_match:
                        default_filename = file_name[:number_match.start()]
                    else:
                        default_filename = file_name
                    if default_filename:
                        print(
                            f"Extracted filename from other saver: {default_filename}"
                        )
                        return default_filename
            except Exception:
                continue

    # 3. Try to extract from comp filename
    if not default_filename:
        try:
            comp_path = comp.GetAttrs("COMPN_FileName")
            if comp_path:
                comp_name = os.path.splitext(os.path.basename(comp_path))[0]
                # Use comp name as filename (remove common suffixes)
                comp_name = re.sub(r'(_v\d+|_comp|_scene)$',
                                   '',
                                   comp_name,
                                   flags=re.IGNORECASE)
                if comp_name:
                    default_filename = comp_name
                    print(
                        f"Extracted filename from comp name: {default_filename}"
                    )
                    return default_filename
        except Exception as e:
            print(f"Could not extract from comp filename: {str(e)}")

    # 4. Try environment variable
    if not default_filename:
        default_filename = os.getenv('DAILY_FILENAME') or os.getenv(
            'DAILY_H264_FILENAME')
        if default_filename:
            print(
                f"Using filename from environment variable: {default_filename}"
            )
            return default_filename

    # 5. Use default
    if not default_filename:
        default_filename = "daily_h264"
        print(f"Using default filename: {default_filename}")

    return default_filename


# Helper function to parse and validate file path
def parse_file_path(path):
    """Parse file path and return (dir, name, ext). Validate extension."""
    path = path.replace('/', os.sep)
    file_dir = os.path.dirname(path)
    file_name, file_ext = os.path.splitext(os.path.basename(path))
    file_ext = file_ext.lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        if path:  # Existing path - warn and default
            print(
                f"Warning: Invalid file extension {file_ext}. Defaulting to .mov"
            )
            file_ext = '.mov'
        else:  # New path - error
            raise ValueError(
                f"Invalid file extension: {file_ext}. Only .mov and .mp4 are allowed."
            )

    return file_dir, file_name, file_ext


# Find or create saver node
all_savers = comp.GetToolList(False, "Saver").values()
existing_saver = next(
    (s for s in all_savers if s.GetAttrs("TOOLS_Name") == saver_name), None)

if existing_saver is None:
    comp.Lock()
    new_saver = comp.AddTool("Saver", -1, -1)
    new_saver.SetAttrs({"TOOLS_Name": saver_name})

    # Connect to MediaOut or selected tool
    media_outs = comp.GetToolList(False, "MediaOut").values()
    if media_outs:
        new_saver.Input.ConnectTo(list(media_outs)[0].Output)
    else:
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
current_path = current_path_attr[1] if current_path_attr else ""

# Auto-detect project_name and user_name
project_name, user_name = get_project_and_user_names(current_path)

# Auto-detect default filename
default_filename = get_default_filename(current_path, all_savers)

# Parse path or ask user for input
if current_path:
    file_dir, file_name, file_ext = parse_file_path(current_path)
else:
    default_path = f"R:\\{project_name}\\{today_date}\\{user_name}\\{default_filename}.mov"
    user_input = comp.AskUser(
        "Daily H264 Saver - Enter File Path",
        {"FilePath": {
            "Name": "File Path",
            "Text": default_path
        }})

    if not user_input:
        print("User cancelled file path input.")
        comp.EndUndo(True)
        raise SystemExit("User cancelled operation.")

    current_path = user_input.get("FilePath", default_path)
    # Re-detect project_name and user_name from user input
    project_name, user_name = get_project_and_user_names(current_path)
    try:
        file_dir, file_name, file_ext = parse_file_path(current_path)
    except ValueError as e:
        comp.EndUndo(True)
        raise

# Update path to today's date folder and ensure project_name/user_name are present
if file_dir:
    normalized_dir = file_dir.replace('/', os.sep).replace('\\', os.sep)
    path_parts = [p for p in normalized_dir.split(os.sep) if p]

    # Find date folder index (format: YYMMDD)
    date_folder_index = next(
        (i for i, p in enumerate(path_parts) if re.match(r'^\d{6}$', p)), -1)

    # Ensure project_name exists before date folder
    if date_folder_index > 0:
        # Check if project_name is already in path
        if path_parts[date_folder_index - 1] != project_name:
            path_parts[date_folder_index - 1] = project_name
    elif date_folder_index == -1:
        # No date folder found, insert project_name before date
        # Find a good insertion point (after drive letter or root)
        insert_index = 1 if path_parts and len(
            path_parts[0]) == 2 and path_parts[0][1] == ':' else 0
        path_parts.insert(insert_index, project_name)
        date_folder_index = insert_index + 1
    else:
        # date_folder_index == 0 (shouldn't happen, but handle it)
        path_parts.insert(0, project_name)
        date_folder_index = 1

    # Update or insert date folder
    if date_folder_index < len(path_parts):
        path_parts[date_folder_index] = today_date
    else:
        path_parts.append(today_date)
        date_folder_index = len(path_parts) - 1

    # Ensure user_name exists after date folder
    if date_folder_index + 1 < len(path_parts):
        if path_parts[date_folder_index + 1] != user_name:
            path_parts[date_folder_index + 1] = user_name
    else:
        path_parts.append(user_name)

    # Reconstruct path (handle Windows drive letter)
    if path_parts and len(path_parts[0]) == 2 and path_parts[0][1] == ':':
        file_dir = path_parts[0] + os.sep + os.sep.join(path_parts[1:])
    else:
        file_dir = os.sep.join(path_parts)
else:
    # Use auto-detected project_name and user_name
    file_dir = os.path.join("R:", project_name, today_date, user_name)

# Ensure directory exists
try:
    mapped_dir = comp.MapPath(file_dir)
    os.makedirs(mapped_dir, exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create directory {file_dir}: {str(e)}")

# Find next available file number
number_match = re.search(r'_(\d+)$', file_name)
base_name = file_name[:number_match.start()] if number_match else file_name
start_number = int(number_match.group(1)) if number_match else 0

# Check if current file exists
current_file_path = os.path.join(file_dir, f"{file_name}{file_ext}")
file_exists = os.path.exists(comp.MapPath(current_file_path))
search_start = start_number + 1 if file_exists else start_number

# Find next available filename
final_path = ""
for i in range(search_start, 1000):
    test_name = base_name if i == 0 else f"{base_name}_{i:03d}"
    test_path = os.path.join(file_dir, f"{test_name}{file_ext}")

    if not os.path.exists(comp.MapPath(test_path)):
        final_path = test_path
        break

if not final_path:
    final_path = os.path.join(
        file_dir, f"{base_name}{file_ext}"
        if search_start == 0 else f"{base_name}_{search_start:03d}{file_ext}")

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

# Ask user for render confirmation
print("=" * 60)
print("Daily H264 Saver - Starting render")
print(f"Output file: {final_path}")
print("=" * 60)

dialog_result = comp.AskUser(
    "Daily H264 Saver - Render Confirmation",
    {"Render": {
        "Name": "Render now?",
        "Default": 1,
        "Checkbox": True
    }})

# Parse dialog result (Checkbox returns 1 for checked, 0 for unchecked)
should_render = False
if dialog_result is None or dialog_result is False:
    print("User clicked Cancel - skipping render")
elif isinstance(dialog_result, dict):
    render_value = dialog_result.get("Render") or dialog_result.get("render")
    if render_value is None:
        # Case-insensitive search
        render_value = next(
            (v for k, v in dialog_result.items() if k.lower() == "render"),
            None)

    if render_value is not None:
        if isinstance(render_value, bool):
            should_render = render_value
        elif isinstance(render_value, (int, float)):
            should_render = (render_value == 1)
        else:
            should_render = str(render_value).strip().lower() in [
                "1", "true", "yes", "y"
            ]
    else:
        should_render = True  # Default to True if checkbox was checked
elif isinstance(dialog_result, bool):
    should_render = dialog_result
elif isinstance(dialog_result, (int, float)):
    should_render = (dialog_result == 1)

# Render if user confirmed
if should_render:
    print("Starting local render...")
    comp.Lock()
    try:
        start_frame = comp.GetAttrs("COMPN_RenderStart")
        end_frame = comp.GetAttrs("COMPN_RenderEnd")
        print(f"Render range: {start_frame} to {end_frame}")

        comp.Render({"Tool": existing_saver, "Wait": True})
        print(f"Render completed: {final_path}")
    except Exception as e:
        error_msg = str(e).lower()
        if any(x in error_msg for x in ["cancel", "abort", "user"]):
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
