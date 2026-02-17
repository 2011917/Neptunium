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
        self.specs = HardwareEngine.get_specs()
        
        self.title("Neptunium AI - Hardware Aware")
        self.geometry("1100x900")
        ctk.set_appearance_mode("dark")
        
        self.llm = None
        self.history = []
        self.messages = []
        self.current_context = ""

        # --- UI Build ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="NEPTUNIUM", font=("Impact", 28)).pack(pady=10)
        
        # Hardware Status Panel
        self.hw_panel = ctk.CTkFrame(self.sidebar, fg_color="#1a1a1a")
        self.hw_panel.pack(pady=10, padx=15, fill="x")
        ctk.CTkLabel(self.hw_panel, text=self.specs["desc"], font=("Arial", 10), text_color="#3498db").pack(pady=5)
        
        self.usage_label = ctk.CTkLabel(self.hw_panel, text="CPU: 0% | RAM: 0%", font=("Consolas", 11))
        self.usage_label.pack(pady=5)

        self.model_dropdown = ctk.CTkOptionMenu(self.sidebar, values=["Scanning..."], command=self.switch_model)
        self.model_dropdown.pack(pady=20, padx=10)

        self.upload_btn = ctk.CTkButton(self.sidebar, text="📎 Attach File/Image", command=self.upload_handler)
        self.upload_btn.pack(pady=5, padx=10)
        
        self.file_status = ctk.CTkLabel(self.sidebar, text="No context loaded", font=("Arial", 10), text_color="gray")
        self.file_status.pack()

        self.chat_container = ctk.CTkScrollableFrame(self, fg_color="#0f0f0f")
        self.chat_container.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="ew")
        
        self.input_box = ctk.CTkEntry(self.input_frame, placeholder_text="Ask me anything...", height=55)
        self.input_box.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_box.bind("<Return>", lambda e: self.start_generation())

        self.submit_btn = ctk.CTkButton(self.input_frame, text="Send", width=120, height=55, command=self.start_generation)
        self.submit_btn.pack(side="right")

        self.update_monitor()
        self.refresh_models()

    def update_monitor(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.usage_label.configure(text=f"CPU: {cpu}% | RAM: {ram}%")
        self.after(1000, self.update_monitor)

    def switch_model(self, model_name):
        def load():
            self.after(0, lambda: self.submit_btn.configure(state="disabled", text="Optimizing..."))
            if self.llm: del self.llm
            try:
                # 
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