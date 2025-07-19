import os
from file_info import File, get_disassembly, get_strings # Renamed for consistency
from utils.file_utils import should_collect, is_executable_file # Renamed and moved
from log_config.logger_config import logger # Import logger
from config import EXCLUDE_DIRS

def read_directory_recursively(root_dir, max_size_bytes):
    all_files = []
    layout_lines = []

    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=True):
        # Exclude specified directories from traversal
        dirnames[:] = [d for d in dirnames if os.path.join(dirpath, d) + os.sep not in EXCLUDE_DIRS]

        rel_dir = os.path.relpath(dirpath, root_dir)
        indent_level = 0 if rel_dir == '.' else rel_dir.count(os.sep) + 1
        indent = '│   ' * (indent_level - 1) if indent_level > 0 else ''
        layout_lines.append(f"{indent}├── {os.path.basename(dirpath)}/")

        subindent = '│   ' * indent_level
        for filename in filenames:
            file_full_path = os.path.join(dirpath, filename)
            layout_lines.append(f"{subindent}├── {filename}")

            if os.path.isfile(file_full_path) and not os.path.islink(file_full_path):
                f = File(file_full_path, root_dir)
                if should_collect(f, max_size_bytes):
                    all_files.append(f)
                else:
                    logger.debug(f"Skipping file: {f.name} (size too large or excluded)")

    return all_files, "\n".join(layout_lines)

def collect_file_contents(files):
    file_dict = {}

    # Flatten the list if it contains sublists
    flat_files = []
    for item in files:
        if isinstance(item, list):
            flat_files.extend(item)
        else:
            flat_files.append(item)

    for f in flat_files:
        try:
            if f.kind == "text":
                with open(f.path, "r", encoding="utf-8", errors="replace") as fp:
                    content = fp.read()
            elif is_executable_file(f): # Use the new utility function
                disassembly = get_disassembly(f.path) # Renamed
                strings = get_strings(f.path) # Renamed
                content = f"--- Disassembly ---\n{disassembly}\n\n--- Strings ---\n{strings}"
            else:
                content = "[Binary file without disassembly]"
        except Exception as e:
            content = f"[Error reading file: {e}]"
            logger.error(f"Failed to collect content for {getattr(f, 'name', str(f))}: {e}")

        file_dict[f] = content

    return file_dict