import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, QVBoxLayout,
    QWidget, QMessageBox, QDialog, QTextEdit, QTabWidget, QFileDialog, QHBoxLayout, QListWidget, QComboBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from PyPDF2 import PdfReader
from gtts import gTTS
import os
from hashlib import sha256

# Global stylesheet for the app
STYLESHEET = """
QDialog, QMainWindow {
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
    stop:0 rgba(34, 193, 195, 255), stop:1 rgba(253, 187, 45, 255));
}

QPushButton {
    font-size: 16px;
    color: white;
    background-color: #ff7f50;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    transition: all 0.3s ease;
    box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2);
}

QPushButton:hover {
    background-color: #ff4500;
    box-shadow: 4px 4px 10px rgba(0, 0, 0, 0.3);
}

QLabel {
    font-size: 16px;
    color: white;
}

QLineEdit {
    font-size: 14px;
    color: #333;
    background-color: #fefefe;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 8px;
}

QTextEdit {
    background-color: #fefefe;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    padding: 10px;
    color: #333;
}
"""

# Database setup
def setup_database():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            file_path TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    conn.commit()
    conn.close()

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(100, 100, 400, 250)
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Login")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)

        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        button_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.login)
        button_layout.addWidget(self.login_button)

        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self.open_register_dialog)
        button_layout.addWidget(self.register_button)

        layout.addLayout(button_layout)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        hashed_password = sha256(password.encode()).hexdigest()

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
        user = cursor.fetchone()
        conn.close()

        if user:
            QMessageBox.information(self, "Login Success", f"Welcome, {username}!")
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password!")

    def open_register_dialog(self):
        dialog = RegisterDialog()
        dialog.exec()

class RegisterDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Register")
        self.setGeometry(100, 100, 400, 300)
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Register")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)

        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self.register)
        layout.addWidget(self.register_button)

    def register(self):
        username = self.username_input.text()
        password = self.password_input.text()
        hashed_password = sha256(password.encode()).hexdigest()

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            QMessageBox.information(self, "Success", "Registration successful!")
            self.accept()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "Username already exists!")
        finally:
            conn.close()

