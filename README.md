Neptunium: The UI for AI
Neptunium is a lightweight, modern desktop interface for running Large Language Models (LLMs) locally on Windows. It uses customtkinter for a sleek UI and llama-cpp-python as the high-performance inference engine.

🚀 Features
Local Inference: Runs completely offline for privacy and speed.

Model Switching: Easily swap between Llama-3.2 (1B/3B) and Qwen2.5-Coder.

Streaming Responses: Real-time text generation.

Modern UI: Dark-themed, responsive interface built with CustomTkinter.

🛠️ Installation
1. Clone the Repository
PowerShell
git clone https://github.com/2011917/ai-no-2.git
cd Neptunium
2. Set Up a Virtual Environment
PowerShell
python -m venv .venv
.\.venv\Scripts\activate
3. Install Dependencies
PowerShell
pip install llama-cpp-python customtkinter tkhtmlview markdown2 huggingface_hub
Note: If you have an NVIDIA GPU, follow the specific llama-cpp-python installation guide to enable CUDA support.

📥 Downloading Models
This repository does not store model files (.gguf) because they are too large for GitHub. We have provided a dedicated script to handle this for you.

Run the downloader script:

PowerShell
python download.py
Choose your model: Follow the menu prompts to download Llama 3.2 or Qwen.

Automatic Setup: The script will place the model directly in the project folder so Neptunium.py can find it instantly.

🖥️ Usage
Run the application using Python:

PowerShell
python Neptunium.py
Select your desired model from the dropdown menu.

Type your prompt in the input box.

Press Enter or click Submit.

⚠️ Important Note on Large Files
This project uses a .gitignore to prevent massive binary files (like .gguf, .dll, and .lib) from being pushed to GitHub. Always ensure your models are stored locally and not committed to the repository history.