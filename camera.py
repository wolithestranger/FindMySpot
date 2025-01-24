import sys
import cv2
import numpy as np
import pickle
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QPushButton, QStackedWidget, QLabel

# Initialize the parking space positions
try:
    with open('CarParkPos', 'rb') as f:
        posList = pickle.load(f)
except FileNotFoundError:
    posList = []

# Configuration variables
original_width, original_height = 107, 48
scale_percent = 50  # percentage of original size
reserved_spaces = set()  # Set to hold reserved spaces

# Create a Qt application
app = QtWidgets.QApplication(sys.argv)

# Main window class
class MainWindow(QtWidgets.QWidget):
    def __init__(self, stacked_widget, db, main_app):
        super().__init__()

        self.db = db
        self.main_app = main_app
        self.stacked_widget = stacked_widget
        
        # Video feed
        self.cap = cv2.VideoCapture('Park.mp4')
        # Playback flag
        self.is_paused = False

        self.frame_counter = 0
        self.process_every_n_frames = 4  # Adjust as needed

        self.current_user = None
        # UI setup
        # Modify these lines in the __init__ method of the MainWindow class

        self.reserved_spots = []

        self.setGeometry(100, 100, 2000, 1200)
        self.setWindowTitle('FindMySpot')

        # Main horizontal layout
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.setLayout(self.main_layout)

        # Image label for displaying the video
        self.image_label = QtWidgets.QLabel(self)
        self.image_label.resize(1280, 960)

        # Overlay widget for the 'Back' button
        self.overlay_widget = QtWidgets.QWidget(self.image_label)
        self.overlay_widget.setGeometry(0, 0, 200, 100)  # Adjust size and position as needed

        # Layout for the overlay widget
        overlay_layout = QtWidgets.QVBoxLayout(self.overlay_widget)

        # Back button on top of the video
        self.back_to_dashboard_button = QtWidgets.QPushButton('Back', self.overlay_widget)
        self.back_to_dashboard_button.clicked.connect(self.gotoDashboard)
        overlay_layout.addWidget(self.back_to_dashboard_button, 0, Qt.AlignTop | Qt.AlignLeft)

        # Set the video label and overlay widget to the main layout
        self.main_layout.addWidget(self.image_label)
        
        # Right layout for controls
        self.right_layout = QtWidgets.QVBoxLayout()

        # Reservation Input
        self.space_input = QtWidgets.QLineEdit(self)
        self.space_input.setPlaceholderText("Enter space number to reserve")
        self.right_layout.addWidget(self.space_input)

        # Reservation Button
        self.reserve_button = QtWidgets.QPushButton("Reserve Space", self)
        self.reserve_button.clicked.connect(self.reserve_space)
        self.right_layout.addWidget(self.reserve_button)

        # Unreserve Button
        self.unreserve_button = QtWidgets.QPushButton("Unreserve", self)
        self.unreserve_button.clicked.connect(self.unreserve_space)
        self.right_layout.addWidget(self.unreserve_button)

        # Information panel
        self.info_panel = QtWidgets.QTextBrowser(self)
        self.right_layout.addWidget(self.info_panel)

        # Notification panel
        self.notification_panel = QtWidgets.QTextBrowser(self)
        self.notification_panel.setFixedHeight(100)  # Adjust the height as needed

        # Set specific style for notification panel
        notification_panel_style = "font-size: 10pt;"  # Smaller font size
        self.notification_panel.setStyleSheet(notification_panel_style)

        self.right_layout.addWidget(self.notification_panel)


        # Add right layout to main layout
        self.main_layout.addLayout(self.right_layout)

        # Timer for video updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(60)  # Update every ~30 ms

        # Pause Button
        self.pause_button = QtWidgets.QPushButton("Pause", self)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.right_layout.addWidget(self.pause_button)

        # Update info panel
        self.update_info_panel()
        
    def gotoDashboard(self):
        # Switch to the Dashboard Screen
        dashboard_index = self.main_app.widget_indices.get('dashboard_screen')
        if dashboard_index is not None:
            self.main_app.stacked_widget.setCurrentIndex(dashboard_index)
        else:
            print("Dashboard Screen not found in QStackedWidget")

    def go_back(self):
        # Hide the current window
        self.hide()
        # Show the dashboard window
        dashboard_index = self.main_app.widget_indices.get('dashboard_screen')
        dashboard_screen = self.stacked_widget.widget(dashboard_index)
        if hasattr(dashboard_screen, 'update_dashboard'):
            dashboard_screen.update_dashboard()
        self.dashboard_window.show()

    def on_user_login(self):
        # Call this method when the user logs in
        self.reserved_spots = self.db.get_all_reserved_spots()
        self.update_frame()  # Update the frame to reflect the new reserved spots

    def display_notification(self, message):
        self.notification_panel.setText(message)

    def set_current_user(self, username):
        self.current_user = username

    # Additional method to toggle pause
    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.pause_button.setText("Resume" if self.is_paused else "Pause")


    def update_frame(self):
        if not self.is_paused:
            ret, frame = self.cap.read()
            if ret:
                self.frame_counter += 1
                if self.frame_counter % self.process_every_n_frames == 0:
                    frame = self.process_frame(frame)
                    frame_qt = self.convert_cv_qt(frame)
                    self.image_label.setPixmap(frame_qt)

    def process_frame(self, frame):
        # Apply image processing to the original frame
        imgGray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        imgBlur = cv2.GaussianBlur(imgGray, (3, 3), 1)
        imgThreshold = cv2.adaptiveThreshold(imgBlur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                            cv2.THRESH_BINARY_INV, 25, 16)
        imgMedian = cv2.medianBlur(imgThreshold, 5)
        kernel = np.ones((3, 3), np.uint8)
        imgDilate = cv2.dilate(imgMedian, kernel, iterations=1)

        # Resize the original frame for display
        scale_factor = scale_percent / 100 * 2  # Double the size
        width_resized = int(frame.shape[1] * scale_factor)
        height_resized = int(frame.shape[0] * scale_factor)
        frame_resized = cv2.resize(frame, (width_resized, height_resized), interpolation=cv2.INTER_AREA)

        free_spaces = len(posList)  # Start with all spaces free
        # Process each parking spot
        for index, pos in enumerate(posList):
            # Scale the coordinates for the resized frame
            x_scaled, y_scaled = int(pos[0] * scale_factor), int(pos[1] * scale_factor)
            width_scaled, height_scaled = int(original_width * scale_factor), int(original_height * scale_factor)
            self.reserved_spots = self.db.get_all_reserved_spots()
            # Crop from the processed single-channel image (imgDilate)
            imgCrop = imgDilate[pos[1]:pos[1] + original_height, pos[0]:pos[0] + original_width]
            count = cv2.countNonZero(imgCrop)
            # Adjust this threshold based on your specific needs
            if index in [30, 32, 42, 43]:
                threshold = 1500
            else:
                threshold = 1200
            
            if count < threshold:
                if index in self.reserved_spots:
                    color = (0, 255, 255)  # Yellow for reserved spaces
                else:
                    color = (57, 255, 20)  # Green for free spaces
            else:
                color = (0, 0, 255)  # Red for occupied spaces
                free_spaces -= 1

            cv2.rectangle(frame_resized, (x_scaled, y_scaled), (x_scaled + width_scaled, y_scaled + height_scaled), color, 2)

            # Display spot number within the rectangle
            spot_text = f"{index}"
            cv2.putText(frame_resized, spot_text, (x_scaled + 5, y_scaled + height_scaled - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Update free spaces count
        self.info_panel.setText(f"Free spaces: {free_spaces}")
        return frame_resized
    

    def convert_cv_qt(self, frame):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(convert_to_qt_format)

    def update_info_panel(self):
        self.info_panel.setText("Information Panel\n")

    def reserve_space(self):
        try:
            space_number = int(self.space_input.text())
            if 0 <= space_number < len(posList):
                username = self.current_user
                dashboard_index = self.main_app.widget_indices.get('dashboard_screen')
                dashboard_screen = self.stacked_widget.widget(dashboard_index)

                # Check if the user has sufficient balance
                if self.db.get_user_balance(username) >= 5:
                    success = self.db.reserve_parking_spot(username, space_number)
                    if success:
                        reserved_spaces.add(posList[space_number])
                        self.display_notification("Space reserved successfully.")

                        # Deduct $5 from the user's balance
                        self.db.update_account_balance(username, -5)

                        if hasattr(dashboard_screen, 'update_dashboard'):
                            dashboard_screen.update_dashboard()

                        self.space_input.clear()
                    else:
                        self.display_notification("Space already reserved!")
                else:
                    # Notify the user if they don't have sufficient balance
                    self.display_notification("Insufficient balance to reserve a space. Please top up your account.")
        except ValueError:
            self.display_notification("Invalid input for space number.")


    def unreserve_space(self):
        try:
            space_number = int(self.space_input.text())
            if 0 <= space_number < len(posList):
                reserved_space = posList[space_number]
                dashboard_screen = self.stacked_widget.widget(1)
                
                # Check if the user has reserved the space
                
                success = self.db.unreserve_parking_spot(self.current_user, space_number)
                if success:
                    # Only attempt to remove if the space is in the set
                    if reserved_space in reserved_spaces:
                        reserved_spaces.remove(reserved_space)

                    self.update_info_panel()
                    self.space_input.clear()

                    # Refund $5 to the user's balance
                    self.db.update_account_balance(self.current_user, 5)
                    dashboard_screen.update_dashboard()

                    self.display_notification("Space unreserved successfully.")
                
                else:
                    self.display_notification("You have not reserved this space.")
        except ValueError:
            pass

    def keyPressEvent(self, event):
        if event.key() == QtGui.QKeySequence('Space'):
            self.is_paused = not self.is_paused
        self.update_info_panel()

    def closeEvent(self, event):
        self.cap.release()

if __name__ == '__main__':
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())
