import cv2
import os
import easyocr
import re
from PIL import Image
import imagehash
import tkinter as tk
from tkinter import filedialog, messagebox

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


###########  Until here are the function deal with the convert from mp4 to jpg

########### from here those who delete the duplications


def find_duplicate_images(folder_path, hash_size=8, threshold=5):
    # מילון לאחסון החתימות
    hashes = {}
    # רשימה לאחסון קבצים למחיקה
    duplicates = []

    # מעבר על כל הקבצים בתיקייה
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
            file_path = os.path.join(folder_path, filename)
            try:
                # פתיחת התמונה וחישוב החתימה
                with Image.open(file_path) as img:
                    img_hash = imagehash.phash(img, hash_size=hash_size)
                # בדיקה אם קיימת חתימה דומה
                found = False
                for existing_hash in hashes:
                    diff = img_hash - existing_hash
                    if diff <= threshold:
                        # נמצא כפילות
                        print(f"photo '{filename}' similar to  '{hashes[existing_hash]}', differance: {diff}")
                        duplicates.append(file_path)
                        found = True
                        break
                if not found:
                    # הוספת החתימה למילון
                    hashes[img_hash] = filename
            except Exception as e:
                print(f"error prosses the photo '{filename}': {e}")
    return duplicates

def delete_files(file_list):
    for file_path in file_list:
        try:
            os.remove(file_path)
            print(f"נמחק הקובץ: {file_path}")
        except Exception as e:
            print(f"error delete the file '{file_path}': {e}")


###########  Until here are the function deal with 'delete the duplications'

########### from here those who extracrt

def extract_text_from_image(image_path):
    reader = easyocr.Reader(['en'])  # הגדרת השפה אנגלית
    result = reader.readtext(image_path, detail=0)
    text = ' '.join(result)
    return text

def find_phone_numbers(text):
    # ביטוי רגולרי מותאם למספרים בפורמט +972 XX-XXX-XXXX
    pattern = r'(?:\+972[\s\-]?)(\d{2})[\s\-]?(\d{3})[\s\-]?(\d{4})'
    matches = re.findall(pattern, text)
    # הרכבת המספרים בצורה אחידה
    numbers = ['0{}{}{}'.format(match[0], match[1], match[2]) for match in matches]
    return numbers


def extract_phone_numbers_from_images(folder_path):
    all_numbers = set()
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff')):
            image_path = os.path.join(folder_path, filename)
            text = extract_text_from_image(image_path)
            numbers = find_phone_numbers(text)
            all_numbers.update(numbers)
    return all_numbers

def select_video_file():
    video_path = filedialog.askopenfilename(title="Pick a video", filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*")))
    if video_path:
        output_folder = 'frames'
        video_to_frames(video_path, output_folder)

        folder_path = output_folder
        duplicates = find_duplicate_images(folder_path)
        """if duplicates:
            response = messagebox.askyesno("confirm delete", "There are some similar photos. Do you want to delete?")
            if response:
                delete_files(duplicates)
                messagebox.showinfo("Result", "Photos has seccsefuly removed.")
            else:
                messagebox.showinfo("Result", "Delete canceled.")"""
        print("starting the delet operation")
        delete_files(duplicates)
        print("starting the extarct faze")
        numbers = extract_phone_numbers_from_images(folder_path)
        if numbers:
            numbers_file_path = os.path.join(folder_path, 'extracted_phone_numbers.txt')
            save_numbers_to_file(numbers, numbers_file_path)
            messagebox.showinfo("Result", f"Numbers have been saved to \n{numbers_file_path}")
        else:
            messagebox.showinfo("Result", "No phone numbers has been found.")


def save_numbers_to_file(numbers, file_path):
    with open(file_path, 'w') as f:
        for number in numbers:
            f.write(f"{number}\n")
    print(f"מספרי הטלפון נשמרו בהצלחה בקובץ {file_path}")
    
if __name__ == "__main__":
    # יצירת ממשק המשתמש
    root = tk.Tk()
    root.title("Video to Frames and Phone Number Extractor")

    frame = tk.Frame(root)
    frame.pack(pady=20, padx=20)

    select_button = tk.Button(frame, text="בחר סרטון", command=select_video_file)
    select_button.pack(pady=10)

    exit_button = tk.Button(frame, text="יציאה", command=root.quit)
    exit_button.pack(pady=10)

    root.mainloop()
"""
if __name__ == "__main__":
    video_path = 'C:/Users/hrtom/Desktop/1.1.mp4'  # החלף לנתיב הסרטון שלך
    output_folder = 'frames'  # שם התיקייה לשמירת התמונות
    video_to_frames(video_path, output_folder)
    
    folder_path = r"C:/Users/hrtom/Desktop/phone-from-video/frames"  # עדכן את הנתיב לתיקייה עם התמונות
    duplicates = find_duplicate_images(folder_path)
    if duplicates:
        print("\nהתמונות הדומות הבאות יימחקו:")
        for file_path in duplicates:
            print(file_path)
        confirm = input("\nהאם אתה בטוח שברצונך למחוק את הקבצים הללו? (y/n): ")
        if confirm.lower() == 'y':
            delete_files(duplicates)
            print("הקבצים נמחקו בהצלחה.")
        else:
            print("המחיקה בוטלה.")
    else:
        print("לא נמצאו תמונות דומות.")
        
    #folder_path = "C:/Users/hrtom/Desktop/excstarct numbers from photo/frames"  # עדכן לנתיב התיקייה עם התמונות
    numbers = extract_phone_numbers_from_images(folder_path)
    print("Phone numbers that have been extract:")
    for number in numbers:
        print(number)"""

