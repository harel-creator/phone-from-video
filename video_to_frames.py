import cv2
import os
import easyocr
import re
from PIL import Image
import imagehash
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# 1) Convert video to frames
def video_to_frames(video_path, output_folder, progress_callback=None):
    """
    Converts the given video to individual frames and saves them in output_folder.
    Calls progress_callback(current, total) if provided to update a progress bar.
    """
    os.makedirs(output_folder, exist_ok=True)
    vidcap = cv2.VideoCapture(video_path)
    total_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    success, image = vidcap.read()
    count = 0

    while success:
        cv2.imwrite(f"{output_folder}/frame_{count:05d}.png", image)
        success, image = vidcap.read()
        count += 1
        if progress_callback:
            progress_callback(count, total_frames)
    
    vidcap.release()
    print(f"{count} frames have been converted and saved in '{output_folder}'.")


# 2) Find duplicate images
def find_duplicate_images(folder_path, hash_size=8, threshold=5, progress_callback=None):
    """
    Scans the given folder for duplicate (or near-duplicate) images using pHash.
    Calls progress_callback(current, total) if provided.
    Returns a list of duplicate file paths to delete.
    """
    hashes = {}
    duplicates = []
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp'))]
    total_files = len(files)

    for i, filename in enumerate(files):
        file_path = os.path.join(folder_path, filename)
        try:
            with Image.open(file_path) as img:
                img_hash = imagehash.phash(img, hash_size=hash_size)
            found = False
            for existing_hash in hashes:
                diff = img_hash - existing_hash
                if diff <= threshold:
                    print(f"Image '{filename}' is similar to '{hashes[existing_hash]}'. Difference: {diff}")
                    duplicates.append(file_path)
                    found = True
                    break
            if not found:
                hashes[img_hash] = filename
        except Exception as e:
            print(f"Error processing image '{filename}': {e}")

        if progress_callback:
            progress_callback(i + 1, total_files)
    
    return duplicates


# 3) Delete duplicate files
def delete_files(file_list, progress_callback=None):
    """
    Deletes the files in file_list.
    Calls progress_callback(current, total) if provided to update a progress bar.
    """
    total_files = len(file_list)
    for i, file_path in enumerate(file_list):
        try:
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
        except Exception as e:
            print(f"Error deleting the file '{file_path}': {e}")
        if progress_callback:
            progress_callback(i + 1, total_files)


# 4) Extract phone numbers from frames
def extract_text_from_image(image_path):
    """
    Uses EasyOCR to extract text from a single image.
    """
    reader = easyocr.Reader(['en'])
    result = reader.readtext(image_path, detail=0)
    text = ' '.join(result)
    return text

def find_phone_numbers(text):
    """
    Uses a regex pattern to find phone numbers in the extracted text.
    Here, the pattern is for Israeli phone numbers starting with +972.
    """
    pattern = r'(?:\+972[\s\-]?)(\d{2})[\s\-]?(\d{3})[\s\-]?(\d{4})'
    matches = re.findall(pattern, text)
    # Convert +972XX-XXX-XXXX to 0XX-XXX-XXXX
    numbers = ['0{}{}{}'.format(match[0], match[1], match[2]) for match in matches]
    return numbers

def extract_phone_numbers_from_frames(frames_dir, progress_callback=None):
    """
    Goes through all frames in frames_dir, extracts text, and looks for phone numbers.
    Calls progress_callback(current, total) if provided to update a progress bar.
    Returns a set of all found phone numbers.
    """
    all_numbers = set()
    files = [f for f in os.listdir(frames_dir) if f.endswith('.png')]
    total_files = len(files)

    for i, filename in enumerate(files):
        image_path = os.path.join(frames_dir, filename)
        text = extract_text_from_image(image_path)
        numbers = find_phone_numbers(text)
        if numbers:
            print(f"Phone numbers found in image {filename}:")
            for number in numbers:
                print(number)
            all_numbers.update(numbers)
        else:
            print(f"No phone numbers found in image {filename}")
        print('-' * 40)  # Separator for clarity

        if progress_callback:
            progress_callback(i + 1, total_files)
    
    return all_numbers


def save_numbers_to_file(numbers, file_path):
    """
    Saves all extracted phone numbers to a file.
    """
    with open(file_path, 'w') as f:
        for number in numbers:
            f.write(f"{number}\n")
    print(f"Phone numbers successfully saved to {file_path}")


