from pathlib import Path
import os
import urllib.request

# If you want the official Ultralytics YOLO11n checkpoint, use this URL.
# For a custom VisDrone-trained model, replace this URL with the actual download link.
MODEL_URL = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov11n.pt"
MODEL_NAME = "yolov11n_visdrone_model.pt"


def download_model(target_dir: str = ".") -> str:
    folder = Path(target_dir).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    save_path = folder / MODEL_NAME

    if save_path.exists():
        print(f"Model already exists: {save_path}")
        return str(save_path)

    print(f"Downloading model from: {MODEL_URL}")
    urllib.request.urlretrieve(MODEL_URL, str(save_path))
    print(f"Model saved to: {save_path}")
    return str(save_path)


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = download_model(current_dir)
    print(f"Use this file in your project: {model_path}")