class ModernPDFReader(QMainWindow):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle("✨PDF & Text-to-Speech Reader")
        self.setGeometry(100, 100, 900, 600)
        self.setStyleSheet(STYLESHEET)

        # Main Layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Left Pane: Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, stretch=3)

        # PDF Reader Tab
        self.pdf_tab = QWidget()
        self.init_pdf_tab()
        self.tabs.addTab(self.pdf_tab, "📄 PDF Reader")

        # Text-to-Speech Tab
        self.tts_tab = QWidget()
        self.init_tts_tab()
        self.tabs.addTab(self.tts_tab, "🎙️ Text-to-Speech")

        # Right Pane: Uploaded Files with Delete Button
        self.uploaded_files_list = QListWidget()
        self.uploaded_files_list.itemClicked.connect(self.load_uploaded_file)

        self.delete_file_button = QPushButton("🗑️ Delete Selected File")
        self.delete_file_button.clicked.connect(self.delete_selected_file)

        # Create right pane layout
        right_pane_layout = QVBoxLayout()
        right_pane_layout.addWidget(QLabel("Uploaded Files"))  # Optional: Heading
        right_pane_layout.addWidget(self.uploaded_files_list)
        right_pane_layout.addWidget(self.delete_file_button)

        # Add right pane layout to the main layout
        right_pane_widget = QWidget()
        right_pane_widget.setLayout(right_pane_layout)
        main_layout.addWidget(right_pane_widget, stretch=1)

        # Load user's uploaded files
        self.load_uploaded_files()

    def init_pdf_tab(self):
        """Set up the PDF Reader tab."""
        layout = QVBoxLayout()
        self.pdf_tab.setLayout(layout)

        # Language selector for PDF tab
        self.language_selector = QComboBox()
        self.language_selector.addItem("English", "en")  # English language code
        self.language_selector.addItem("Khmer", "km")    # Khmer language code
        layout.addWidget(QLabel("Select Language:"))
        layout.addWidget(self.language_selector)

        # Load PDF Button
        self.load_pdf_button = QPushButton("📂 Upload and Load PDF")
        self.load_pdf_button.clicked.connect(self.upload_and_load_pdf)
        layout.addWidget(self.load_pdf_button)

        # Text Display Area
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        layout.addWidget(self.text_display)

        # Play PDF Button
        self.play_pdf_button = QPushButton("▶️ Play PDF")
        self.play_pdf_button.clicked.connect(self.play_pdf)
        self.play_pdf_button.setEnabled(False)
        layout.addWidget(self.play_pdf_button)


    def init_tts_tab(self):
        """Set up the Text-to-Speech tab."""
        layout = QVBoxLayout()
        self.tts_tab.setLayout(layout)

        # Language selector for TTS tab
        self.tts_language_selector = QComboBox()
        self.tts_language_selector.addItem("English", "en")  # English language code
        self.tts_language_selector.addItem("Khmer", "km")    # Khmer language code
        layout.addWidget(QLabel("Select Language:"))
        layout.addWidget(self.tts_language_selector)

        # Text Input Area
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text to speak...")
        layout.addWidget(self.text_input)

        # Speak Button
        self.speak_button = QPushButton("🎤 Speak Text")
        self.speak_button.clicked.connect(self.speak_text)
        layout.addWidget(self.speak_button)


    def upload_and_load_pdf(self):
        """Upload and load a PDF."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if file_path:
            # Save file path to database
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO uploaded_files (username, file_path) VALUES (?, ?)", (self.username, file_path))
            conn.commit()
            conn.close()

            # Add file to list and load it
            self.uploaded_files_list.addItem(file_path)
            self.load_pdf(file_path)

    def load_uploaded_file(self, item):
        """Load a selected uploaded file."""
        file_path = item.text()
        self.load_pdf(file_path)

    def load_pdf(self, file_path):
        """Load a PDF and display its content."""
        try:
            pdf = PdfReader(file_path)
            text = "\n".join(page.extract_text() for page in pdf.pages)
            self.text_display.setPlainText(text)
            self.play_pdf_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PDF: {e}")

    def play_pdf(self):
        """Convert PDF text to speech and play it."""
        text = self.text_display.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Warning", "No text available to play!")
            return

        # Get the selected language
        lang = self.language_selector.currentData()  # Retrieve the language code (e.g., "en" or "km")
        
        try:
            tts = gTTS(text=text, lang=lang)
            audio_file = "pdf_audio.mp3"
            tts.save(audio_file)
            os.system(f"start {audio_file}" if os.name == "nt" else f"xdg-open {audio_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to play audio: {e}")


    def speak_text(self):
        """Speak text entered by the user."""
        text = self.text_input.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Warning", "Please enter text to speak!")
            return

        # Get the selected language
        lang = self.tts_language_selector.currentData()  # Retrieve the language code (e.g., "en" or "km")
        
        try:
            tts = gTTS(text=text, lang=lang)
            audio_file = "text_audio.mp3"
            tts.save(audio_file)
            os.system(f"start {audio_file}" if os.name == "nt" else f"xdg-open {audio_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to play audio: {e}")


    def load_uploaded_files(self):
        """Load uploaded files for the current user."""
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM uploaded_files WHERE username = ?", (self.username,))
        files = cursor.fetchall()
        conn.close()

        for file in files:
            file_name = os.path.basename(file[0])
            self.uploaded_files_list.addItem(file_name)

    def delete_selected_file(self):
        """Deletes the selected file from the uploaded files list and the database."""
        selected_item = self.uploaded_files_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Warning", "No file selected!")
            return

        file_path = selected_item.text()

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete this file?\n\n{file_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Remove the file from the database
                conn = sqlite3.connect("users.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM uploaded_files WHERE username = ? AND file_path = ?", (self.username, file_path))
                conn.commit()
                conn.close()

                # Remove the file from the UI list
                self.uploaded_files_list.takeItem(self.uploaded_files_list.row(selected_item))
                QMessageBox.information(self, "Success", "The file has been deleted successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file: {e}")


if __name__ == "__main__":
    setup_database()
    app = QApplication([])
    login_dialog = LoginDialog()
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        username = login_dialog.username_input.text()
        main_window = ModernPDFReader(username)
        main_window.show()
        app.exec()
