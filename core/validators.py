import os
from django.core.exceptions import ValidationError
# import cv2


def post_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.jpg', '.png', '.jpeg', '.mp4', '.mkv', '.avi', '.mp3']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')
    

def validate_image_with_face(file):
    # """
    # Custom validator to check if the uploaded file is a valid image and contains a face using OpenCV.
    # """
    # try:
    #     # Open the file using OpenCV
    #     image = cv2.imread(file.path)

    #     # Convert the image to grayscale
    #     gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
    #     # Load the pre-trained Haar Cascade classifier for face detection
    #     face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    #     # Detect faces in the image
    #     faces = face_cascade.detectMultiScale(gray_image, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    #     # Check if at least one face is detected
    #     if len(faces) == 0:
    #         raise ValidationError("No face detected in the image. Please upload an image with a face.")
    # except Exception as e:
    #     raise ValidationError(f"Error validating image with face recognition: {e}")

    pass