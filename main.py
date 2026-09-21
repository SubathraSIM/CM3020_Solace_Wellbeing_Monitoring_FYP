# Import required libraries
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from UI.database.database import create_database
from UI.ui.main_window import MainWindow
from UI.ui.translations import prepare_translations

# folder containing file
PROJECT_ROOT = Path(__file__).resolve().parent
# path to the stylesheet
STYLE_PATH = PROJECT_ROOT / "UI" / "ui" / "styles.css"

# app stylesheet
def load_stylesheet():
    # stylesheet as UTF-8 text
    return STYLE_PATH.read_text(encoding="utf-8")


# Set up and start the app
def main():
    # Set up the database
    create_database()
    # Prepare app translations
    prepare_translations()
    # Create app using the startup arguments
    app = QApplication(sys.argv)
    # Apply stylesheet
    app.setStyleSheet(load_stylesheet())
    # main window
    window = MainWindow()
    # Show main window
    window.show()
    # app running and handle user actions
    return app.exec()


# Start the app
if __name__ == "__main__":
    sys.exit(main())