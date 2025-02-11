import easyocr
import os
import re

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

if __name__ == "__main__":
    folder_path = "C:/Users/hrtom/Desktop/excstarct numbers from photo/frames"  # עדכן לנתיב התיקייה עם התמונות
    numbers = extract_phone_numbers_from_images(folder_path)
    print("Phone numbers that have been extract:")
    for number in numbers:
        print(number)
