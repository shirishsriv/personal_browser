# Indo Chromium Browser + MiniCPM AI

A lightweight multi-tab desktop browser built with **PyQt6** and **PyQt6-WebEngine**, with an integrated AI sidebar powered by **MiniCPM5-2B-0822** through the ModelBest API.

The AI assistant can read the currently displayed webpage and answer questions about its content.

## Features

### Browser
- Multi-tab browsing
- New tab button
- Back, Forward, Reload, and Home navigation
- URL/search bar
- Google search when a search phrase is entered
- Browser history
- External history-file opening
- Chromium-based webpage rendering through Qt WebEngine

### AI Assistant
- Integrated AI sidebar
- Powered by `MiniCPM5-2B-0822`
- Uses the ModelBest Chat Completions API
- Read the current webpage with one click
- Ask questions about the current webpage
- Page title and URL are included as context
- Automatic webpage reading when asking a question without existing page context
- Chat history during the current session
- Clear chat option
- Handles API, HTTP, and network errors

## Requirements

- Python 3.9+ recommended
- PyQt6
- PyQt6-WebEngine
- A ModelBest API key with access to `MiniCPM5-2B-0822`

## Installation

Clone the repository:

```bash
git clone https://github.com/shirishsriv/personal_browser.git
cd personal_browser
```

Install dependencies:

```bash
python3 -m pip install PyQt6 PyQt6-WebEngine
```

### macOS Python note

If `pip` and `python3` point to different Python installations, install using the same Python executable that will run the application:

```bash
python3 -m pip install PyQt6 PyQt6-WebEngine
```

You can check the Python installation with:

```bash
which python3
python3 --version
python3 -c "import sys; print(sys.executable)"
```

If you use the Python 3.11 installation from the official Python framework on macOS:

```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pip install PyQt6 PyQt6-WebEngine
```

## Configure the ModelBest API Key

The application reads the API key from the environment variable:

```text
MODEL_BEST_API_KEY
```

### macOS / Linux

```bash
export MODEL_BEST_API_KEY="YOUR_TEST_KEY"
```

Then run:

```bash
python3 main.py
```

### Windows PowerShell

```powershell
$env:MODEL_BEST_API_KEY="YOUR_TEST_KEY"
python main.py
```

**Never hard-code the API key inside `main.py` and never commit it to GitHub.**

## Running the Application

From the project directory:

```bash
python3 main.py
```

On macOS, if necessary:

```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 main.py
```

## Using the AI Assistant

1. Start the browser.
2. Open a webpage.
3. Click the **🤖 AI** button to open the AI sidebar.
4. Click **📖 Read Current Page**.
5. Wait for the page content to be extracted.
6. Type a question in the AI input box.
7. Click **Send**.

Example questions:

```text
Summarize this webpage.
```

```text
What are the main points of this article?
```

```text
Explain this page in simple language.
```

```text
What are the important facts mentioned on this page?
```

The application extracts the rendered webpage text using Qt WebEngine's `toPlainText()` functionality. Very large pages are limited to approximately 30,000 characters to keep the AI request manageable.

## Project Structure

```text
personal_browser/
├── main.py
├── README.md
└── Application_Screenshot.png
```

## API Configuration

The application communicates with:

```text
https://api.modelbest.cn/v1/chat/completions
```

The configured model is:

```text
MiniCPM5-2B-0822
```

The request uses the standard Chat Completions structure with a Bearer token supplied through `MODEL_BEST_API_KEY`.

## Security

Do not commit secrets to GitHub.

Recommended:

```bash
export MODEL_BEST_API_KEY="YOUR_TEST_KEY"
```

Do not do this inside `main.py`:

```python
MODEL_BEST_API_KEY = "actual-secret-key"
```

If you create a `.env` file for local development, add it to `.gitignore`:

```gitignore
.env
```

## GitHub Workflow

After modifying `main.py`:

```bash
git status
git add main.py README.md
git commit -m "Add MiniCPM AI webpage assistant"
git push origin main
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'PyQt6'`

Install the packages with the same Python interpreter used to run the application:

```bash
python3 -m pip install PyQt6 PyQt6-WebEngine
```

Then verify:

```bash
python3 -c "import PyQt6; print('PyQt6 installed')"
```

### AI says API key is missing

Check that the environment variable exists.

macOS/Linux:

```bash
echo $MODEL_BEST_API_KEY
```

Windows PowerShell:

```powershell
echo $env:MODEL_BEST_API_KEY
```

If it is empty, set it again and restart the application.

### AI cannot answer questions about the page

Click:

```text
📖 Read Current Page
```

before asking the question.

Also make sure the webpage has finished loading.

### API/network errors

Check:
- Internet connection
- ModelBest API availability
- API key validity
- Model access
- Firewall or network restrictions

## Development

The application intentionally uses Python's built-in HTTP libraries for the ModelBest request rather than requiring an additional AI SDK.

Main technologies:

- Python
- PyQt6
- PyQt6-WebEngine
- Qt WebEngine
- ModelBest API
- MiniCPM5-2B-0822

## License

Add the appropriate license for your project before distributing it publicly.
