import os
import sys
import psutil
import platform
import fitz  # PyMuPDF
from llama_cpp import Llama
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                             QFileDialog, QComboBox, QLabel, QFrame, QScrollArea)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QSize
from PySide6.QtGui import QFont, QIcon, QColor, QPalette

# --- Worker Thread for LLM ---
class LlamaWorker(QThread):
    response_received = Signal(str)
    finished_generating = Signal()

    def __init__(self, llm, messages):
        super().__init__()
        self.llm = llm
        self.messages = messages

    def run(self):
        try:
            stream = self.llm.create_chat_completion(messages=self.messages, stream=True)
            for chunk in stream:
                if "content" in chunk["choices"][0]["delta"]:
                    token = chunk["choices"][0]["delta"]["content"]
                    self.response_received.emit(token)
        except Exception as e:
            self.response_received.emit(f"\n[Error]: {e}")
        self.finished_generating.emit()

# --- Main UI ---
class NeptuniumApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neptunium AI - PySide6 Edition")
        self.resize(1000, 800)
        self.setAcceptDrops(True)
        
        # LLM Logic State
        self.llm = None
        self.history = []
        self.pending_context = ""
        self.specs = self.get_specs()
        
        self.setup_ui()
        self.refresh_models()
        self.apply_styles()

    def get_specs(self):
        ram_gb = round(psutil.virtual_memory().total / (1024**3))
        return {"ram": ram_gb, "cores": os.cpu_count() or 4}

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)

        sidebar_layout.addWidget(QLabel("<b>MODELS</b>"))
        self.model_box = QComboBox()
        self.model_box.currentTextChanged.connect(self.load_selected_model)
        sidebar_layout.addWidget(self.model_box)
        
        sidebar_layout.addStretch()
        self.status_label = QLabel("System Ready")
        sidebar_layout.addWidget(self.status_label)
        
        main_layout.addWidget(self.sidebar)

        # --- Chat Area ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("chatScroll")
        
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.addStretch()
        self.scroll_area.setWidget(self.chat_widget)
        
        right_layout.addWidget(self.scroll_area)

        # --- Input Bar (Gemini Style) ---
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_hbox = QHBoxLayout(input_frame)

        self.attach_btn = QPushButton("+")
        self.attach_btn.setFixedSize(40, 40)
        self.attach_btn.clicked.connect(self.handle_upload)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Neptunium anything...")
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setEnabled(False)

        input_hbox.addWidget(self.attach_btn)
        input_hbox.addWidget(self.input_field)
        input_hbox.addWidget(self.send_btn)
        
        right_layout.addWidget(input_frame)
        main_layout.addWidget(right_container)

    def refresh_models(self):
        models = [f for f in os.listdir(".") if f.endswith(".gguf")]
        self.model_box.clear()
        if models:
            self.model_box.addItems(models)
        else:
            self.model_box.addItem("No models found")

    def load_selected_model(self, model_name):
        if not model_name or not model_name.endswith(".gguf"): return
        self.status_label.setText("Loading model...")
        self.send_btn.setEnabled(False)
        
        # Using a simple thread to load weights without freezing UI
        threading.Thread(target=self._init_llm, args=(model_name,), daemon=True).start()

    def _init_llm(self, path):
        try:
            self.llm = Llama(model_path=path, n_ctx=4096, verbose=False)
            self.status_label.setText("● Online")
            self.send_btn.setEnabled(True)
        except Exception as e:
            self.status_label.setText(f"Error: {e}")

    def handle_upload(self):
        path, _ = QFileDialog.getOpenFileName(self, "Upload File", "", "Text/PDF (*.txt *.pdf)")
        if not path: return
        
        filename = os.path.basename(path)
        if path.endswith(".pdf"):
            doc = fitz.open(path)
            content = "\n".join([page.get_text() for page in doc])
        else:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        
        self.pending_context = f"\n[File: {filename}]\n{content[:5000]}\n"
        self.add_chat_bubble(f"📎 Attached: {filename}", is_user=True, is_file=True)

    def add_chat_bubble(self, text, is_user=True, is_file=False):
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setFixedWidth(500)
        
        bg = "#2b5ff1" if is_user else "#333333"
        if is_file: bg = "#1a3a5a"
        
        bubble.setStyleSheet(f"""
            background-color: {bg};
            color: white;
            border-radius: 15px;
            padding: 12px;
            margin: 5px;
        """)
        
        alignment = Qt.AlignRight if is_user else Qt.AlignLeft
        self.chat_layout.addWidget(bubble, alignment=alignment)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())
        return bubble

    def send_message(self):
        query = self.input_field.text().strip()
        if not query or not self.llm: return
        
        self.add_chat_bubble(query, is_user=True)
        self.input_field.clear()
        
        full_prompt = f"{self.pending_context}\nUser: {query}" if self.pending_context else query
        self.history.append({"role": "user", "content": full_prompt})
        self.pending_context = ""
        
        # Setup AI response bubble
        self.ai_bubble = self.add_chat_bubble("...", is_user=False)
        self.current_ai_text = ""
        
        # Start Worker Thread
        self.worker = LlamaWorker(self.llm, self.history)
        self.worker.response_received.connect(self.update_ai_stream)
        self.worker.finished_generating.connect(lambda: self.send_btn.setEnabled(True))
        self.send_btn.setEnabled(False)
        self.worker.start()

    @Slot(str)
    def update_ai_stream(self, token):
        self.current_ai_text += token
        self.ai_bubble.setText(self.current_ai_text)
        self.ai_bubble.adjustSize()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            #sidebar { 
                background-color: #121212; 
                border-right: 1px solid #333; 
                padding: 15px;
            }
            #chatScroll { border: none; background: transparent; }
            #inputFrame { 
                background-color: #252525; 
                border-top: 1px solid #333; 
                padding: 10px;
            }
            QLineEdit {
                background-color: #333;
                border: 1px solid #444;
                border-radius: 20px;
                padding: 8px 15px;
                color: white;
            }
            QPushButton {
                background-color: #2b5ff1;
                color: white;
                border-radius: 15px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:disabled { background-color: #444; }
            QLabel { color: #ccc; }
        """)

if __name__ == "__main__":
    import threading
    app = QApplication(sys.argv)
    window = NeptuniumApp()
    window.show()
    sys.exit(app.exec())