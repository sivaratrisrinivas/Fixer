import os

def write_file(working_directory, file_path, content):
    full_path = os.path.abspath(os.path.join(working_directory, file_path))
    
    if not full_path.startswith(os.path.abspath(working_directory)):
        return f'Error: Cannot write to "{file_path}" as it is outside the permitted working directory'
    
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as file:
            file.write(content)
        
        return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'
    except OSError as e:
        return f'Error: Could not write to "{file_path}": {str(e)}'