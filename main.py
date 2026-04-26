import sys
import os
# This library is needed to tell Windows to treat this as a separate app
try:
    import ctypes
except ImportError:
    ctypes = None

from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar, QLineEdit, 
                             QTabWidget, QVBoxLayout, QWidget, QPushButton)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

class MultiTabBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.history_file = "history.txt"

        # 1. Main Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.setCentralWidget(self.tabs)

        # 2. Navigation Bar
        navbar = QToolBar("Navigation")
        self.addToolBar(navbar)

        # Navigation Buttons
        back_btn = QPushButton("←")
        back_btn.clicked.connect(lambda: self.tabs.currentWidget().back())
        navbar.addWidget(back_btn)

        forward_btn = QPushButton("→")
        forward_btn.clicked.connect(lambda: self.tabs.currentWidget().forward())
        navbar.addWidget(forward_btn)

        reload_btn = QPushButton("↻")
        reload_btn.clicked.connect(lambda: self.tabs.currentWidget().reload())
        navbar.addWidget(reload_btn)

        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL and press Enter...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        navbar.addWidget(self.url_bar)

        # Function Buttons
        new_tab_btn = QPushButton("+")
        new_tab_btn.clicked.connect(lambda: self.add_new_tab())
        navbar.addWidget(new_tab_btn)

        hist_btn = QPushButton("📜")
        hist_btn.clicked.connect(self.show_history)
        navbar.addWidget(hist_btn)

        # Initial Tab Setup
        self.add_new_tab(QUrl("https://www.google.com"), "Homepage")

        # --- SET WINDOW TITLE ---
        self.setWindowTitle("Indo Chromium Browser")
        self.showMaximized()

    def add_new_tab(self, qurl=None, label="New Tab"):
        if qurl is None:
            qurl = QUrl("https://www.google.com")

        browser = QWebEngineView()
        browser.setUrl(qurl)
        
        index = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(index)

        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_ui_components(qurl, browser))
        browser.loadFinished.connect(lambda _, browser=browser: self.finalize_page_load(browser))

    def finalize_page_load(self, browser):
        index = self.tabs.indexOf(browser)
        if index != -1:
            title = browser.page().title()
            self.tabs.setTabText(index, title[:20])
            if browser == self.tabs.currentWidget():
                self.setWindowTitle(f"{title} - Indo Chromium Browser")
            
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(f"{browser.url().toString()}\n")

    def tab_open_doubleclick(self, i):
        if i == -1: self.add_new_tab()

    def current_tab_changed(self, i):
        if i != -1:
            current_browser = self.tabs.currentWidget()
            qurl = current_browser.url()
            self.update_ui_components(qurl, current_browser)
            self.setWindowTitle(f"{current_browser.page().title()} - Indo Chromium Browser")

    def close_current_tab(self, i):
        if self.tabs.count() < 2: return
        self.tabs.removeTab(i)

    def navigate_to_url(self):
        url_input = self.url_bar.text()
        q = QUrl(url_input)
        if q.scheme() == "":
            q.setScheme("https")
        self.tabs.currentWidget().setUrl(q)

    def update_ui_components(self, q, browser=None):
        if browser != self.tabs.currentWidget():
            return
        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)

    def show_history(self):
        if os.path.exists(self.history_file):
            os.startfile(self.history_file) if sys.platform == "win32" else os.system(f"open {self.history_file}")

if __name__ == "__main__":
    # --- TASKBAR NAME FIX (WINDOWS ONLY) ---
    if sys.platform == "win32" and ctypes:
        my_app_id = "indo.chromium.browser.1.0" # A unique string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)

    app = QApplication(sys.argv)
    app.setApplicationName("Indo Chromium Browser")
    
    window = MultiTabBrowser()
    sys.exit(app.exec())