# --- TKINTER APP ---

def select_video_file():
    """
    Opens a file dialog to pick a video, then processes it step by step:
      1) Convert video to frames
      2) Scan for duplicate frames
      3) Delete duplicates
      4) Extract phone numbers
    Uses separate progress bars for each step.
    """
    video_path = filedialog.askopenfilename(
        title="Select a Video",
        filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*"))
    )
    if not video_path:
        return  # User canceled

    output_folder = 'frames'
    folder_path = output_folder

    # 1) Convert video to frames
    convert_progress_var.set(0)
    video_to_frames(video_path, output_folder, progress_callback=update_convert_progress)

    # 2) Find duplicate images
    scan_progress_var.set(0)
    duplicates = find_duplicate_images(folder_path, progress_callback=update_scan_progress)

    # 3) Delete duplicates
    delete_progress_var.set(0)
    delete_files(duplicates, progress_callback=update_delete_progress)
    
    # 4) Extract phone numbers
    extract_progress_var.set(0)
    numbers = extract_phone_numbers_from_frames(folder_path, progress_callback=update_extract_progress)

    if numbers:
        numbers_file_path = os.path.join(folder_path, 'extracted_phone_numbers.txt')
        save_numbers_to_file(numbers, numbers_file_path)
        messagebox.showinfo("Result", f"Numbers have been saved to \n{numbers_file_path}")
    else:
        messagebox.showinfo("Result", "No phone numbers have been found.")


# --- PROGRESS UPDATE FUNCTIONS ---
def update_convert_progress(current, total):
    convert_progress_var.set(int((current / total) * 100))
    convert_progress_bar.update()

def update_scan_progress(current, total):
    scan_progress_var.set(int((current / total) * 100))
    scan_progress_bar.update()

def update_delete_progress(current, total):
    delete_progress_var.set(int((current / total) * 100))
    delete_progress_bar.update()

def update_extract_progress(current, total):
    extract_progress_var.set(int((current / total) * 100))
    extract_progress_bar.update()


# --- MAIN APP ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Video to Frames & Phone Number Extractor")

    # Make the window a bit larger and set a light background for a more welcoming look
    root.geometry("700x500")
    root.configure(bg="#e6f7ff")

    main_frame = tk.Frame(root, bg="#e6f7ff")
    main_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

    # Button to select video
    select_button = tk.Button(main_frame, text="Select Video", command=select_video_file)
    select_button.pack(pady=10)

    # Button to exit
    exit_button = tk.Button(main_frame, text="Exit", command=root.quit)
    exit_button.pack(pady=10)

    # Frame for progress bars
    progress_frame = tk.Frame(main_frame, bg="#e6f7ff")
    progress_frame.pack(pady=10)

    # --- 1) Convert Progress ---
    convert_label = tk.Label(progress_frame, text="Conversion Progress:", bg="#e6f7ff")
    convert_label.pack()
    convert_progress_var = tk.IntVar()
    convert_progress_bar = ttk.Progressbar(progress_frame, variable=convert_progress_var, maximum=100)
    convert_progress_bar.pack(pady=5)

    # --- 2) Scan Progress ---
    scan_label = tk.Label(progress_frame, text="Duplicate Scan Progress:", bg="#e6f7ff")
    scan_label.pack()
    scan_progress_var = tk.IntVar()
    scan_progress_bar = ttk.Progressbar(progress_frame, variable=scan_progress_var, maximum=100)
    scan_progress_bar.pack(pady=5)

    # --- 3) Delete Progress ---
    delete_label = tk.Label(progress_frame, text="Deleting Duplicates Progress:", bg="#e6f7ff")
    delete_label.pack()
    delete_progress_var = tk.IntVar()
    delete_progress_bar = ttk.Progressbar(progress_frame, variable=delete_progress_var, maximum=100)
    delete_progress_bar.pack(pady=5)

    # --- 4) Extract Progress ---
    extract_label = tk.Label(progress_frame, text="Extraction Progress:", bg="#e6f7ff")
    extract_label.pack()
    extract_progress_var = tk.IntVar()
    extract_progress_bar = ttk.Progressbar(progress_frame, variable=extract_progress_var, maximum=100)
    extract_progress_bar.pack(pady=5)

    root.mainloop()
