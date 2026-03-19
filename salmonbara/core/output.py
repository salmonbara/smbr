import os

def create_output_dir(target):

    path = f"output/{target}"
    os.makedirs(path, exist_ok=True)

    return path