import os

def get_files_info(working_directory, directory=None):
    if directory:
        path_to_check = os.path.join(working_directory, directory)
    else:
        path_to_check = working_directory

    abs_working_dir = os.path.abspath(working_directory)
    abs_path_to_check = os.path.abspath(path_to_check)

    if not abs_path_to_check.startswith(abs_working_dir):
        return f'Error: Cannot list "{directory}" as it is outside the permitted working directory'

    if not os.path.isdir(abs_path_to_check):
        error_dir = directory if directory is not None else working_directory
        return f'Error: "{error_dir}" is not a directory'

    result = []
    try:
        for item in os.listdir(abs_path_to_check):
            try:
                full_path = os.path.join(abs_path_to_check, item)
                is_dir = os.path.isdir(full_path)
                size = os.path.getsize(full_path)
                result.append(f"- {item}: file_size={size} bytes, is_dir={is_dir}")
            except OSError as e:
                result.append(f"Error: Could not access {item}: {str(e)}")

        return "\n".join(result)
    except OSError as e:
        return f"Error: Could not list directory contents: {str(e)}"