import io
import os

import imageio_ffmpeg
import subprocess

from PIL import Image

from src.ffmpeg_extractor.tools import create_snaps_folder
from src.options import SNAPS_FOLDER
from src.utils import extract_file_name


def extract_frames_to_folder(filename: str, frame_width: int, frame_height: int) -> str:
    folder_name = extract_file_name(filename)
    folder_path = os.path.join(SNAPS_FOLDER, folder_name)
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
        ffmpeg_make_extraction_to_folder(filename, frame_width, frame_height)

    return folder_path


def ffmpeg_make_extraction_to_folder(video_path: str, width: int, height: int):
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    video_name = extract_file_name(video_path)
    create_snaps_folder(video_name)
    min_time_step = width / 100

    command = [
        ffmpeg_path,
        "-i", video_path,
        "-vf", f"fps=1/{min_time_step}",
        "-s", f"{width}x{height}",
        "-vcodec", "png",
        f"snaps/{video_name}/{video_name}%03d.png"
    ]
    subprocess.run(command)


def extract_frames_from_pipe(video_path: str, time_step: float, width: int, height: int):
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    command = [
        ffmpeg_path,
        "-i", video_path,
        "-vf", f"fps=1/{time_step}",
        "-s", f"{width}x{height}",
        "-f", "image2pipe",
        "-vcodec", "png",
        "-"]

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    buffer = b''
    start_marker = b'\x89PNG\r\n\x1a\n'
    end_marker = b'IEND\xaeB`\x82'
    chunk_size = 8192 * 8

    while True:
        try:
            chunk = proc.stdout.read(chunk_size)
            if not chunk:
                break

            buffer += chunk

            while True:
                start_idx = buffer.find(start_marker)
                if start_idx == -1:
                    break

                end_idx = buffer.find(end_marker)
                if end_idx == -1:
                    break

                img_data_bytes = buffer[start_idx:end_idx + 8]
                buffer = buffer[end_idx + 8:]
                img = Image.open(io.BytesIO(img_data_bytes))
                yield img

        except Exception as e:
            print(e)

    proc.terminate()