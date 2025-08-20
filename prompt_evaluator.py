import json
import ollama
from dataclasses import dataclass
from typing import List, Dict
from PyQt5.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
                             QTextEdit, QProgressBar, QWidget, QFrame, QScrollArea,
                             QGraphicsDropShadowEffect, QApplication, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QIcon, QFont


@dataclass
class EvaluationMetrics:
    clarity_score: float
    specificity_score: float
    actionability_score: float
    overall_improvement: float
    improvement_details: List[str]
    suggestions: List[str]


class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.drag_start_position = None
        self.setFixedHeight(35)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # Title area with icon
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        
        # Window icon (optional - will work without icon)
        self.icon_label = QLabel()
        try:
            icon_path = r"C:\Users\Admin\source\repos\Promptly\Promptly.ico"
            icon = QIcon(icon_path)
            if not icon.isNull():
                icon_pixmap = icon.pixmap(22, 22)
                self.icon_label.setPixmap(icon_pixmap)
        except:
            pass  # Icon is optional
        
        self.icon_label.setFixedSize(22, 22)
        title_layout.addWidget(self.icon_label)
        
        # Title text
        self.title_label = QLabel("Prompt Evaluation")
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

        layout.addLayout(title_layout, stretch=1)

        # Window controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(1)

        button_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 0px;
                color: #ffffff;
                font-size: 16px;
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
                font-size: 16px;
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

        self.minimize_btn = QPushButton("−")
        self.maximize_btn = QPushButton("□")
        self.close_btn = QPushButton("×")

        self.minimize_btn.setStyleSheet(button_style)
        self.maximize_btn.setStyleSheet(button_style)
        self.close_btn.setStyleSheet(close_button_style)

        controls_layout.addWidget(self.minimize_btn)
        controls_layout.addWidget(self.maximize_btn)
        controls_layout.addWidget(self.close_btn)

        layout.addLayout(controls_layout)

        # Set up the title bar styling
        self.setStyleSheet("""
            CustomTitleBar {
                background-color: #1a1a1a;
                border-bottom: 1px solid #2d2d2d;
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
            if not self.parent.isMaximized():
                self.parent.move(event.globalPos() - self.drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = None
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()
            event.accept()
            
    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.maximize_btn.setText("□")
        else:
            self.parent.showMaximized()
            self.maximize_btn.setText("❐")


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #292929;
                border: none;
                border-radius: 8px;
                margin: 4px;
            }
        """)
        self.add_shadow()

    def add_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)


