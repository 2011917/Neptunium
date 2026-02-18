import os
import sys
import threading
import psutil
import platform
import customtkinter as ctk
from tkinter import filedialog
from llama_cpp import Llama
import fitz  # PyMuPDF
from PIL import Image

class HardwareEngine:
    """Detects system specs and recommends LLM parameters"""
    @staticmethod
    def get_specs():
        ram_gb = round(psutil.virtual_memory().total / (1024**3))
        cores = os.cpu_count()
        is_mac = platform.system() == "Darwin"
        is_arm = "arm" in platform.machine().lower()
        
        # Adjust logic based on RAM
        if ram_gb <= 8:
            ctx_limit = 2048  # Low RAM: keep context small
            offload = 10 if not is_mac else -1 # Partial offload for low-end
        elif ram_gb <= 16:
            ctx_limit = 4096
            offload = -1 # Try full offload
        else:
            ctx_limit = 8192 # High-end
            offload = -1

        return {
            "ram": ram_gb,
            "cores": max(cores - 2, 1), # Leave some cores for the OS
            "ctx": ctx_limit,
            "offload": offload,
            "desc": f"{platform.system()} | {ram_gb}GB RAM | {cores} Cores"
        }

class ChatMessage(ctk.CTkFrame):
    def __init__(self, master, role, text, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        is_user = role == "user"
        bg_color = "#2b5ff1" if is_user else "#333333"
        
        self.textbox = ctk.CTkTextbox(
            self, width=550, fg_color=bg_color, text_color="white",
            font=("Segoe UI", 13), corner_radius=12, wrap="word",
            padx=12, pady=12, border_width=0
        )
        self.textbox.insert("0.0", text)
        self.textbox.configure(state="disabled")
        self.textbox.pack(side="right" if is_user else "left", padx=10, pady=5)
        self.update_height()

    def update_height(self):
        self.update_idletasks()
        content = self.textbox.get("0.0", "end")
        lines = content.count("\n") + (len(content) // 65) + 1
        self.textbox.configure(height=min(max(lines * 22, 45), 800))

class NeptuniumAI(ctk.CTk):
    def __init__(self):
        super().__init__()

        def load_model(llm_path="Llama-3.2-3B-Instruct-Q4_K_M.gguf"):
            try:
                self.llm = Llama(
                    model_path=model_name,
                    n_gpu_layers=self.specs["offload"],
                    n_threads=self.specs["cores"],
                    n_ctx=self.specs["ctx"],
                    flash_attn=True,
                    verbose=False
                )
            except Exception as e: print(f"Load error: {e}")
            self.after(0, lambda: self.submit_btn.configure(state="normal", text="Send"))
        threading.Thread(target=load, daemon=True).start()

    def upload_handler(self):
        path = filedialog.askopenfilename(filetypes=[("All Files", "*.txt *.pdf *.png *.jpg")])
        if not path: return
        ext = os.path.splitext(path)[1].lower()
        if ext in [".png", ".jpg", ".jpeg"]:
            self.current_context = f"\n[User Image: {os.path.basename(path)}]\n"
            self.file_status.configure(text=f"Image Linked", text_color="#3498db")
        elif ext == ".pdf":
            text = "".join([p.get_text() for p in fitz.open(path)])
            self.current_context = f"\n[Document: {text[:self.specs['ctx']]}]\n"
            self.file_status.configure(text="PDF Context Active", text_color="#4CAF50")
        else:
            with open(path, "r", encoding="utf-8") as f:
                self.current_context = f"\n[Text Data: {f.read()[:self.specs['ctx']]}]\n"
            self.file_status.configure(text="Text Context Active", text_color="#4CAF50")

    def add_message(self, role, text):
        msg = ChatMessage(self.chat_container, role, text)
        msg.pack(fill="x", padx=15, pady=8)
        self.messages.append(msg)
        self.after(50, lambda: self.chat_container._parent_canvas.yview_moveto(1.0))
        return msg

    def start_generation(self):
        query = self.input_box.get().strip()
        if not query or not self.llm: return
        self.add_message("user", query)
        self.input_box.delete(0, "end")
        self.submit_btn.configure(state="disabled")
        prompt = self.current_context + query
        self.history.append({"role": "user", "content": prompt})
        self.current_context = "" 
        threading.Thread(target=self.generate_response, daemon=True).start()

    def generate_response(self):
        ai_msg = self.add_message("assistant", "Thinking...")
        full_txt = ""
        try:
            stream = self.llm.create_chat_completion(messages=self.history, stream=True)
            for chunk in stream:
                if "content" in chunk["choices"][0]["delta"]:
                    token = chunk["choices"][0]["delta"]["content"]
                    full_txt += token
                    self.after(0, lambda t=full_txt: self.update_ai_bubble(ai_msg, t))
            self.history.append({"role": "assistant", "content": full_txt})
        except Exception as e:
            self.after(0, lambda: ai_msg.textbox.configure(state="normal"))
            self.after(0, lambda: ai_msg.textbox.insert("end", f"\nError: {e}"))
        self.after(0, lambda: self.submit_btn.configure(state="normal"))

    def update_ai_bubble(self, msg_obj, text):
        msg_obj.textbox.configure(state="normal")
        msg_obj.textbox.delete("0.0", "end")
        msg_obj.textbox.insert("0.0", text)
        msg_obj.textbox.configure(state="disabled")
        msg_obj.update_height()

    def refresh_models(self):
        files = [f for f in os.listdir(".") if f.endswith(".gguf")]
        if files:
            self.model_dropdown.configure(values=files)
            self.model_dropdown.set(files[0])
            self.switch_model(files[0])

if __name__ == "__main__":
    app = NeptuniumAI()
    app.mainloop()