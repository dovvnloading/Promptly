import sys
import json
import os
import re
import math  # Import math for LoadingSpinner
import markdown


from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QFrame, QSystemTrayIcon, QMenu, QAction,
                             QGraphicsDropShadowEffect, QMessageBox, QToolTip)
from PyQt5.QtCore import (QPoint, QPointF, QSize, Qt, QThread, pyqtSignal, QTimer,
                          QRect)
from PyQt5.QtGui import (QFont, QIcon, QColor, QPalette, QPainter, QPen,
                         QSyntaxHighlighter, QTextCharFormat, QTextOption, QPainterPath)
import ollama

# Import the EvaluationDialog and related classes from the other file
from prompt_evaluator import PromptEvaluator, EvaluationDialog, EvalWorkerThread


class PromptDatabase:
    PROMPT_FILE = "prompt_history.json"

    @classmethod
    def load_prompts(cls):
        try:
            if os.path.exists(cls.PROMPT_FILE):
                with open(cls.PROMPT_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading prompts: {e}")
            return []

    @classmethod
    def save_prompts(cls, prompts):
        try:
            with open(cls.PROMPT_FILE, 'w', encoding='utf-8') as f:
                json.dump(prompts, f, indent=4)
        except Exception as e:
            print(f"Error saving prompts: {e}")


class PromptWorker:
    def __init__(self):
        self.history = []  # Store last 3 outputs
        self.original_prompt = None # Store the original prompt

        self.generate_system_prompt = """
            # ROLE AND PURPOSE
            You are a Prompt Engineering Assistant. Your sole function is to improve and rewrite the given text - removing any ambiguity and leaving minimal room for assumption. NEVER EVER ANSWER OR ATTEMPT TO RESPOND DIRECTLY TO THE QUERY! THIS IS NOT YOUR ROLE OR PLACE TO DO SO. NEVER fabricate, add things or make things up just for the sake of it. This is not the goal either, you are to enhance clarity on the given text removing ambiguity.

            # TASK
            The user will provide a prompt inside `<prompt_to_enhance>` tags. Your one and only job is to rewrite and improve the text found inside these tags according to the guidelines below. You must output ONLY the rewritten text and nothing else.

            # CRITICAL INSTRUCTIONS
            - DO NOT answer or fulfill the prompt found inside the tags.
            - DO NOT engage in conversation.
            - DO NOT provide explanations.
            - DO NOT offer additional context.
            - DO NOT ask questions.
            - DO NOT make suggestions beyond the prompt improvement.

            # OUTPUT REQUIREMENTS
            1. Format: Clean, properly structured text.
            2. Must maintain original intent.
            3. No meta-commentary or notes.
            4. No prefixes or suffixes (e.g., "Enhanced prompt:", "Result:", etc.).
            5. Output only the final, enhanced prompt text.

            # PROMPT ENHANCEMENT GUIDELINES
            Improve the prompt by making it:
            1. SPECIFIC
                - Remove ambiguity
                - Add necessary context
                - Define any unclear terms
                - Specify desired format/style

            2. STRUCTURED
                - Logical flow
                - Clear sections
                - Step-by-step where appropriate
                - Proper paragraph breaks

            3. PRECISE
                - Exact requirements
                - Quantifiable metrics where applicable
                - Clear scope and limitations
                - Defined constraints

            4. ACTIONABLE
                - Clear deliverables
                - Measurable outcomes
                - Explicit instructions
                - Defined success criteria

            {history_context}

            # STRICTLY FORBIDDEN
            - Responding to the prompt.
            - Adding explanatory notes.
            - Including meta-commentary.
            - Engaging in conversation.
            - Offering alternatives.
            - Asking questions.
            - Providing additional or alternate examples.
            - Adding instructions about how to use the prompt.
            """

        self.feedback_system_prompt = """
            You are an AI assistant helping to refine and improve prompts. Your goal is to make prompts clearer and more effective while preserving their core purpose. The user has rejected the last output, it is your role to re-attempt enhancing the given prompt -

            Original prompt to improve:
            {original_prompt}

            Previous version:
            {last_attempt}

            Guidelines for improvement:
            1. Keep what works well from both versions
            2. Identify any unclear or ambiguous parts
            3. Look for opportunities to make instructions more precise
            4. Consider what additional context would be helpful
            5. Focus on practical, usable improvements
            6. Maintain a natural, readable style
            7. Only add structure where it genuinely helps clarity

            Important:
            - Keep the original intent and purpose
            - Avoid making the prompt overly formal or rigid
            - Don't add unnecessary complexity
            - Don't force structure where it isn't needed
            - Focus on making the prompt more effective, not just more detailed

            Return only the improved prompt without any explanations or meta-commentary.
            """

    def update_history(self, prompt):
        self.history.append(prompt)
        if len(self.history) > 3:
            self.history.pop(0)

    def get_history_context(self):
        if not self.history:
            return "No previous attempts available."
        return "\n\n".join([f"Previous attempt {i+1}:\n{prompt}"
                            for i, prompt in enumerate(self.history)])

    def generate_prompt(self, requirements, is_feedback=False):
        try:
            if not is_feedback:
                # For initial generation, store original prompt
                self.original_prompt = requirements
                system_prompt = self.generate_system_prompt.format(
                    history_context=self.get_history_context()
                )
                # THIS IS THE KEY CHANGE: Frame the user input as data
                user_content = f"Please enhance the following prompt:\n\n<prompt_to_enhance>\n{requirements}\n</prompt_to_enhance>"
            else:
                # For feedback, use original prompt and last attempt
                if not self.history:
                    raise Exception("No previous attempts available for feedback.")
                system_prompt = self.feedback_system_prompt.format(
                    original_prompt=self.original_prompt,
                    last_attempt=self.history[-1]
                )
                # You can apply a similar framing here if needed, but the feedback prompt is already structured differently
                user_content = "Please improve this prompt based on the feedback."

            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content} # Use the new framed content
            ]

            response = ollama.chat(model='phi4:14b', messages=messages)

            if not response or 'message' not in response:
                raise Exception("Invalid response from Ollama.")

            result = response['message']['content']
            self.update_history(result)
            return result

        except Exception as e:
            raise Exception(f"Error generating prompt: {str(e)}")



class WorkerThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, prompt_worker, text, is_feedback=False):
        super().__init__()
        self.prompt_worker = prompt_worker
        self.text = text
        self.is_feedback = is_feedback

    def run(self):
        try:
            result = self.prompt_worker.generate_prompt(self.text, self.is_feedback)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))



class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.drag_start_position = None

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(4)

        # Title area with icon
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        # Window icon (replace with your actual icon path)
        self.icon_label = QLabel()
        icon_path = r"C:\Users\Admin\source\repos\Promptly\Promptly.ico"  # Use a raw string for Windows paths
        icon = QIcon(icon_path)
        if not icon.isNull():  # Only set pixmap if icon loads correctly
            icon_pixmap = icon.pixmap(22, 22)
            self.icon_label.setPixmap(icon_pixmap)
        self.icon_label.setFixedSize(22, 22)
        title_layout.addWidget(self.icon_label)

        # Title text
        self.title_label = QLabel("Promptly")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
                margin-left: 4px;
            }
        """)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()  # Push buttons to the right

        self.layout.addLayout(title_layout, stretch=1)  # Add stretch to title layout

        # Window controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(1)  # Reduced spacing

        button_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 0px; /* Remove rounded corners */
                color: #ffffff;
                font-family: "Segoe MDL2 Assets"; /* Correct font for symbols */
                font-size: 10px; /* Smaller font size */
                padding: 0px; /* Remove padding */
                width: 45px; /* Fixed width */
                height: 30px; /* Fixed height */
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1); /* Lighter hover */
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.15); /* Slightly darker press */
            }
        """
        close_button_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 0px;
                color: #ffffff;
                font-family: "Segoe MDL2 Assets";
                font-size: 10px;
                padding: 0px;
                width: 45px;
                height: 30px;
            }
            QPushButton:hover {
                background: #e81123; /* Red hover for close */
            }
            QPushButton:pressed {
                background: #f1707a; /* Darker red press */
            }
        """

        self.minimize_btn = QPushButton("🗕")  # Minimize symbol
        self.maximize_btn = QPushButton("🗖")  # Maximize/Restore symbol
        self.close_btn = QPushButton("🗙")  # Close symbol


        self.minimize_btn.setStyleSheet(button_style)
        self.maximize_btn.setStyleSheet(button_style)
        self.close_btn.setStyleSheet(close_button_style)  # Different style for close

        controls_layout.addWidget(self.minimize_btn)
        controls_layout.addWidget(self.maximize_btn)
        controls_layout.addWidget(self.close_btn)

        self.layout.addLayout(controls_layout)  # Add control buttons
        self.setLayout(self.layout)
        self.setStyleSheet("""
            CustomTitleBar {
                background-color: #1a1a1a; /* Darker background */
                border-bottom: 1px solid #2d2d2d; /* Subtle border */
            }
                          """)

        # Connect buttons
        self.minimize_btn.clicked.connect(self.parent.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.close_btn.clicked.connect(self.parent.close)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.globalPos() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_start_position is not None:
            if not self.parent.isMaximized():  # Only move if not maximized
                self.parent.move(event.globalPos() - self.drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = None
            event.accept()

    def mouseDoubleClickEvent(self, event):  # Add double-click handling
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()
            event.accept()

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.maximize_btn.setText("🗖")  # Restore icon
        else:
            self.parent.showMaximized()
            self.maximize_btn.setText("🗗")  # Maximized icon

class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #292929;
                border: none;
                border-radius: 8px;
            }
        """)
        self.add_shadow()

    def add_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 30))  # Reduced opacity for subtlety
        shadow.setOffset(0, 2)  # Smaller offset
        self.setGraphicsEffect(shadow)