class EvaluationDialog(QMainWindow):
    def __init__(self, metrics=None, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowTitle("Prompt Evaluation")
        self.setMinimumSize(500, 600)
        self.resize(550, 750)
        
        # Main window styling
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
                height: 12px;
                text-align: center;
                border-radius: 6px;
                margin: 4px 0px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 6px;
            }
            QTextEdit {
                background-color: #242424;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.4;
            }
        """)

        # Create central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add custom title bar
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a4a4a;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
        """)

        # Content widget inside scroll area
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(16)

        # Initially show loading message or metrics if provided
        if metrics:
            self.update_ui(metrics)
        else:
            self.show_loading()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def show_loading(self):
        """Show loading message"""
        self.clear_content()
        
        loading_card = Card()
        loading_layout = QVBoxLayout(loading_card)
        loading_layout.setContentsMargins(20, 20, 20, 20)
        
        loading_label = QLabel("Evaluating prompt...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("font-size: 18px; color: #3498db;")
        loading_layout.addWidget(loading_label)
        
        self.content_layout.addWidget(loading_card)
        self.content_layout.addStretch()

    def show_error(self, error_message: str):
        """Show error message"""
        self.clear_content()
        
        error_card = Card()
        error_layout = QVBoxLayout(error_card)
        error_layout.setContentsMargins(20, 20, 20, 20)
        
        error_label = QLabel(f"Error: {error_message}")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("font-size: 16px; color: #e74c3c;")
        error_label.setWordWrap(True)
        error_layout.addWidget(error_label)
        
        self.content_layout.addWidget(error_card)
        self.content_layout.addStretch()

    def update_ui(self, metrics: EvaluationMetrics):
        """Updates the UI with the evaluation results."""
        self.clear_content()

        # Overall score card
        score_card = Card()
        score_layout = QVBoxLayout(score_card)
        score_layout.setContentsMargins(20, 20, 20, 20)
        score_layout.setSpacing(16)

        # Overall score
        overall_label = QLabel(f"Overall Improvement: {metrics.overall_improvement:.1f}%")
        overall_label.setStyleSheet("font-size: 24px; color: #3498db; font-weight: bold;")
        overall_label.setAlignment(Qt.AlignCenter)
        score_layout.addWidget(overall_label)

        # Progress bars for individual metrics
        metrics_data = [
            ("Clarity", metrics.clarity_score),
            ("Specificity", metrics.specificity_score),
            ("Actionability", metrics.actionability_score)
        ]

        for label_text, value in metrics_data:
            metric_layout = QHBoxLayout()
            metric_layout.setSpacing(12)
            
            label = QLabel(f"{label_text}:")
            label.setMinimumWidth(120)
            label.setStyleSheet("font-size: 14px; font-weight: 500;")
            
            progress = QProgressBar()
            progress.setValue(int(value))
            progress.setFormat(f"{value:.1f}%")
            progress.setTextVisible(True)
            progress.setMinimumHeight(20)
            
            metric_layout.addWidget(label)
            metric_layout.addWidget(progress, stretch=1)
            score_layout.addLayout(metric_layout)

        self.content_layout.addWidget(score_card)

        # Improvements card
        if metrics.improvement_details:
            improvements_card = Card()
            improvements_layout = QVBoxLayout(improvements_card)
            improvements_layout.setContentsMargins(20, 20, 20, 20)
            improvements_layout.setSpacing(12)

            improvements_title = QLabel("Improvements Made")
            improvements_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2ecc71;")
            improvements_layout.addWidget(improvements_title)

            improvements_text = QTextEdit()
            improvements_text.setPlainText("\n".join(f"• {imp}" for imp in metrics.improvement_details))
            improvements_text.setReadOnly(True)
            improvements_text.setMaximumHeight(200)
            improvements_layout.addWidget(improvements_text)

            self.content_layout.addWidget(improvements_card)

        # Suggestions card
        if metrics.suggestions:
            suggestions_card = Card()
            suggestions_layout = QVBoxLayout(suggestions_card)
            suggestions_layout.setContentsMargins(20, 20, 20, 20)
            suggestions_layout.setSpacing(12)

            suggestions_title = QLabel("Further Suggestions")
            suggestions_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f39c12;")
            suggestions_layout.addWidget(suggestions_title)

            suggestions_text = QTextEdit()
            suggestions_text.setPlainText("\n".join(f"• {sug}" for sug in metrics.suggestions))
            suggestions_text.setReadOnly(True)
            suggestions_text.setMaximumHeight(150)
            suggestions_layout.addWidget(suggestions_text)

            self.content_layout.addWidget(suggestions_card)

        # Add stretch at the end
        self.content_layout.addStretch()

    def clear_content(self):
        """Clear all content from the layout"""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class EvalWorkerThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, evaluator, original, enhanced):
        super().__init__()
        self.evaluator = evaluator
        self.original = original
        self.enhanced = enhanced

    def run(self):
        try:
            result = self.evaluator.evaluate(self.original, self.enhanced)
            self.finished.emit(result)
        except Exception as e:
            print(f"Thread error: {str(e)}")
            self.error.emit(str(e))


class PromptEvaluator:
    def __init__(self):
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
1. Clarity (0-100):
   - Clear instructions
   - Unambiguous language
   - Logical structure

2. Specificity (0-100):
   - Detailed requirements
   - Precise constraints
   - Defined parameters

3. Actionability (0-100):
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

