import sys
import base64
import json
import urllib.request
import os
import subprocess
import tempfile
import glob


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:31b-cloud"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def describe_image(image_path: str, prompt: str = "Describe this image in detail.") -> str:
    image_b64 = encode_image(image_path)

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["response"]


def extract_frames(video_path: str, num_frames: int = 4) -> list[str]:
    """Use ffmpeg to extract evenly spaced frames from a video."""
    tmpdir = tempfile.mkdtemp(prefix="describe_")

    # Get video duration
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
        capture_output=True, text=True,
    )
    duration = float(json.loads(result.stdout)["format"]["duration"])
    interval = duration / (num_frames + 1)

    frame_paths = []
    for i in range(1, num_frames + 1):
        timestamp = interval * i
        out_path = os.path.join(tmpdir, f"frame_{i:03d}.jpg")
        subprocess.run(
            ["ffmpeg", "-ss", str(timestamp), "-i", video_path,
             "-frames:v", "1", "-q:v", "2", out_path, "-y"],
            capture_output=True,
        )
        if os.path.isfile(out_path):
            frame_paths.append(out_path)

    return frame_paths


def get_file_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


def main():
    if len(sys.argv) < 2:
        print("Usage: python describe.py <image_or_video> [prompt]")
        print()
        print("Images: Describes the image directly")
        print("Videos:  Extracts frames with ffmpeg, then describes each")
        print()
        print("Examples:")
        print("  python describe.py photo.jpg")
        print('  python describe.py photo.jpg "What objects are in this image?"')
        print("  python describe.py video.mp4")
        print(f'  python describe.py video.mp4 "Summarize what happens in this video"')
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    prompt = sys.argv[2] if len(sys.argv) > 2 else None
    file_type = get_file_type(file_path)

    print(f"Using model: {MODEL}")

    if file_type == "image":
        prompt = prompt or "Describe this image in detail."
        print(f"Analyzing image: {file_path}")
        print("Processing...\n")
        print(describe_image(file_path, prompt))

    elif file_type == "video":
        prompt = prompt or "Describe what you see in this video frame in detail."
        print(f"Analyzing video: {file_path}")
        print("Extracting frames with ffmpeg...\n")

        frames = extract_frames(file_path)
        if not frames:
            print("Error: Could not extract any frames from the video.")
            sys.exit(1)

        print(f"Extracted {len(frames)} frames\n")

        all_descriptions = []
        for i, frame in enumerate(frames, 1):
            print(f"--- Frame {i}/{len(frames)} ---")
            desc = describe_image(frame, prompt)
            print(desc)
            print()
            all_descriptions.append(desc)
            os.remove(frame)

        # Generate overall summary
        summary_prompt = (
            "Based on these frame descriptions from a video, provide a cohesive summary "
            "of what the video shows:\n\n"
            + "\n\n".join(f"Frame {i}: {d}" for i, d in enumerate(all_descriptions, 1))
        )
        print("--- Overall Video Summary ---")
        payload = {
            "model": MODEL,
            "prompt": summary_prompt,
            "stream": False,
        }
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(result["response"])

    else:
        print(f"Error: Unsupported file type: {os.path.splitext(file_path)[1]}")
        print(f"Supported images: {', '.join(sorted(IMAGE_EXTENSIONS))}")
        print(f"Supported videos: {', '.join(sorted(VIDEO_EXTENSIONS))}")
        sys.exit(1)


if __name__ == "__main__":
    main()