class ActionButton(QPushButton):
    def __init__(self, text, icon_text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
            QPushButton:disabled {
                background-color: #7f8c8d; /* Greyed out */
                color: #bdc3c7; /* Lighter text */
            }
        """)
        if icon_text:  # Add icon text if provided
            self.setText(f"{icon_text} {text}")

class LoadingSpinner(QWidget):
    def __init__(self, parent=None, centerOnParent=True, disableParentWhenSpinning=True, modality=Qt.NonModal):
        super().__init__(parent)

        self._centerOnParent = centerOnParent
        self._disableParentWhenSpinning = disableParentWhenSpinning

        # We'll handle modality a bit differently
        self.setWindowModality(modality)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # Important for staying on top
        self.setAttribute(Qt.WA_TranslucentBackground) # Make the background transparent


        # Animation Properties
        self._numberOfDots = 3          # Number of dots
        self._dotSize = 4               # Dot size
        self._spacing = 16
        self._animationDuration = 1200    # Total duration for one cycle
        self._maxSteps = 60              # Number of steps to reach max/min size
        self._currentStep = 0
        self._color = QColor("#3498db") # Dot color

        # Timer setup
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.nextAnimationStep)
        self._timer.setInterval(int(self._animationDuration / self._maxSteps))
        #print(f"Timer interval: {self._timer.interval()} ms")

        # Pre-calculate size based on dots
        width = (self._numberOfDots * (self._dotSize * 2)) + ((self._numberOfDots - 1) * self._spacing)
        self.setFixedSize(width + 10, self._dotSize * 4)  # Add a bit of padding
        self.hide()



    def paintEvent(self, event):
        self.updatePosition()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Center the spinner
        centerY = self.height() / 2
        totalWidth = (self._numberOfDots * (self._dotSize * 2)) + ((self._numberOfDots - 1) * self._spacing)
        startX = (self.width() - totalWidth) / 2

        for i in range(self._numberOfDots):
            x = startX + (i * (self._dotSize * 2 + self._spacing))  # Corrected x-coordinate

            # Calculate phase offset for each dot
            phase = (self._currentStep + (i * (self._maxSteps / self._numberOfDots))) % self._maxSteps

            # Smooth sine wave for scale and opacity
            scale = 0.5 + (math.sin(2 * math.pi * phase / self._maxSteps) + 1) * 0.25  # Scale between 0.5 and 1.0
            opacity = 0.3 + (math.sin(2 * math.pi * phase / self._maxSteps) + 1) * 0.35 # Opacity between 0.4 and 1.0


            color = QColor(self._color)
            color.setAlphaF(opacity)  # Use setAlphaF for floating-point alpha
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)  # No outline

            radius = self._dotSize * scale  # Calculate radius based on scale
            painter.drawEllipse(QPointF(x + self._dotSize, centerY), radius, radius)


    def start(self):
        self.updatePosition()  # Ensure position is correct before showing
        self.show()
        if self.parentWidget() and self._disableParentWhenSpinning:
            self.parentWidget().setEnabled(False)

        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self.hide()
        if self.parentWidget() and self._disableParentWhenSpinning:
            self.parentWidget().setEnabled(True)

        if self._timer.isActive():
            self._timer.stop()
            self._currentStep = 0  # Reset animation

    def updatePosition(self):
        if self.parentWidget() and self._centerOnParent:
            parentRect = self.parentWidget().rect()
            self.move(parentRect.center() - self.rect().center())

    def nextAnimationStep(self):
        self._currentStep = (self._currentStep + 1) % self._maxSteps
        self.update() # Call update to trigger a repaint


    # Keep these for compatibility, even if not used directly
    def setNumberOfLines(self, lines): pass  # Placeholder
    def setLineLength(self, length): pass    # Placeholder
    def setLineWidth(self, width): pass     # Placeholder
    def setInnerRadius(self, radius): pass  # Placeholder


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Formatting rules (store QFont and QTextCharFormat)
        self.formats = {
            'header': self.create_format('#3498db', True),  # Blue and bold
            'bold': self.create_format('#e74c3c', True),    # Red and bold
            'emphasis': self.create_format('#2ecc71'),      # Green
            'code': self.create_format('#9b59b6'),          # Purple
            'list': self.create_format('#f1c40f'),          # Yellow
        }

        # Regex patterns
        self.patterns = [
            (r'^\s*#{1,6}\s+.*$', 'header'),  # Headers (leading whitespace)
            (r'\*\*([^*]+)\*\*', 'bold'),     # Bold with **
            (r'^\s*[-*]\s+', 'list'),        # List items (leading whitespace)
            (r'`([^`]+)`', 'code'),          # Inline code
            (r'\*([^*]+)\*', 'emphasis'),   # Emphasis with *
            (r'_{2}([^_]+)_{2}', 'bold'),    # Bold with __ (consistent)
            (r'_([^_]+)_', 'emphasis'),      # Emphasis with _
        ]


    def create_format(self, color, bold=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        return fmt

    def highlightBlock(self, text):
        for pattern, format_name in self.patterns:
            for match in re.finditer(pattern, text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, self.formats[format_name])


class FormattedTextEdit(QTextEdit):
    def __init__(self, placeholder_text="", parent=None, is_output=False):
        super().__init__(parent)
        self.is_output = is_output
        self.setPlaceholderText(placeholder_text)

        # Set up the document styling
        doc = self.document()
        doc.setDocumentMargin(16)  # Consistent margin

        # Base font configuration
        font = QFont("Segoe UI", 10)
        font.setStyleStrategy(QFont.PreferAntialias)  # For smoother text
        self.setFont(font)

        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)  # Wrap long lines
        self.setLayoutDirection(Qt.LeftToRight)  # Ensure correct text direction

        # Set up default styles for different elements (using CSS-like syntax)
        self.document().setDefaultStyleSheet("""
            /* Base text styling */
            body {
                color: #E8E8E8;  /* Light grey text */
                line-height: 1.6; /* Comfortable line spacing */
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }

            /* Headers */
            h1, h2, h3, h4, h5, h6 {
                color: #3498db;  /* Blue headers */
                font-weight: 600;
                margin: 16px 0 8px 0; /* Top, Right, Bottom, Left */
                padding: 0;
            }
            h1 { font-size: 18px; }
            h2 { font-size: 16px; }
            h3 { font-size: 14px; }

            /* Paragraphs */
            p {
                margin: 8px 0;
                padding: 0;
                line-height: 1.6;
            }

            /* Lists */
            ul, ol {
                margin: 8px 0;
                padding-left: 24px; /* Indent lists */
            }
            li {
                margin: 4px 0;
                padding: 0;
                line-height: 1.6;
            }
            /* Ordered list specific */
            ol {
                counter-reset: item;
                list-style-type: none; /* Remove default numbers */
                padding-left: 0;
            }
            ol > li {
                counter-increment: item;
                padding-left: 24px; /* Space for the number */
                position: relative; /* For absolute positioning of :before */
            }
            ol > li:before {
                content: counter(item) "."; /* Show number */
                color: #3498db; /* Number color */
                position: absolute;
                left: 0;
                width: 20px;    /*Fixed width*/
                text-align: right;
                margin-right: 4px; /* Space between number and text */

            }

            /* Unordered list specific */
            ul {
              list-style-type: none;  /* Remove default bullets */
              padding-left: 0; /* Remove default indent */
            }

            ul > li {
              padding-left: 24px;   /*Consistent with Ol*/
              position: relative;     /*For absolute*/
            }

            ul > li:before {
              content: "•";         /* Bullet character */
              color: #3498db;      /* Bullet color */
              position: absolute;
              left: 8px;           /* Position the bullet */

            }

            /* Bold and emphasis */
            b, strong {
                color: #3498db;
                font-weight: 600;
            }
            i, em {
                color: #2ecc71;
                font-style: italic;
            }

            /* Code blocks */
            code {
                font-family: 'Consolas', monospace;
                background-color: #2d2d2d;
                padding: 2px 4px;
                border-radius: 3px;
                color: #9b59b6; /* Purple */
            }

            /* Block quotes */
            blockquote {
                margin: 8px 0;
                padding: 8px 16px;
                border-left: 4px solid #3498db;
                background-color: #2d2d2d;  /* Dark grey */
            }

            /* Horizontal rule */
            hr {
                border: none;
                height: 1px;
                background-color: #333333;
                margin: 16px 0;
            }
        """)

        # Set up the widget styling (different for input and output)
        if is_output:
            self.setReadOnly(True)
            style = """
                QTextEdit {
                    background-color: #242424;  /* Slightly lighter background */
                    color: #E8E8E8;
                    border: 1px solid #333333;
                    border-radius: 4px;
                    selection-background-color: #264F78; /* Highlight color */
                    selection-color: #ffffff;
                    padding: 12px; /* More padding */
                }
                QTextEdit:focus {
                    border: 1px solid #3498db;  /* Blue border on focus */
                }

                /* Scrollbar styling */
                QScrollBar:vertical {
                    border: none;
                    background: #1E1E1E;
                    width: 12px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: #424242;
                    min-height: 20px;
                    border-radius: 6px;
                    margin: 2px; /* Small margin around the handle */
                }
                QScrollBar::handle:vertical:hover {
                    background: #525252; /* Slightly lighter on hover */
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0; /* Hide the arrows */
                    background: none;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none; /* No background for scrollbar area */
                }
            """
        else:  # Input field
            style = """
                QTextEdit {
                    background-color: #1E1E1E; /* Dark background */
                    color: #D4D4D4; /* Light grey text */
                    border: 1px solid #333333; /* Darker border */
                    border-radius: 4px;
                    selection-background-color: #264F78; /* Blue selection */
                    selection-color: #ffffff;
                    padding: 12px;
                }
                QTextEdit:focus {
                    border: 1px solid #3498db; /* Blue border on focus */
                }
                QTextEdit::placeholder {
                    color: #666666; /* Darker placeholder text */
                    font-style: italic;
                }
            """
        self.setStyleSheet(style)

    def insertFromMimeData(self, source):
        """Handle pasted text properly"""
        if source.hasText():
            self.insertPlainText(source.text())  # Insert as plain text to avoid formatting issues




class PromptEngineerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(r"C:\Users\Admin\source\repos\Promptly\Promptly.ico"))  # Replace with your icon path
        self.setWindowTitle("Promptly")
        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; }")  # Dark background
        self.setWindowFlag(Qt.FramelessWindowHint)  # Remove default title bar

        self.prompt_worker = PromptWorker()
        self.setup_ui()
        self.setup_system_tray()

        # Initialize the highlighter and evaluator *here*
        self.highlighter = MarkdownHighlighter(self.generated_text.document())
        self.prompt_evaluator = PromptEvaluator()

        self.generate_spinner = LoadingSpinner(self.generated_text)
        self.generate_spinner.setNumberOfLines(12)
        self.generate_spinner.setLineLength(12)
        self.generate_spinner.setLineWidth(4)
        self.generate_spinner.setInnerRadius(12)


    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(r"C:\Users\Admin\source\repos\Promptly\Promptly.ico"))  # Replace with your icon path
        self.tray_icon.setToolTip("Promptly")

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #292929;
                border: 1px solid #333333;
                color: #ffffff;
            }
            QMenu::item {
                padding: 8px 20px; /* Add some padding */
            }
            QMenu::item:selected {
                background-color: #3498db; /* Blue selection */
            }
        """)
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show_window)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)


    def setup_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        main_layout.setSpacing(0) # Remove Spacing

        # Add custom title bar
        title_bar = CustomTitleBar(self)  # Pass 'self' (the main window)
        main_layout.addWidget(title_bar)

        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)  # Consistent margins
        content_layout.setSpacing(16)

        # Input Section
        input_card = Card()  # Use the Card class
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(16, 16, 16, 16)
        input_layout.setSpacing(12)

        # Input header
        input_header = QLabel("Input Prompt")
        input_header.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        input_layout.addWidget(input_header)

        # Input text area
        self.req_text = QTextEdit()  # Use regular QTextEdit
        self.req_text.setPlaceholderText("Enter your prompt here...")
        self.req_text.setStyleSheet("""
            QTextEdit {
                background-color: #242424; /* Slightly lighter background */
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                line-height: 1.4;
            }
            QTextEdit:focus {
                border: 1px solid #3498db; /* Blue border on focus */
            }
        """)
        input_layout.addWidget(self.req_text)



        # Button container (for horizontal layout)
        button_container = QWidget()  # Use a container
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 8, 0, 0)  # Remove margins


        # Generate button (icon only, no text)
        self.generate_button = QPushButton()
        self.generate_button.setIcon(QIcon(r"C:\Users\Admin\source\repos\Promptly\asset\gen.png"))  # Replace with your icon path
        self.generate_button.setIconSize(QSize(20, 20))  # Adjust size as needed
        self.generate_button.setToolTip("Generate Enhanced Prompt")
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 8px;
                min-width: 36px; /* Minimum width for the button */
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1); /* Lighter hover */
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15); /* Slightly darker press */
            }
            QPushButton:disabled {
                opacity: 0.5; /* Reduce opacity when disabled */
            }
        """)

        # Feedback button (icon only)
        self.feedback_button = QPushButton()
        self.feedback_button.setIcon(QIcon(r"C:\Users\Admin\source\repos\Promptly\asset\dislike.png"))  # Replace with your icon path
        self.feedback_button.setIconSize(QSize(20, 20))
        self.feedback_button.setToolTip("Give Feedback & Retry")
        self.feedback_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 8px;
                min-width: 36px;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:disabled {
                opacity: 0.5;
            }
        """)

        button_layout.addStretch()  # Push buttons to the center
        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.feedback_button)
        button_layout.addStretch()  # Push buttons to the center

        input_layout.addWidget(button_container)  # Add the container to the input layout

        # Output section
        output_card = Card()
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(16, 16, 16, 16)
        output_layout.setSpacing(12)

        # Output header (with copy button)
        header_container = QWidget()  # Container for horizontal layout
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        output_header = QLabel("Enhanced Prompt")
        output_header.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        
        self.evaluate_button = QPushButton()
        self.evaluate_button.setIcon(QIcon(r"C:\Users\Admin\source\repos\Sapphire - PrismXL\Sapphire - PrismXL\assets\notice.png"))  # Use a suitable icon
        self.evaluate_button.setIconSize(QSize(20, 20))
        self.evaluate_button.setToolTip("Evaluate Prompt Improvement")
        self.evaluate_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 8px;
                min-width: 36px;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:disabled {
                opacity: 0.5;
            }
        """)
        button_layout.addWidget(self.evaluate_button)
        self.evaluate_button.clicked.connect(self.evaluate_prompt)
        self.evaluate_button.setEnabled(False)  # Initially disabled

        # Copy button (icon only)
        self.copy_button = QPushButton()
        self.copy_button.setIcon(QIcon(r"C:\Users\Admin\source\repos\Promptly\asset\copy.png"))  # Replace with your icon path
        self.copy_button.setIconSize(QSize(26, 26))  # Slightly larger
        self.copy_button.setToolTip("Copy to Clipboard")
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px; /* Smaller padding */
                min-width: 24px; /* Minimum width */
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.copy_button.clicked.connect(self.copy_to_clipboard)

        header_layout.addWidget(output_header)
        header_layout.addStretch()  # Push copy button to the right
        header_layout.addWidget(self.copy_button)

        output_layout.addWidget(header_container)

        # Output text area
        self.generated_text = FormattedTextEdit(is_output=True)  # Use the custom text edit
        output_layout.addWidget(self.generated_text)

        # Add cards to the main content layout
        content_layout.addWidget(input_card, stretch=1)  # Add stretch to make them equal size
        content_layout.addWidget(output_card, stretch=1)

        main_layout.addWidget(content_widget) # Add content into the main layout
        self.setCentralWidget(central_widget)

        # Connect button actions
        self.generate_button.clicked.connect(self.generate_prompt)
        self.feedback_button.clicked.connect(self.regenerate_with_feedback)
        
        # Set a reasonable minimum size
        self.setMinimumSize(600, 500)


    def evaluate_prompt(self):
        original_prompt = self.req_text.toPlainText().strip()
        enhanced_prompt = self.generated_text.toPlainText().strip()

        if not original_prompt or not enhanced_prompt:
            self.show_error("Both original and enhanced prompts are required for evaluation.")
            return

        self.evaluate_button.setEnabled(False)  # Disable while evaluating

        # Create and *use* the EvaluationDialog
        self.eval_dialog = EvaluationDialog(None, self)  # Create the dialog *here*

        # Create evaluation thread
        self.eval_thread = EvalWorkerThread(self.prompt_evaluator, original_prompt, enhanced_prompt)

        # Connect signals
        self.eval_thread.finished.connect(self.handle_evaluation_results)
        self.eval_thread.error.connect(lambda e: self.show_error(f"Evaluation error: {e}"))
        self.eval_thread.start()
        self.eval_dialog.show() #show the evaluation dialog


    def handle_evaluation_results(self, metrics):
        if self.eval_dialog:  # Check if the dialog exists
            self.eval_dialog.update_ui(metrics)  # Update the *existing* dialog
            #self.eval_dialog.exec_() #exec is only if you make a NEW dialog, we don't want that.
        self.evaluate_button.setEnabled(True)


    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        text = self.generated_text.toPlainText()
        clipboard.setText(text)

        # Show a brief tooltip confirmation
        QToolTip.showText(
            self.copy_button.mapToGlobal(QPoint(0, -30)),  # Position above the button
            "Copied to clipboard!",
            self.copy_button,
            QRect(),  # Use default rect
            1500  # Hide after 1.5 seconds
        )

    def generate_prompt(self):
        requirements = self.req_text.toPlainText().strip()
        if not requirements:
            self.show_error("Please enter prompt requirements.")
            return

        self.generate_button.setEnabled(False)  # Disable button during generation
        self.generate_spinner.start()  # Start the spinner
        self.generated_text.clear()  # Clear previous output

        self.worker_thread = WorkerThread(self.prompt_worker, requirements)
        self.worker_thread.finished.connect(self.handle_generation_response)
        self.worker_thread.error.connect(self.handle_error)
        self.worker_thread.finished.connect(self.generate_spinner.stop) # Stop spinner
        self.worker_thread.finished.connect(lambda: self.generate_button.setEnabled(True))  # Re-enable
        self.worker_thread.error.connect(self.generate_spinner.stop)
        self.worker_thread.error.connect(lambda: self.generate_button.setEnabled(True))

        self.worker_thread.start()


    def regenerate_with_feedback(self):
        requirements = self.req_text.toPlainText().strip()
        if not requirements:
            self.show_error("Please enter prompt requirements.")
            return

        # Clear the output *before* starting generation.
        self.generated_text.clear()

        self.generate_button.setEnabled(False)
        self.feedback_button.setEnabled(False)  # Disable feedback button too
        self.generate_spinner.start()

        self.worker_thread = WorkerThread(self.prompt_worker, requirements, is_feedback=True)
        self.worker_thread.finished.connect(self.handle_generation_response)
        self.worker_thread.error.connect(self.handle_error)
        self.worker_thread.finished.connect(self.generate_spinner.stop)
        self.worker_thread.finished.connect(lambda: self.generate_button.setEnabled(True))
        self.worker_thread.finished.connect(lambda: self.feedback_button.setEnabled(True))  # Re-enable
        self.worker_thread.error.connect(self.generate_spinner.stop)
        self.worker_thread.error.connect(lambda: self.generate_button.setEnabled(True))
        self.worker_thread.error.connect(lambda: self.feedback_button.setEnabled(True))  # Re-enable
        self.worker_thread.start()

    def handle_generation_response(self, response):
        """Converts Markdown response to HTML and displays it."""
        # Convert the raw markdown text from the AI into HTML
        html_content = markdown.markdown(response, extensions=['fenced_code', 'tables'])

        # The setHtml method will now correctly render the rich text
        # because the HTML is properly formatted by the library.
        # Your existing CSS in FormattedTextEdit will style it automatically.
        self.generated_text.setHtml(html_content)

        self.evaluate_button.setEnabled(True)  # Enable evaluate button
        self.tray_icon.showMessage(
            "Prompt Generated",
            "New prompt is ready for review",
            QSystemTrayIcon.Information,
            3000  # milliseconds
        )

    def show_error(self, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle("Error")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def handle_error(self, error_message):
        self.show_error(error_message)
        self.tray_icon.showMessage(
            "Error",
            error_message,
            QSystemTrayIcon.Critical,
            3000
        )
    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()  # Hide the main window
            event.ignore() # Prevent the app from closing
        else:
            event.accept()  # Close if tray icon is not visible


    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

    def show_window(self):
        self.showNormal()  # Restore the window
        self.activateWindow() # Bring it to the front


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use a consistent style

    # Dark palette for a modern look
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor("#1e1e1e"))
    dark_palette.setColor(QPalette.WindowText, QColor("#ffffff"))
    dark_palette.setColor(QPalette.AlternateBase, QColor("#292929"))
    dark_palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    dark_palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
    dark_palette.setColor(QPalette.Text, QColor("#ffffff"))
    dark_palette.setColor(QPalette.Button, QColor("#292929"))
    dark_palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor("#3498db"))
    dark_palette.setColor(QPalette.Highlight, QColor("#3498db"))
    dark_palette.setColor(QPalette.HighlightedText, QColor("#000000"))
    dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#7f8c8d"))  # Greyed-out text
    app.setPalette(dark_palette)

    window = PromptEngineerApp()
    window.show()
    sys.exit(app.exec_())
