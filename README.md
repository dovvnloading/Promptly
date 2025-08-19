# Promptly | An AI-Powered Prompt Engineering Toolkit

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-orange.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

**Promptly** is a sleek, standalone desktop application designed to streamline the prompt engineering workflow. It leverages local Large Language Models (LLMs) via Ollama to help you refine, enhance, and objectively evaluate your prompts, turning rough ideas into highly effective instructions for AI.

This tool acts as a dedicated assistant, ensuring your prompts are clear, specific, and actionable, ultimately leading to better and more consistent AI-generated results.


<img width="1170" height="707" alt="Screenshot 2025-08-19 091434" src="https://github.com/user-attachments/assets/8b5e301d-05d8-47d5-946d-296cd5bba673" />

## About The Project

In the world of generative AI, the quality of the output is directly tied to the quality of the input. Crafting the perfect prompt can be a tedious process of trial and error. **Promptly** is built to solve this problem by providing a structured, AI-assisted environment for prompt development.

Instead of guessing what might work, you can use Promptly to:
*   **Refine a concept:** Automatically enhance a basic prompt with structure, clarity, and specific details.
*   **Iterate with feedback:** Guide the AI to better versions if the first enhancement isn't quite right.
*   **Quantify improvement:** Get an objective, AI-driven analysis of how much better the enhanced prompt is compared to the original.

---

## Key Features

🧠 **AI-Powered Prompt Refinement**
*   Utilizes a specialized `Prompt Engineering Assistant` agent to rewrite and improve your prompts.
*   The agent is strictly instructed to enhance clarity, add structure, and remove ambiguity, without answering or fulfilling the prompt itself.
*   Maintains the original intent while optimizing for AI comprehension.

🔄 **Iterative Feedback Loop**
*   If a generated prompt isn't satisfactory, a one-click "feedback" button tells the AI to reconsider its last attempt and try again, using the original prompt as a reference.
*   The assistant maintains a short-term memory of recent attempts to avoid repetition and encourage novel improvements.

📊 **Quantitative Prompt Evaluation**
*   Features a dedicated `Prompt Evaluation Agent` that objectively compares your original prompt against the enhanced version.
*   Generates a detailed report with scores (0-100) for **Clarity**, **Specificity**, and **Actionability**.
*   Provides an **Overall Improvement** score and a list of specific changes made and further suggestions.

🖥️ **Modern & Responsive Desktop UI**
*   Built with **PyQt5** with a polished, dark-themed interface inspired by modern developer tools.
*   **Fully Asynchronous Operations**: All Ollama requests run on background threads, ensuring the UI remains fast and responsive at all times.
*   **Custom UI Components**: Features a custom frameless window, smooth loading spinners, and rich-text display with Markdown-style highlighting for enhanced readability.
*   **System Tray Integration**: Can be minimized to the system tray for easy access without cluttering your taskbar, with desktop notifications for completed tasks.

---

## How It Works

1.  **Input:** The user enters a draft or a basic idea for a prompt in the left-hand panel.
2.  **Generate:** Upon clicking "Generate," the `PromptWorker` sends the text to a local LLM (e.g., `phi4:14b`) with a system prompt that guides it to act as a prompt engineer.
3.  **Enhance:** The LLM returns a refined, well-structured version of the prompt, which is displayed in the right-hand panel with syntax highlighting.
4.  **Iterate or Evaluate:**
    *   **Copy:** The user can copy the new prompt for use.
    *   **Feedback:** If needed, the user can click the "Feedback" button to trigger a regeneration.
    *   **Evaluate:** The user can click the "Evaluate" button to open a new window.
5.  **Analysis:** The `PromptEvaluator` agent receives both the original and enhanced prompts. It performs a comparative analysis and returns a structured JSON report.
6.  **Report:** The evaluation results are displayed in a clean, graphical interface with progress bars, scores, and detailed text feedback.

---

## Tech Stack

*   **Language**: Python
*   **GUI Framework**: `PyQt5`
*   **AI/LLM Backend**: `ollama` for local model hosting.
    *   **Models Used**: `phi4:14b` (or similar high-quality instruction-tuned model)
*   **UI Styling**: Custom stylesheets for a modern, dark theme.
*   **Data Persistence**: `JSON` for storing prompt history.

---

## Getting Started

Follow these instructions to get Promptly up and running on your machine.

### Prerequisites

1.  **Python**: Python 3.8 or newer is recommended.
2.  **Ollama**: You must have [Ollama](https://ollama.com/) installed and running on your system.
3.  **Required LLM Model**: Pull the model used by the application from the Ollama library.
    ```sh
    ollama pull phi4:14b
    ```
    *(You can modify the model name in the source code if you wish to use another model like `llama3` or `mistral`)*

### Installation

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/your-username/promptly.git
    cd promptly
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```sh
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install the required packages:**
    ```sh
    pip install PyQt5 ollama
    ```
4.  **Run the application:**
    ```sh
    python Promptly.py
    ```
---

Icon source and credits: https://thenounproject.com
