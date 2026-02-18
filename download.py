import os
import threading
import customtkinter as ctk
from huggingface_hub import hf_hub_download

class ModelDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Neptunium - Model Manager")
        self.geometry("620x550")
        ctk.set_appearance_mode("dark")

        # Models optimized for 8GB RAM
        self.models = [
            {"name": "Llama-3.2-3B (Balanced)", "repo": "bartowski/Llama-3.2-3B-Instruct-GGUF", "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf"},
            {"name": "Llama-3.2-1B (Ultra Fast)", "repo": "bartowski/Llama-3.2-1B-Instruct-GGUF", "file": "Llama-3.2-1B-Instruct-Q4_K_M.gguf"},
            {"name": "Qwen-2.5-Coder-1.5B", "repo": "Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF", "file": "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"},
            {"name": "Phi-3.5-Mini (Logic)", "repo": "lm-kit/phi-3.5-mini-3.8b-instruct-gguf", "file": "Phi-3.5-mini-Instruct-Q4_K_M.gguf"},
            {"name": "Moondream2 (Vision)", "repo": "vikhyatk/moondream2", "file": "moondream2.gguf"}
        ]

        # UI Components
        ctk.CTkLabel(self, text="Neptunium Model Manager", font=("Impact", 24)).pack(pady=20)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=580, height=320)
        self.scroll_frame.pack(pady=10, padx=20)

        self.buttons = {} # Store buttons to update them after download
        self.render_model_list()

        self.status_label = ctk.CTkLabel(self, text="Ready", font=("Arial", 12))
        self.status_label.pack(pady=(10, 0))

        self.progress_bar = ctk.CTkProgressBar(self, width=500)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=20)

    def render_model_list(self):
        """Clears and rebuilds the list to show current file status"""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        for model in self.models:
            file_exists = os.path.exists(model["file"])
            
            frame = ctk.CTkFrame(self.scroll_frame)
            frame.pack(fill="x", pady=5, padx=5)
            
            label_text = f"{model['name']}\n({model['file']})"
            ctk.CTkLabel(frame, text=label_text, font=("Arial", 11), justify="left").pack(side="left", padx=10, pady=5)
            
            # Change button appearance if model exists
            btn_text = "Installed ✅" if file_exists else "Download"
            btn_state = "disabled" if file_exists else "normal"
            btn_color = "#2e7d32" if file_exists else "#1f6aa5"

            btn = ctk.CTkButton(
                frame, 
                text=btn_text, 
                width=110,
                state=btn_state,
                fg_color=btn_color,
                command=lambda m=model: self.start_download(m)
            )
            btn.pack(side="right", padx=10)
            self.buttons[model["file"]] = btn

    def start_download(self, model_data):
        self.status_label.configure(text=f"Downloading {model_data['file']}...", text_color="white")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        
        thread = threading.Thread(target=self.download_engine, args=(model_data,))
        thread.daemon = True
        thread.start()

    def download_engine(self, model_data):
        try:
            # hf_hub_download handles the download and returns the local path
            hf_hub_download(
                repo_id=model_data["repo"],
                filename=model_data["file"],
                local_dir=".", 
                local_dir_use_symlinks=False
            )
            
            # Update UI on completion
            self.after(0, self.on_download_complete, model_data)
            
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"Error: {str(e)}", text_color="red"))
            self.after(0, self.progress_bar.stop)

    def on_download_complete(self, model_data):
        self.progress_bar.stop()
        self.progress_bar.set(1.0)
        self.status_label.configure(text=f"Success! {model_data['name']} is ready.", text_color="#4CAF50")
        
        # Update the button specifically for this model
        btn = self.buttons.get(model_data["file"])
        if btn:
            btn.configure(text="Installed ✅", state="disabled", fg_color="#2e7d32")

if __name__ == "__main__":
    app = ModelDownloader()
    app.mainloop()