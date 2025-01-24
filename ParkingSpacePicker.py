import cv2
import pickle

# Original dimensions of the parking spaces
width, height = 107, 48

# Scale factor (same as used in the video display resizing)
scale_percent = 50  # Adjust this to match the scale you want

# Load or initialize parking space positions
try:
    with open('CarParkPos', 'rb') as f:
        posList = pickle.load(f)
except FileNotFoundError:
    posList = []

# Function to handle the mouse click events
def mouseClick(events, x, y, flags, params):
    # Scale the mouse click coordinates
    scaled_x = int(x * (100 / scale_percent))
    scaled_y = int(y * (100 / scale_percent))

    if events == cv2.EVENT_LBUTTONDOWN:
        posList.append((scaled_x, scaled_y))
    if events == cv2.EVENT_RBUTTONDOWN:
        for i, pos in reversed(list(enumerate(posList))):
            x1, y1 = pos
            if x1 < scaled_x < x1 + width and y1 < scaled_y < y1 + height:
                posList.pop(i)

    # Save the positions after every click
    with open('CarParkPos', 'wb') as f:
        pickle.dump(posList, f)

# Video feed
cap = cv2.VideoCapture('Park.mp4')
pause = False  # Start with video not paused

cv2.namedWindow("Image")
cv2.setMouseCallback("Image", mouseClick)

while True:
    if not pause:
        success, img = cap.read()
        if not success:
            break  # Break the loop if video is finished

    # Resize the image for display
    img_resized = cv2.resize(img, (0, 0), fx=scale_percent / 100, fy=scale_percent / 100)

    for pos in posList:
        # Draw the boxes on the resized image
        box_x, box_y = int(pos[0] * scale_percent / 100), int(pos[1] * scale_percent / 100)
        cv2.rectangle(img_resized, (box_x, box_y),
                      (box_x + int(width * scale_percent / 100),
                       box_y + int(height * scale_percent / 100)),
                      (255, 0, 255), 2)

    cv2.imshow("Image", img_resized)

    key = cv2.waitKey(1)
    if key & 0xFF == ord('q'):  # Exit on 'q' key press
        break
    elif key & 0xFF == 32:  # Pause on spacebar press
        pause = not pause

# Cleanup
cap.release()
cv2.destroyAllWindows()
