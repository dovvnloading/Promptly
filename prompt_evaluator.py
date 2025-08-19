import json
import ollama
from dataclasses import dataclass
from typing import List, Dict
from PyQt5.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QLabel,  # Import QMainWindow
                             QTextEdit, QProgressBar, QWidget, QFrame,
                             QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QIcon  # Import QIcon


@dataclass
class EvaluationMetrics:
    clarity_score: float
    specificity_score: float
    actionability_score: float
    overall_improvement: float
    improvement_details: List[str]
    suggestions: List[str]

class CustomTitleBar(QWidget):  # Title bar from PromptEngineerApp
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
        
        # Window icon (you'll need to provide a suitable icon path)
        self.icon_label = QLabel()
        icon_path = r"C:\Users\Admin\source\repos\Promptly\Promptly.ico"  # Replace with YOUR icon path.
        icon = QIcon(icon_path)
        if not icon.isNull():
            icon_pixmap = icon.pixmap(22, 22)
            self.icon_label.setPixmap(icon_pixmap)
        self.icon_label.setFixedSize(22, 22)
        title_layout.addWidget(self.icon_label)
        
        # Title text
        self.title_label = QLabel("Prompt Evaluation") # Changed the Label
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
                margin-left: 4px;
            }
        """)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        self.layout.addLayout(title_layout, stretch=1)

        # Window controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(1)

        button_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 0px;
                color: #ffffff;
                font-family: Segoe MDL2 Assets;
                font-size: 10px;
                padding: 0px;
                width: 45px;
                height: 30px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.15);
            }
        """

        close_button_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 0px;
                color: #ffffff;
                font-family: Segoe MDL2 Assets;
                font-size: 10px;
                padding: 0px;
                width: 45px;
                height: 30px;
            }
            QPushButton:hover {
                background: #e81123;
            }
            QPushButton:pressed {
                background: #f1707a;
            }
        """

        self.minimize_btn = QPushButton("🗕")
        self.maximize_btn = QPushButton("🗖")
        self.close_btn = QPushButton("🗙")

        self.minimize_btn.setStyleSheet(button_style)
        self.maximize_btn.setStyleSheet(button_style)
        self.close_btn.setStyleSheet(close_button_style)

        controls_layout.addWidget(self.minimize_btn)
        controls_layout.addWidget(self.maximize_btn)
        controls_layout.addWidget(self.close_btn)

        self.layout.addLayout(controls_layout)
        self.setLayout(self.layout)

        # Set up the title bar styling
        self.setStyleSheet("""
            CustomTitleBar {
                background-color: #1a1a1a;
                border-bottom: 1px solid #2d2d2d;
            }
        """)
        
        #connect buttons
        self.minimize_btn.clicked.connect(self.parent.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.close_btn.clicked.connect(self.parent.close)



    def mousePressEvent(self, event):
      if event.button() == Qt.LeftButton:
          self.drag_start_position = event.globalPos() - self.parent.frameGeometry().topLeft()
          event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_start_position is not None:
            if not self.parent.isMaximized():
                self.parent.move(event.globalPos() - self.drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = None
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.parent.isMaximized():
                self.parent.showNormal()
            else:
                self.parent.showMaximized()
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
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

class EvaluationDialog(QMainWindow):  # Inherit from QMainWindow
    def __init__(self, metrics: EvaluationMetrics, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.FramelessWindowHint) # Add this line - VERY IMPORTANT
        self.setWindowTitle("Prompt Evaluation")
        self.setFixedSize(500, 700)
        self.setStyleSheet("""
             QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
            QProgressBar {
                border: none;
                background-color: #333333;
                height: 8px;
                text-align: center;
                border-radius: 4px;
                margin-top: 4px;
                margin-bottom: 4px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #242424;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.4;
            }
        """)

        central_widget = QWidget(self)  # Create a central widget
        self.setCentralWidget(central_widget) # Set the central widget

        layout = QVBoxLayout(central_widget)  # Use central_widget as parent
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        layout.setSpacing(0)

        # Add custom title bar
        title_bar = CustomTitleBar(self)  # Pass 'self' (the QMainWindow)
        layout.addWidget(title_bar)

        # Content area (within the central widget)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)


        # Overall score card (will be populated later)
        self.score_card = Card(self)
        self.score_layout = QVBoxLayout(self.score_card)
        self.score_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.addWidget(self.score_card)

        # Improvements card (will be populated later)
        self.improvements_card = Card(self)
        self.improvements_layout = QVBoxLayout(self.improvements_card)
        self.improvements_layout.setContentsMargins(16, 16, 16, 16)
        self.improvements_layout.setSpacing(8)
        content_layout.addWidget(self.improvements_card)


        # Suggestions card (will be populated later)
        self.suggestions_card = Card(self)
        self.suggestions_layout = QVBoxLayout(self.suggestions_card)
        self.suggestions_layout.setContentsMargins(16, 16, 16, 16)
        self.suggestions_layout.setSpacing(8)
        content_layout.addWidget(self.suggestions_card)

        layout.addWidget(content_widget) #add the content to the main layout

    def update_ui(self, metrics: EvaluationMetrics):
        """Updates the UI with the evaluation results."""

        # Clear previous content
        for i in reversed(range(self.score_layout.count())):
            self.score_layout.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.improvements_layout.count())):
            self.improvements_layout.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.suggestions_layout.count())):
            self.suggestions_layout.itemAt(i).widget().setParent(None)
            

        # Overall score
        overall = QLabel(f"Overall Improvement: {metrics.overall_improvement:.1f}%")
        overall.setStyleSheet("font-size: 24px; color: #3498db; font-weight: bold;")
        self.score_layout.addWidget(overall, alignment=Qt.AlignCenter)

        # Progress bars
        for label, value in [
            ("Clarity", metrics.clarity_score),
            ("Specificity", metrics.specificity_score),
            ("Actionability", metrics.actionability_score)
        ]:
            metric_layout = QHBoxLayout()
            label_widget = QLabel(f"{label}:")
            label_widget.setMinimumWidth(100)
            progress = QProgressBar()
            progress.setValue(int(value))
            progress.setFormat(f"{value:.1f}%")
            progress.setTextVisible(True)
            metric_layout.addWidget(label_widget)
            metric_layout.addWidget(progress)
            self.score_layout.addLayout(metric_layout)


        # Improvements
        self.improvements_layout.addWidget(QLabel("Improvements Made"))
        improvements_text = QTextEdit()
        improvements_text.setPlainText("\n".join(f"• {imp}" for imp in metrics.improvement_details))
        improvements_text.setReadOnly(True)
        improvements_text.setMinimumHeight(200)
        self.improvements_layout.addWidget(improvements_text)

        # Suggestions
        self.suggestions_layout.addWidget(QLabel("Further Suggestions"))
        suggestions_text = QTextEdit()
        suggestions_text.setPlainText("\n".join(f"• {sug}" for sug in metrics.suggestions))
        suggestions_text.setReadOnly(True)
        suggestions_text.setMinimumHeight(150)
        self.suggestions_layout.addWidget(suggestions_text)



class EvalWorkerThread(QThread):
    finished = pyqtSignal(object)  # Signal for finished with results
    error = pyqtSignal(str)      # Signal for errors

    def __init__(self, evaluator, original, enhanced):
        super().__init__()
        self.evaluator = evaluator
        self.original = original
        self.enhanced = enhanced

    def run(self):
        try:
            result = self.evaluator.evaluate(self.original, self.enhanced)
            self.finished.emit(result)  # Emit results
        except Exception as e:
            print(f"Thread error: {str(e)}")
            self.error.emit(str(e))  # Emit error message


class PromptEvaluator:
    def __init__(self):
        self.system_prompt = """
        # ROLE AND PURPOSE
        You are a Prompt Evaluation Agent ... (rest of your system prompt)
        """
        self.system_prompt = """# ROLE AND PURPOSE
        You are a Prompt Evaluation Agent specialized in analyzing and comparing prompts to determine improvements and effectiveness. Your role is to evaluate an original prompt against its enhanced version.

        # CRITICAL REQUIREMENTS
        - Provide ONLY analytical evaluation
        - Focus on measurable improvements
        - Stay neutral and objective
        - DO NOT attempt to further improve or rewrite prompts
        - DO NOT engage in conversation
        - DO NOT provide explanations beyond evaluation metrics
        - DO NOT answer or execute the prompts

        # EVALUATION CRITERIA
        1.  Clarity (0-100):
            - Clear instructions
            - Unambiguous language
            - Logical structure

        2.  Specificity (0-100):
            - Detailed requirements
            - Precise constraints
            - Defined parameters

        3.  Actionability (0-100):
            - Clear deliverables
            - Measurable outcomes
            - Implementation guidance

        # OUTPUT FORMAT
        Provide a JSON object with:
        {
            "metrics": {
                "clarity_score": float,
                "specificity_score": float,
                "actionability_score": float,
                "overall_improvement": float
            },
            "improvement_details": [
                "specific improvement point 1",
                "specific improvement point 2"
            ],
            "suggestions": [
                "potential improvement 1",
                "potential improvement 2"
            ]
        }

        # SCORING GUIDELINES
        - Scores should be 0-100
        - Overall improvement is weighted average:
          - Clarity: 40%
          - Specificity: 35%
          - Actionability: 25%
        """

    def evaluate(self, original_prompt: str, enhanced_prompt: str) -> EvaluationMetrics:
        try:
            messages = [
                {'role': 'system', 'content': self.system_prompt},
                {'role': 'user', 'content': f"""
                Original Prompt:
                {original_prompt}

                Enhanced Prompt:
                {enhanced_prompt}

                Evaluate the improvement and provide metrics in the specified JSON format.
                """}
            ]

            response = ollama.chat(model='phi4:14b', messages=messages)

            if not response or 'message' not in response:
                raise Exception("Invalid response from evaluation model")

            result = self._extract_json(response['message']['content'])

            if not result:
                raise Exception("Could not parse evaluation results")


            return EvaluationMetrics(
                clarity_score=result['metrics']['clarity_score'],
                specificity_score=result['metrics']['specificity_score'],
                actionability_score=result['metrics']['actionability_score'],
                overall_improvement=result['metrics']['overall_improvement'],
                improvement_details=result['improvement_details'],
                suggestions=result['suggestions']
            )

        except Exception as e:
            print(f"Error in evaluate: {str(e)}")
            raise Exception(f"Error during prompt evaluation: {str(e)}")

    def _extract_json(self, content: str) -> Dict:
        """Extracts a JSON object from the given string content."""
        try:
            # Find the start and end of the JSON object
            start = content.find('{')
            end = content.rfind('}') + 1  # Include the closing brace
            if start >= 0 and end > start:
                json_str = content[start:end]
                return json.loads(json_str)
            raise Exception("No valid JSON found in response")  # More specific exception
        except Exception as e:
            print(f"Error extracting JSON: {str(e)}")
            raise  # Re-raise the exception to be caught by the caller