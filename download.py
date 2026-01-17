from huggingface_hub import hf_hub_download
import os

def download_model(repo_id, filename):
    print(f"\n--- Starting download for {filename} ---")
    try:
        path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=".",
            local_dir_use_symlinks=False
        )
        print(f"Successfully downloaded to: {os.path.abspath(path)}")
    except Exception as e:
        print(f"Error downloading {filename}: {e}")

if __name__ == "__main__":
    # List of models your UI supports
    models = [
        {"repo": "Bartowski/Llama-3.2-3B-Instruct-GGUF", "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf"},
        {"repo": "Bartowski/Llama-3.2-1B-Instruct-GGUF", "file": "Llama-3.2-1B-Instruct-Q4_K_M.gguf"},
        {"repo": "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF", "file": "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf"}
    ]

    print("Neptunium Model Downloader")
    print("==========================")
    for i, m in enumerate(models):
        print(f"[{i}] {m['file']}")

    choice = input("\nEnter the number of the model to download (or 'all'): ")

    if choice.lower() == 'all':
        for m in models:
            download_model(m['repo'], m['file'])
    elif choice.isdigit() and int(choice) < len(models):
        m = models[int(choice)]
        download_model(m['repo'], m['file'])
    else:
        print("Invalid choice. Exiting.")