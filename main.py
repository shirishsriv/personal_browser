import sys
import os
import json
import urllib.request
import urllib.error
import urllib.parse

try:
    import ctypes
except ImportError:
    ctypes = None

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QToolBar,
    QLineEdit,
    QTabWidget,
    QPushButton,
    QDockWidget,
    QPlainTextEdit,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QObject, QThread, pyqtSignal, Qt


MODEL_BEST_URL = "https://api.modelbest.cn/v1/chat/completions"
MODEL_NAME = "MiniCPM5-2B-0822"
MAX_PAGE_CHARS = 30000


class ChatWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def run(self):
        api_key = os.getenv("MODEL_BEST_API_KEY")

        if not api_key:
            self.error.emit(
                "MODEL_BEST_API_KEY is not set.\n\n"
                "Start the browser with your API key, for example:\n"
                "export MODEL_BEST_API_KEY=\"YOUR_TEST_KEY\"\n"
                "python3 main.py"
            )
            return

        payload = {
            "model": MODEL_NAME,
            "messages": self.messages,
            "stream": False,
        }

        request = urllib.request.Request(
            MODEL_BEST_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                response_data = json.loads(
                    response.read().decode("utf-8")
                )

            choices = response_data.get("choices", [])
            if not choices:
                self.error.emit(
                    "Unexpected API response:\n\n"
                    + json.dumps(response_data, indent=2)
                )
                return

            message = choices[0].get("message", {})
            answer = message.get("content")

            if isinstance(answer, list):
                answer = "".join(
                    item.get("text", "")
                    for item in answer
                    if isinstance(item, dict)
                )

            if not answer:
                self.error.emit(
                    "The model returned an empty response:\n\n"
                    + json.dumps(response_data, indent=2)
                )
                return

            self.finished.emit(str(answer))

        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = str(exc)
            self.error.emit(
                f"ModelBest API error ({exc.code}):\n\n{body}"
            )
        except urllib.error.URLError as exc:
            self.error.emit(
                f"Network error while contacting ModelBest:\n\n{exc}"
            )
        except Exception as exc:
            self.error.emit(f"Unexpected error:\n\n{exc}")


class MultiTabBrowser(QMainWindow):
    def __init__(self):
        super().__init__()

        self.history_file = "history.txt"

        # Conversation messages sent to the model.
        self.chat_messages = []

        # Text extracted from the currently selected webpage.
        self.current_page_text = ""
        self.current_page_url = ""
        self.current_page_title = ""

        self.chat_thread = None
        self.chat_worker = None

        # ----------------------------------------------------
        # Main browser tabs
        # ----------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)

        # ----------------------------------------------------
        # Navigation toolbar
        # ----------------------------------------------------
        navbar = QToolBar("Navigation")
        self.addToolBar(navbar)

        back_btn = QPushButton("←")
        back_btn.setToolTip("Back")
        back_btn.clicked.connect(
            lambda: self.tabs.currentWidget().back()
        )
        navbar.addWidget(back_btn)

        forward_btn = QPushButton("→")
        forward_btn.setToolTip("Forward")
        forward_btn.clicked.connect(
            lambda: self.tabs.currentWidget().forward()
        )
        navbar.addWidget(forward_btn)

        reload_btn = QPushButton("↻")
        reload_btn.setToolTip("Reload")
        reload_btn.clicked.connect(
            lambda: self.tabs.currentWidget().reload()
        )
        navbar.addWidget(reload_btn)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText(
            "Enter URL and press Enter..."
        )
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        navbar.addWidget(self.url_bar)

        new_tab_btn = QPushButton("+")
        new_tab_btn.setToolTip("New Tab")
        new_tab_btn.clicked.connect(self.add_new_tab)
        navbar.addWidget(new_tab_btn)

        history_btn = QPushButton("📜")
        history_btn.setToolTip("History")
        history_btn.clicked.connect(self.show_history)
        navbar.addWidget(history_btn)

        ai_btn = QPushButton("🤖 AI")
        ai_btn.setToolTip(
            "Open MiniCPM5-2B-0822 AI Assistant"
        )
        ai_btn.clicked.connect(self.toggle_ai_panel)
        navbar.addWidget(ai_btn)

        # ----------------------------------------------------
        # AI panel
        # ----------------------------------------------------
        self.create_ai_panel()

        # Initial page
        self.add_new_tab(
            QUrl("https://www.google.com"),
            "Homepage"
        )

        self.setWindowTitle("Indo Chromium Browser")
        self.showMaximized()

    # ========================================================
    # AI PANEL
    # ========================================================

    def create_ai_panel(self):
        self.ai_dock = QDockWidget(
            "MiniCPM5-2B-0822 AI",
            self
        )

        self.ai_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )

        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.page_status = QLabel(
            "Page context: not loaded"
        )
        self.page_status.setWordWrap(True)
        layout.addWidget(self.page_status)

        self.read_page_button = QPushButton(
            "📖 Read Current Page"
        )
        self.read_page_button.setToolTip(
            "Extract visible text from the current webpage"
        )
        self.read_page_button.clicked.connect(
            self.read_current_page
        )
        layout.addWidget(self.read_page_button)

        self.chat_output = QPlainTextEdit()
        self.chat_output.setReadOnly(True)
        self.chat_output.setPlaceholderText(
            "Ask MiniCPM about the current webpage..."
        )
        layout.addWidget(self.chat_output)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(
            "Ask about this page and press Enter..."
        )
        self.chat_input.returnPressed.connect(
            self.send_chat_message
        )
        layout.addWidget(self.chat_input)

        button_layout = QHBoxLayout()

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(
            self.send_chat_message
        )
        button_layout.addWidget(self.send_button)

        clear_button = QPushButton("Clear Chat")
        clear_button.clicked.connect(
            self.clear_chat
        )
        button_layout.addWidget(clear_button)

        layout.addLayout(button_layout)

        self.ai_dock.setWidget(panel)

        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,
            self.ai_dock
        )

        self.ai_dock.hide()

    def toggle_ai_panel(self):
        visible = self.ai_dock.isVisible()
        self.ai_dock.setVisible(not visible)

        if not visible:
            self.chat_input.setFocus()

    # ========================================================
    # WEBPAGE READING
    # ========================================================

    def read_current_page(self):
        browser = self.tabs.currentWidget()

        if browser is None:
            return

        self.read_page_button.setEnabled(False)
        self.page_status.setText(
            "📖 Reading current webpage..."
        )

        # QWebEnginePage.toPlainText() extracts rendered text
        # rather than sending the entire HTML source.
        browser.page().toPlainText(
            self.on_page_text_extracted
        )

    def on_page_text_extracted(self, text):
        text = (text or "").strip()

        if not text:
            self.current_page_text = ""
            self.page_status.setText(
                "⚠️ No readable text found on this page."
            )
            self.read_page_button.setEnabled(True)
            return

        # Keep the request reasonably small.
        if len(text) > MAX_PAGE_CHARS:
            text = text[:MAX_PAGE_CHARS] + (
                "\n\n[Page text truncated because it is very large.]"
            )

        browser = self.tabs.currentWidget()

        if browser is not None:
            self.current_page_url = (
                browser.url().toString()
            )
            self.current_page_title = (
                browser.page().title()
            )

        self.current_page_text = text

        title = self.current_page_title or "Current page"

        self.page_status.setText(
            f"📄 Page ready: {title}\n"
            f"Extracted {len(text):,} characters."
        )

        self.read_page_button.setEnabled(True)

        # Keep page context separate from chat history.
        self.chat_output.appendPlainText(
            "\n📖 Current webpage has been read. "
            "You can now ask questions about it.\n"
        )

    def reset_page_context(self):
        self.current_page_text = ""
        self.current_page_url = ""
        self.current_page_title = ""

        self.page_status.setText(
            "Page context: not loaded"
        )

    # ========================================================
    # CHAT
    # ========================================================

    def clear_chat(self):
        self.chat_messages = []
        self.chat_output.clear()

    def send_chat_message(self):
        text = self.chat_input.text().strip()

        if not text:
            return

        if self.chat_thread is not None:
            return

        # Automatically read the current page if the user has
        # not explicitly pressed "Read Current Page".
        if not self.current_page_text:
            self.read_page_button.setEnabled(False)
            self.chat_input.setEnabled(False)
            self.send_button.setEnabled(False)
            self.chat_output.appendPlainText(
                "📖 Reading the current page first...\n"
            )

            browser = self.tabs.currentWidget()

            if browser is None:
                self.on_page_read_failed()
                return

            self.pending_question = text
            browser.page().toPlainText(
                self.on_page_text_for_question
            )
            return

        self._send_question_with_context(text)

    def on_page_text_for_question(self, text):
        self.read_page_button.setEnabled(True)
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)

        text = (text or "").strip()

        if not text:
            self.chat_output.appendPlainText(
                "⚠️ Could not extract readable text from the page.\n"
            )
            self.pending_question = None
            return

        if len(text) > MAX_PAGE_CHARS:
            text = text[:MAX_PAGE_CHARS] + (
                "\n\n[Page text truncated because it is very large.]"
            )

        browser = self.tabs.currentWidget()

        if browser is not None:
            self.current_page_url = (
                browser.url().toString()
            )
            self.current_page_title = (
                browser.page().title()
            )

        self.current_page_text = text

        question = getattr(
            self,
            "pending_question",
            None
        )

        self.pending_question = None

        if question:
            self._send_question_with_context(question)

    def on_page_read_failed(self):
        self.read_page_button.setEnabled(True)
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.pending_question = None

    def _send_question_with_context(self, text):
        self.chat_input.clear()

        self.chat_output.appendPlainText(
            f"\nYou:\n{text}\n"
        )

        # System instruction + current page context.
        page_title = (
            self.current_page_title
            or "Current webpage"
        )

        page_url = (
            self.current_page_url
            or ""
        )

        context_message = (
            "You are an AI assistant inside a personal web browser. "
            "Answer questions using the current webpage context when "
            "relevant. If the answer is not present in the page, say "
            "that clearly rather than inventing information.\n\n"
            f"CURRENT PAGE TITLE:\n{page_title}\n\n"
            f"CURRENT PAGE URL:\n{page_url}\n\n"
            "CURRENT PAGE TEXT:\n"
            f"{self.current_page_text}"
        )

        # Build a request conversation without permanently adding
        # the large page context to every turn of chat history.
        messages = [
            {
                "role": "system",
                "content": context_message,
            }
        ]

        # Include recent conversation history.
        messages.extend(
            self.chat_messages[-10:]
        )

        messages.append(
            {
                "role": "user",
                "content": text,
            }
        )

        # Store only user/assistant messages, not the page context.
        self.chat_messages.append(
            {
                "role": "user",
                "content": text,
            }
        )

        self.send_button.setEnabled(False)
        self.chat_input.setEnabled(False)
        self.read_page_button.setEnabled(False)

        self.chat_output.appendPlainText(
            "MiniCPM:\nThinking...\n"
        )

        self.chat_thread = QThread()
        self.chat_worker = ChatWorker(messages)
        self.chat_worker.moveToThread(
            self.chat_thread
        )

        self.chat_thread.started.connect(
            self.chat_worker.run
        )

        self.chat_worker.finished.connect(
            self.on_chat_response
        )

        self.chat_worker.error.connect(
            self.on_chat_error
        )

        self.chat_worker.finished.connect(
            self.chat_thread.quit
        )

        self.chat_worker.error.connect(
            self.chat_thread.quit
        )

        self.chat_thread.finished.connect(
            self.cleanup_chat_worker
        )

        self.chat_thread.start()

    def on_chat_response(self, answer):
        self.chat_output.appendPlainText(
            f"MiniCPM:\n{answer}\n"
        )

        self.chat_messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

    def on_chat_error(self, message):
        self.chat_output.appendPlainText(
            f"❌ Error:\n{message}\n"
        )

        # Remove the user message that was queued but did not
        # receive a response, so it can be retried cleanly.
        if (
            self.chat_messages
            and self.chat_messages[-1].get("role") == "user"
        ):
            self.chat_messages.pop()

    def cleanup_chat_worker(self):
        self.send_button.setEnabled(True)
        self.chat_input.setEnabled(True)
        self.read_page_button.setEnabled(True)
        self.chat_input.setFocus()

        if self.chat_worker is not None:
            self.chat_worker.deleteLater()

        if self.chat_thread is not None:
            self.chat_thread.deleteLater()

        self.chat_worker = None
        self.chat_thread = None

    # ========================================================
    # TABS
    # ========================================================

    def add_new_tab(
        self,
        qurl=None,
        label="New Tab"
    ):
        if qurl is None:
            qurl = QUrl("https://www.google.com")

        browser = QWebEngineView()
        browser.setUrl(qurl)

        index = self.tabs.addTab(
            browser,
            label
        )
        self.tabs.setCurrentIndex(index)

        browser.urlChanged.connect(
            lambda url, browser=browser:
            self.update_ui_components(
                url,
                browser
            )
        )

        browser.loadFinished.connect(
            lambda success, browser=browser:
            self.finalize_page_load(
                browser
            )
        )

    def finalize_page_load(self, browser):
        index = self.tabs.indexOf(browser)

        if index != -1:
            title = browser.page().title()

            if not title:
                title = "New Tab"

            self.tabs.setTabText(
                index,
                title[:20]
            )

            if browser == self.tabs.currentWidget():
                self.setWindowTitle(
                    f"{title} - Indo Chromium Browser"
                )

            try:
                with open(
                    self.history_file,
                    "a",
                    encoding="utf-8"
                ) as f:
                    f.write(
                        f"{browser.url().toString()}\n"
                    )
            except Exception:
                pass

    def tab_open_doubleclick(self, index):
        if index == -1:
            self.add_new_tab()

    def current_tab_changed(self, index):
        if index == -1:
            return

        current_browser = self.tabs.currentWidget()

        if current_browser is None:
            return

        self.update_ui_components(
            current_browser.url(),
            current_browser
        )

        title = current_browser.page().title()

        if not title:
            title = "New Tab"

        self.setWindowTitle(
            f"{title} - Indo Chromium Browser"
        )

        # Page context belongs to the active tab. Reset it when
        # switching tabs so we never accidentally ask about the
        # previous tab.
        self.reset_page_context()

    def close_current_tab(self, index):
        if self.tabs.count() < 2:
            return

        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)

        if widget is not None:
            widget.deleteLater()

    # ========================================================
    # NAVIGATION
    # ========================================================

    def navigate_to_url(self):
        url_input = self.url_bar.text().strip()

        if not url_input:
            return

        if "://" not in url_input:
            if " " in url_input:
                search_url = (
                    "https://www.google.com/search?q="
                    + urllib.parse.quote(url_input)
                )
                qurl = QUrl(search_url)
            else:
                qurl = QUrl(
                    "https://" + url_input
                )
        else:
            qurl = QUrl(url_input)

        self.tabs.currentWidget().setUrl(qurl)

    def update_ui_components(
        self,
        qurl,
        browser=None
    ):
        if browser != self.tabs.currentWidget():
            return

        self.url_bar.setText(
            qurl.toString()
        )
        self.url_bar.setCursorPosition(0)

    # ========================================================
    # HISTORY
    # ========================================================

    def show_history(self):
        if not os.path.exists(
            self.history_file
        ):
            return

        try:
            if sys.platform == "win32":
                os.startfile(
                    self.history_file
                )
            elif sys.platform == "darwin":
                os.system(
                    f'open "{self.history_file}"'
                )
            else:
                os.system(
                    f'xdg-open "{self.history_file}"'
                )
        except Exception as exc:
            print(
                f"Could not open history: {exc}"
            )


if __name__ == "__main__":
    if (
        sys.platform == "win32"
        and ctypes
    ):
        my_app_id = (
            "indo.chromium.browser.1.0"
        )
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            my_app_id
        )

    app = QApplication(sys.argv)
    app.setApplicationName(
        "Indo Chromium Browser"
    )

    window = MultiTabBrowser()
    sys.exit(app.exec())
