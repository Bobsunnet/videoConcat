from os import path


def extract_file_name(file_path: str) -> str:
    """ Extracts the name of file without extension
    Args:
        file_path (str): The path to the file.
    Returns:
        str: The name of the file without extension."""
    return path.split(file_path)[-1].rpartition(".")[0]

