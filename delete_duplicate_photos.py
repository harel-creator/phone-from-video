import os
from PIL import Image
import imagehash

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
                        print(f"תמונה '{filename}' דומה ל '{hashes[existing_hash]}', הבדל: {diff}")
                        duplicates.append(file_path)
                        found = True
                        break
                if not found:
                    # הוספת החתימה למילון
                    hashes[img_hash] = filename
            except Exception as e:
                print(f"שגיאה בעיבוד התמונה '{filename}': {e}")
    return duplicates

def delete_files(file_list):
    for file_path in file_list:
        try:
            os.remove(file_path)
            print(f"נמחק הקובץ: {file_path}")
        except Exception as e:
            print(f"שגיאה במחיקת הקובץ '{file_path}': {e}")

if __name__ == "__main__":
    folder_path = r"C:/Users/hrtom/Desktop/excstarct numbers from photo/frames"  # עדכן את הנתיב לתיקייה עם התמונות
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
