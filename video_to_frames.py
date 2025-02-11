import cv2
import os

def video_to_frames(video_path, output_folder):
    # יצירת התיקייה אם היא לא קיימת
    os.makedirs(output_folder, exist_ok=True)
    
    # פתיחת הסרטון
    vidcap = cv2.VideoCapture(video_path)
    success, image = vidcap.read()
    count = 0

    while success:
        # שמירת הפריים כתמונה
        cv2.imwrite(f"{output_folder}/frame_{count:05d}.png", image)
        success, image = vidcap.read()
        count += 1
    
    vidcap.release()
    print(f"{count} has been converted to frames and saved in '{output_folder}'.")

if __name__ == "__main__":
    video_path = '"C:/Users/hrtom/Desktop/1.1.mp4"'  # החלף לנתיב הסרטון שלך
    output_folder = 'frames'  # שם התיקייה לשמירת התמונות
    video_to_frames(video_path, output_folder)
