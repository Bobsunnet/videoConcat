from os import path, mkdir


def create_snaps_folder(video_name: str):
    if not path.exists(f"snaps/{video_name}"):
        mkdir(f"snaps/{video_name}")
