import os
import threading
import psutil
import platform
import customtkinter as ctk
from tkinter import filedialog
from llama_cpp import Llama
import fitz  # PyMuPDF

class HardwareEngine:
    @staticmethod
    def get_specs():
        ram_gb = round(psutil.virtual_memory().total / (1024**3))
        cores = os.cpu_count() or 4
        is_mac = platform.system() == "Darwin"
        
        # Heuristic for local LLM settings
        ctx_limit = 4096 if ram_gb > 8 else 2048
        offload = -1 if ram_gb > 12 else 0 # -1 uses all GPU layers if available
        
        return {
            "ram": ram_gb,
            "cores": max(cores - 2, 1),
            "ctx": ctx_limit,
            "offload": offload,
            "desc": f"{platform.system()} | {ram_gb}GB RAM"
        }

class ChatMessage(ctk.CTkFrame):
    def __init__(self, master, role, text, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        is_user = role == "user"
        bg_color = "#2b5ff1" if is_user else "#333333"
        
        self.textbox = ctk.CTkTextbox(
            self, width=500, fg_color=bg_color, text_color="white",
            font=("Segoe UI", 13), corner_radius=15, wrap="word", padx=10, pady=10
        )
        self.textbox.insert("0.0", text)
        self.textbox.configure(state="disabled")
        self.textbox.pack(side="right" if is_user else "left", padx=10, pady=5)
        self.update_height()

    def update_height(self):
        text = self.textbox.get("0.0", "end")
        lines = text.count("\n") + (len(text) // 60) + 1
        self.textbox.configure(height=min(max(lines * 22, 45), 600))

class NeptuniumAI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Neptunium AI")
        self.geometry("900x750")
        
        self.specs = HardwareEngine.get_specs()
        self.history = []
        self.pending_context = ""
        self.llm = None

        # --- Top Bar (Model Selection) ---
        self.top_bar = ctk.CTkFrame(self, height=50, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=20, pady=10)
        
        self.model_label = ctk.CTkLabel(self.top_bar, text="Model:", font=("Segoe UI", 12, "bold"))
        self.model_label.pack(side="left", padx=(0, 10))
        
        self.model_dropdown = ctk.CTkOptionMenu(self.top_bar, values=["Scanning..."], command=self.switch_model)
        self.model_dropdown.pack(side="left")
        
        self.status_indicator = ctk.CTkLabel(self.top_bar, text="● Offline", text_color="gray")
        self.status_indicator.pack(side="right")

        # --- Chat Area ---
        self.chat_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.chat_container.pack(fill="both", expand=True, padx=20, pady=10)

        # --- Attachment Preview ---
        self.file_pill = ctk.CTkLabel(self, text="", text_color="#3498db", font=("Segoe UI", 11, "italic"))
        self.file_pill.pack(pady=0)

        # --- Input Bar (Gemini Style) ---
        self.input_container = ctk.CTkFrame(self, corner_radius=25, fg_color="#252525", border_width=1, border_color="#444")
        self.input_container.pack(fill="x", padx=30, pady=(0, 20))

        self.attach_btn = ctk.CTkButton(self.input_container, text="+", width=40, height=40, 
                                       corner_radius=20, fg_color="#333", hover_color="#444", 
                                       command=self.upload_handler)
        self.attach_btn.pack(side="left", padx=10, pady=5)

        self.input_box = ctk.CTkEntry(self.input_container, placeholder_text="Ask anything...", 
                                     border_width=0, fg_color="transparent", height=40)
        self.input_box.pack(side="left", fill="x", expand=True, padx=5)
        self.input_box.bind("<Return>", lambda e: self.start_generation())

        self.submit_btn = ctk.CTkButton(self.input_container, text="Send", width=80, height=34, 
                                       corner_radius=17, command=self.start_generation, state="disabled")
        self.submit_btn.pack(side="right", padx=10)

        # Initialize
        self.refresh_models()

    def refresh_models(self):
        models = [f for f in os.listdir(".") if f.endswith(".gguf")]
        if not models:
            self.model_dropdown.configure(values=["No .gguf files found"])
        else:
            self.model_dropdown.configure(values=models)
            self.model_dropdown.set(models[0])
            self.switch_model(models[0])

    def switch_model(self, model_name):
        self.status_indicator.configure(text="○ Loading...", text_color="yellow")
        self.submit_btn.configure(state="disabled")
        threading.Thread(target=self._load_engine, args=(model_name,), daemon=True).start()

    def _load_engine(self, model_name):
        try:
            # Clean up old model if exists
            if self.llm: del self.llm
            
            self.llm = Llama(
                model_path=model_name,
                n_gpu_layers=self.specs["offload"],
                n_threads=self.specs["cores"],
                n_ctx=self.specs["ctx"],
                verbose=False
            )
            self.after(0, lambda: self.status_indicator.configure(text="● Ready", text_color="#4CAF50"))
            self.after(0, lambda: self.submit_btn.configure(state="normal"))
        except Exception as e:
            self.after(0, lambda: self.status_indicator.configure(text="● Error", text_color="red"))
            print(f"Engine Error: {e}")

    def upload_handler(self):
        path = filedialog.askopenfilename(filetypes=[("Documents", "*.txt *.pdf")])
        if not path: return
        
        ext = os.path.splitext(path)[1].lower()
        filename = os.path.basename(path)
        
        try:
            if ext == ".pdf":
                doc = fitz.open(path)
                content = "\n".join([page.get_text() for page in doc])
            else:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

            # Limit context to avoid crashing small models
            char_limit = self.specs["ctx"] * 3 
            self.pending_context = f"\n[Document Content: {filename}]\n{content[:char_limit]}\n[End of Document]\n"
            self.file_pill.configure(text=f"📎 {filename} attached")
        except Exception as e:
            self.file_pill.configure(text=f"❌ Error loading file: {e}")

    def start_generation(self):
        query = self.input_box.get().strip()
        if not query or not self.llm: return
        
        self.add_message("user", query)
        self.input_box.delete(0, "end")
        self.submit_btn.configure(state="disabled")
        
        # Inject file context if it exists
        full_prompt = f"{self.pending_context}\nQuestion: {query}" if self.pending_context else query
        self.history.append({"role": "user", "content": full_prompt})
        
        # Clear UI file indicator and internal buffer
        self.pending_context = ""
        self.file_pill.configure(text="")
        
        threading.Thread(target=self.generate_response, daemon=True).start()

    def generate_response(self):
        ai_msg = self.add_message("assistant", "...")
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
            self.after(0, lambda: self.update_ai_bubble(ai_msg, f"Generation Error: {e}"))
        
        self.after(0, lambda: self.submit_btn.configure(state="normal"))

    def add_message(self, role, text):
        msg = ChatMessage(self.chat_container, role, text)
        msg.pack(fill="x", padx=5, pady=5)
        self.after(100, lambda: self.chat_container._parent_canvas.yview_moveto(1.0))
        return msg

    def update_ai_bubble(self, msg_obj, text):
        msg_obj.textbox.configure(state="normal")
        msg_obj.textbox.delete("0.0", "end")
        msg_obj.textbox.insert("0.0", text)
        msg_obj.textbox.configure(state="disabled")
        msg_obj.update_height()

if __name__ == "__main__":
    app = NeptuniumAI()
    app.mainloop()