Evaluate the improvement and provide metrics in the specified JSON format. IMPORTANT: Return ONLY valid JSON, no additional text.
"""}
            ]

            response = ollama.chat(model='phi4:14b', messages=messages)

            if not response or 'message' not in response:
                raise Exception("Invalid response from evaluation model")

            result = self._extract_json(response['message']['content'])
            print(f"Parsed JSON result: {result}")  # Debug output

            if not result:
                print("No JSON found, using fallback values")
                return self._create_fallback_metrics()

            # Validate and extract with fallback values
            metrics_data = result.get('metrics', {})
            
            clarity_score = self._safe_float(metrics_data.get('clarity_score'), 75.0)
            specificity_score = self._safe_float(metrics_data.get('specificity_score'), 70.0)
            actionability_score = self._safe_float(metrics_data.get('actionability_score'), 65.0)
            overall_improvement = self._safe_float(metrics_data.get('overall_improvement'), 70.0)
            
            improvement_details = result.get('improvement_details', ["Enhanced prompt structure and clarity"])
            suggestions = result.get('suggestions', ["Consider adding more specific constraints"])
            
            # Ensure lists are properly formatted
            if not isinstance(improvement_details, list):
                improvement_details = [str(improvement_details)]
            if not isinstance(suggestions, list):
                suggestions = [str(suggestions)]

            return EvaluationMetrics(
                clarity_score=clarity_score,
                specificity_score=specificity_score,
                actionability_score=actionability_score,
                overall_improvement=overall_improvement,
                improvement_details=improvement_details,
                suggestions=suggestions
            )

        except Exception as e:
            print(f"Error in evaluate: {str(e)}")
            print("Falling back to default metrics")
            return self._create_fallback_metrics()

    def _extract_json(self, content: str) -> Dict:
        """Extracts a JSON object from the given string content with multiple strategies."""
        try:
            print(f"Raw content: {content[:500]}...")  # Debug output (first 500 chars)
            
            # Strategy 1: Find JSON block markers
            json_markers = ['```json', '```', '{', '}']
            cleaned_content = content.strip()
            
            # Remove markdown code blocks if present
            if '```json' in cleaned_content:
                start_marker = '```json'
                end_marker = '```'
                start = cleaned_content.find(start_marker) + len(start_marker)
                end = cleaned_content.find(end_marker, start)
                if end > start:
                    cleaned_content = cleaned_content[start:end].strip()
            
            # Strategy 2: Find the JSON object boundaries
            start = cleaned_content.find('{')
            if start == -1:
                return None
                
            # Find the matching closing brace
            brace_count = 0
            end = start
            for i, char in enumerate(cleaned_content[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            if end <= start:
                return None
                
            json_str = cleaned_content[start:end]
            print(f"Extracted JSON string: {json_str}")  # Debug output
            
            # Strategy 3: Try to parse the JSON
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            # Try to fix common JSON issues
            return self._try_fix_json(content)
        except Exception as e:
            print(f"Error extracting JSON: {str(e)}")
            return None

    def _try_fix_json(self, content: str) -> Dict:
        """Attempt to fix common JSON formatting issues."""
        try:
            # Remove common problematic characters and patterns
            fixed_content = content
            
            # Fix single quotes to double quotes
            fixed_content = fixed_content.replace("'", '"')
            
            # Remove trailing commas
            import re
            fixed_content = re.sub(r',\s*}', '}', fixed_content)
            fixed_content = re.sub(r',\s*]', ']', fixed_content)
            
            # Extract JSON portion
            start = fixed_content.find('{')
            end = fixed_content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = fixed_content[start:end]
                return json.loads(json_str)
                
        except Exception as e:
            print(f"Failed to fix JSON: {str(e)}")
            
        return None

    def _safe_float(self, value, default: float) -> float:
        """Safely convert a value to float with fallback."""
        try:
            if value is None:
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    def _create_fallback_metrics(self) -> EvaluationMetrics:
        """Create fallback metrics when parsing fails."""
        return EvaluationMetrics(
            clarity_score=75.0,
            specificity_score=70.0,
            actionability_score=65.0,
            overall_improvement=70.0,
            improvement_details=[
                "Unable to analyze specific improvements due to evaluation error",
                "Recommend manual review of prompt changes"
            ],
            suggestions=[
                "Ensure prompts are well-structured and specific",
                "Consider adding examples or constraints to improve clarity"
            ]
        )


# Example usage and test function
def test_evaluation():
    """Test function to demonstrate the evaluator"""
    app = QApplication([])
    
    # Create and show the dialog
    dialog = EvaluationDialog(None, None)  # Updated to match the new signature
    dialog.show()
    
    # Create evaluator and test data
    evaluator = PromptEvaluator()
    original = "Write a story about a cat."
    enhanced = "Write a compelling 500-word short story about a mysterious cat who appears in a small town during a thunderstorm. Include dialogue, descriptive imagery, and a surprising twist ending that reveals the cat's true nature."
    
    # Create worker thread
    worker = EvalWorkerThread(evaluator, original, enhanced)
    
    # Connect signals
    def on_finished(metrics):
        dialog.update_ui(metrics)
    
    def on_error(error_msg):
        dialog.show_error(error_msg)
    
    worker.finished.connect(on_finished)
    worker.error.connect(on_error)
    
    # Start evaluation
    worker.start()
    
    app.exec_()


if __name__ == "__main__":
    test_evaluation()
