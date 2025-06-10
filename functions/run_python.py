import os
import subprocess

def run_python_file(working_directory, file_path):
    abs_working_dir = os.path.abspath(working_directory)
    full_path = os.path.abspath(os.path.join(abs_working_dir, file_path))

    if not full_path.startswith(abs_working_dir):
        return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'

    if not os.path.exists(full_path):
        return f'Error: File "{file_path}" not found.'

    if not file_path.endswith('.py'):
        return f'Error: "{file_path}" is not a Python file.'
    try:
        # We use full_path for the check but pass the relative file_path to the subprocess
        # because the CWD is set to working_directory.
        result = subprocess.run(['python3', file_path], cwd=working_directory, check=False, timeout=30, capture_output=True, text=True)

        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        if result.returncode != 0:
            output.append(f"Process exited with code {result.returncode}")
        if not output:
            output.append("No output produced.")

        return "\n".join(output)

    except subprocess.TimeoutExpired:
        return f'Error: Execution of "{file_path}" timed out after 30 seconds'
    except Exception as e:
        return f"Error: executing Python file: {e}"