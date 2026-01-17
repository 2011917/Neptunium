import os
import sys
import ctypes
import customtkinter as ctk
import tkinter as tk
from llama_cpp import Llama
import threading

# 1. Fix for PyInstaller DLL loading
if getattr(sys, "frozen", False):
    # Get the directory where the .exe is running
    base_path = sys._MEIPASS
    dll_dir = os.path.join(base_path, "llama_cpp", "lib")

    # Force Windows to search this folder for DLLs
    if os.path.exists(dll_dir):
        os.add_dll_directory(dll_dir)
        # Extra fix for some Windows 11 environments
        os.environ["PATH"] = dll_dir + os.pathsep + os.environ["PATH"]


history = []
stringresponce = ""


def resource_path(relative_path):
    # """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class TheUIForAI(ctk.CTk):
    def __init__(self):
        super().__init__()

        def load_model(llm_path="Llama-3.2-3B-Instruct-Q4_K_M.gguf"):
            try:
                self.llm = Llama(
                    model_path=resource_path(llm_path),
                    n_ctx=2048,  # 2048 is a sweet spot for 8GB RAM laptops
                    n_threads=4,
                    flash_attn=True,  # Significantly speeds up generation on modern CPUs
                    verbose=False,
                )
            except Exception as e:
                print(f"Error loading model: {e}")
                self.llm = None

        load_model()

        self.title("The UI for AI")
        self.geometry("600x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.label = ctk.CTkLabel(
            self,
            text="lama-3.2-3B",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.label.pack(pady=20)

        self.dropdown = ctk.CTkOptionMenu(
            self,
            values=[
                "Llama-3.2-3B-Instruct-Q4_K_M",
                "Llama-3.2-1B-Instruct-Q4_K_M",
                "qwen2.5-coder-7b-instruct-q4_k_m",
            ],
            command=lambda choice: load_model(llm_path=f"{choice}.gguf"),
        )
        self.dropdown.pack(pady=10)

        self.container = ctk.CTkFrame(self)
        self.container.pack(pady=10, padx=20, fill="both", expand=True)

        # Replace the HTMLText line with this:
        self.output_box = ctk.CTkTextbox(self.container, fg_color="#2b2b2b", text_color="white", font=("Segoe UI", 13))
        self.output_box.pack(fill="both", expand=True)
        self.output_box.configure(state="disabled") # Keep it read-only

        self.progress_bar = ctk.CTkProgressBar(
            self, orientation="horizontal", mode="indeterminate"
        )

        self.input_box = ctk.CTkEntry(
            self, placeholder_text="Enter your prompt here..."
        )
        self.input_box.pack(pady=10, padx=20, fill="x")

        self.submit_button = ctk.CTkButton(
            self, text="Submit", command=self.start_generation
        )
        self.submit_button.pack(pady=10)
        self.input_box.bind("<Return>", lambda event: self.start_generation())

    def start_generation(self):
        prompt = self.input_box.get().strip()
        if not prompt: return

        # Add headers directly to the box
        self.output_box.configure(state="normal")
        self.output_box.insert("end", f"\nUSER: {prompt}\n\nAI: ")
        self.output_box.configure(state="disabled")
        self.output_box.see("end")

        self.submit_button.configure(state="disabled")
        self.input_box.delete(0, tk.END)
        self.progress_bar.pack(pady=5, padx=20, fill="x")
        self.progress_bar.start()

        threading.Thread(target=self.generate_response, args=(prompt,), daemon=True).start()

    def generate_response(self, prompt):
        global history
        history.append({"role": "user", "content": prompt})

        if self.llm is None:
            self.after(
                0, lambda: self.update_output_box("Error: Model file not found!")
            )
            self.after(0, self.finalize_generation)
            return

        full_ai_response = ""

        try:
            # stream=True makes the model return tokens one by one
            stream = self.llm.create_chat_completion(messages=history, stream=True)

            for chunk in stream:
                if "content" in chunk["choices"][0]["delta"]:
                    token = chunk["choices"][0]["delta"]["content"]

                    full_ai_response += token

                    # Send token to the main thread to update UI

                    self.after(0, lambda t=token: self.update_output_box(t))

            history.append({"role": "assistant", "content": full_ai_response})

        except:
            self.after(
                0, lambda: self.update_output_box("\n\n[Error generating response]\n")
            )

        # Cleanup UI when done
        self.after(0, self.finalize_generation)

    def update_output_box(self, text):
        # Enable the box to add text, then disable it again
        self.output_box.configure(state="normal")
        self.output_box.insert("end", text)
        self.output_box.configure(state="disabled")
        
        # Simple auto-scroll to the bottom
        self.output_box.see("end")

    def finalize_generation(self):
        self.output_box.configure(state="normal")
        self.output_box.insert("end", "\n" + "="*40 + "\n")
        self.output_box.configure(state="disabled")
        self.output_box.see("end")

        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.submit_button.configure(state="normal")

if __name__ == "__main__":
    app = TheUIForAI()
    app.mainloop()
