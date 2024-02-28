from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog, QSpacerItem, QSizePolicy
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont, QIcon
import os
import sys

# Append the .src directory to the system path
sys.path.append('src')

# Import your modules from the .src directory
import src.ImageVideo2desc as ImageVideo2desc
import src.Diagnosis_TXT as Diagnosis_TXT
import src.Diagnosis_Video_Dialogue as Diagnosis_Video_Dialogue
import src.Diagnosis_SRT_Scenes as Diagnosis_SRT_Scenes


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Main Window Setup
        self.setWindowTitle("Personality Analysis Tool")
        self.setGeometry(100, 100, 300, 180)  # Adjust size as needed
        self.setFixedSize(300, 180)  # Lock the window size

        # Set the window icon to Psi2.png from the assets folder
        self.setWindowIcon(QIcon("assets/Psi2.png"))

        # Layout Setup
        layout = QVBoxLayout()
        layout.setSpacing(0)  # Remove space between buttons
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins to center buttons in the window

        # Add a spacer at the top for some space
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Buttons
        self.btn_dialogue_file = QPushButton(QIcon("assets/srt.png"), " Dialogue File (SRT/Captions)")
        self.btn_dialogue_file.clicked.connect(self.process_dialogue_file)
        self.btn_dialogue_file.setFont(QFont('Arial', 10, QFont.Weight.Bold))  # Set font to bold
        self.btn_dialogue_file.setFixedSize(QSize(300, 70))  # Make the button taller but same width

        self.btn_media_folder = QPushButton(QIcon("assets/folder.png"), " Media Folder (Visual)")
        self.btn_media_folder.clicked.connect(self.process_media_folder)
        self.btn_media_folder.setFixedSize(QSize(300, 50))

        self.btn_video_file = QPushButton(QIcon("assets/video.png"), " Video File (Speech)")
        self.btn_video_file.clicked.connect(self.process_video_file)
        self.btn_video_file.setFixedSize(QSize(300, 50))

        # Add buttons to layout with alignment
        layout.addWidget(self.btn_dialogue_file, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.btn_media_folder, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.btn_video_file, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add a spacer at the bottom for some space at the end
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Central Widget
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def process_media_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Media Folder")
        if folder_path:
            print(f"Selected Folder: {folder_path}")
            # Receive the output file path from ImageVideo2desc
            description_txt_file = ImageVideo2desc.main(folder_path)
            print(f"File to analyze: {description_txt_file}")
            # Check if the file exists before attempting analysis
            if os.path.exists(description_txt_file):
                Diagnosis_TXT.analyze_text_file(description_txt_file)
            else:
                print(f"File not found: {description_txt_file}")

    def process_video_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", filter="MP4 Files (*.mp4)")
        if file_path:
            analysis_save_path = Diagnosis_Video_Dialogue.analyze_video_dialogue(file_path)
            print(f"Video analysis saved to: {analysis_save_path}")

    def process_dialogue_file(self):
        # Function to handle the SRT/Captions file processing
        srt_file_path, _ = QFileDialog.getOpenFileName(self, "Select Dialogue File", filter="SRT Files (*.srt)")
        if srt_file_path:
            print(f"Selected File: {srt_file_path}")

            # Specify the output directory where the results will be saved
            output_directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")

            if output_directory:
                print(f"Output will be saved to: {output_directory}")
                try:
                    # Process the SRT file using the Diagnosis_SRT_Scenes module
                    # Replace 'Diagnosis_SRT_Scenes' with the actual name of your module
                    Diagnosis_SRT_Scenes.process_srt_file(srt_file_path, output_directory)
                    print("Dialogue file processed successfully.")
                except Exception as e:
                    print(f"An error occurred while processing the dialogue file: {e}")
            else:
                print("No output directory selected. Processing canceled.")
        else:
            print("No SRT file selected. Processing canceled.")


if __name__ == "__main__":
    app = QApplication([])
    window = MainApp()
    window.show()
    app.exec()
