import os
from google.genai import types


def get_file_content(working_directory, file_path):
    try:
        if not os.path.abspath(file_path).startswith(os.path.abspath(working_directory)):
            return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
        
        if not os.path.isfile(file_path):
            return f'Error: File not found or is not a regular file: "{file_path}"'
        
        with open(file_path, 'r') as file:
            content = file.read()
            if len(content) > 10000:
                return content[:10000] + f'\n[...File "{file_path}" truncated at 10000 characters]'
            return content
    except OSError as e:
        return f'Error: Could not read file "{file_path}": {str(e)}'
    

schema_get_file_content = types.FunctionDeclaration(
    name="get_file_content",
    description="Get the content of a file",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The path to the file to read, relative to the working directory.",
            ),
        },
    ),
)