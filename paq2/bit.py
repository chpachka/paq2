import subprocess
import os

def convert_mp3_to_wav(input_path, output_path):
    """Конвертирование MP3 в WAV с помощью ffmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-y", 
            "-i", input_path,
            output_path 
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Преобразование выполнено: {input_path} → {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка преобразования: {e.stdout}, {e.stderr}")

convert_mp3_to_wav("c:\project\tracks\Astral step.mp3", "C:\project\tracks\my_song.wav")
