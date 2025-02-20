import cv2
import os
import easyocr
import re
from PIL import Image
import imagehash
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import time
import shutil
import concurrent.futures
import threading

# Thread-local variable for the EasyOCR reader.
# Each thread will create its own instance if not already created.
thread_local = threading.local()

def get_reader():
    if not hasattr(thread_local, "reader"):
        thread_local.reader = easyocr.Reader(['en'])
    return thread_local.reader

# -------------------- Step 1: Convert Video to Frames --------------------
def video_to_frames(video_path, output_folder, progress_callback=None):
    """
    Converts a video into frames and saves them in output_folder.
    Calls progress_callback(current, total) if provided.
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

# -------------------- Step 2: Find Duplicate Images --------------------
def find_duplicate_images(folder_path, hash_size=8, threshold=5, progress_callback=None):
    """
    Scans the folder for duplicate (or near-duplicate) images using pHash.
    Calls progress_callback(current, total) if provided.
    Returns a list of duplicate file paths.
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

# -------------------- Step 3: Delete Duplicate Files --------------------
def delete_files(file_list, progress_callback=None):
    """
    Deletes the files in file_list.
    Calls progress_callback(current, total) if provided.
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

# -------------------- Step 4: Extract Phone Numbers from Frames (Multithreaded) --------------------
def extract_text_from_image(image_path):
    """
    Uses EasyOCR (with a thread-local reader) to extract text from an image.
    """
    reader = get_reader()
    result = reader.readtext(image_path, detail=0)
    text = ' '.join(result)
    return text

def find_phone_numbers(text):
    """
    Uses a regex pattern to find Israeli phone numbers in the text.
    Converts numbers starting with +972 into a 0XX... format.
    """
    pattern = r'(?:\+972[\s\-]?)(\d{2})[\s\-]?(\d{3})[\s\-]?(\d{4})'
    matches = re.findall(pattern, text)
    numbers = ['0{}{}{}'.format(match[0], match[1], match[2]) for match in matches]
    return numbers

def process_frame(image_path):
    """
    Processes a single frame: extracts text and then finds phone numbers.
    Returns a tuple (filename, list of numbers).
    """
    text = extract_text_from_image(image_path)
    numbers = find_phone_numbers(text)
    return (os.path.basename(image_path), numbers)

def extract_phone_numbers_from_frames_multithreaded(frames_dir, progress_callback=None):
    """
    Processes all frames in frames_dir concurrently using a thread pool with 4 workers.
    Calls progress_callback(current, total) each time a frame is processed.
    Returns a set of all found phone numbers.
    """
    all_numbers = set()
    files = [f for f in os.listdir(frames_dir) if f.endswith('.png')]
    total_files = len(files)
    processed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_frame, os.path.join(frames_dir, filename)): filename for filename in files}
        for future in concurrent.futures.as_completed(futures):
            filename, numbers = future.result()
            if numbers:
                print(f"Phone numbers found in image {filename}:")
                for number in numbers:
                    print(number)
                all_numbers.update(numbers)
            else:
                print(f"No phone numbers found in image {filename}")
            print('-' * 40)
            processed += 1
            if progress_callback:
                progress_callback(processed, total_files)
    return all_numbers

def save_numbers_to_file(numbers, file_path):
    """
    Saves all extracted phone numbers to a file.
    """
    with open(file_path, 'w') as f:
        for number in numbers:
            f.write(f"{number}\n")
    print(f"Phone numbers successfully saved to {file_path}")

# -------------------- TKINTER UI --------------------
def update_progress(progress_var, percentage_label, progress_bar, current, total):
    """Helper function to update a progress bar and its percentage label."""
    percentage = int((current / total) * 100)
    progress_var.set(percentage)
    progress_bar.update()
    if percentage < 100:
        percentage_label.config(text=f"{percentage}%")
    else:
        percentage_label.config(text="Done")

def update_convert_progress(current, total):
    update_progress(convert_progress_var, convert_percentage_label, convert_progress_bar, current, total)

def update_scan_progress(current, total):
    update_progress(scan_progress_var, scan_percentage_label, scan_progress_bar, current, total)

def update_delete_progress(current, total):
    update_progress(delete_progress_var, delete_percentage_label, delete_progress_bar, current, total)

def update_extract_progress(current, total):
    update_progress(extract_progress_var, extract_percentage_label, extract_progress_bar, current, total)

def select_video_file():
    """
    Opens a file dialog to select a video and then processes it step by step:
      1. Converts video to frames.
      2. Scans for duplicate frames.
      3. Deletes duplicate frames.
      4. Extracts phone numbers concurrently using 4 threads.
    Updates separate progress bars with percentages and elapsed time.
    After extraction, prompts whether to delete the frames.
    """
    video_path = filedialog.askopenfilename(
        title="Select a Video",
        filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*"))
    )
    if not video_path:
        return

    output_folder = 'frames'
    folder_path = output_folder
    start_total = time.time()

    # -------------------- 1. Convert Video to Frames --------------------
    convert_progress_var.set(0)
    convert_percentage_label.config(text="0%")
    start_convert = time.time()
    video_to_frames(video_path, output_folder, progress_callback=update_convert_progress)
    end_convert = time.time()
    convert_elapsed = end_convert - start_convert
    convert_time_label.config(text=f"Time taken: {convert_elapsed:.2f} sec")

    # -------------------- 2. Duplicate Scan --------------------
    scan_progress_var.set(0)
    scan_percentage_label.config(text="0%")
    start_scan = time.time()
    duplicates = find_duplicate_images(folder_path, progress_callback=update_scan_progress)
    end_scan = time.time()
    scan_elapsed = end_scan - start_scan
    scan_time_label.config(text=f"Time taken: {scan_elapsed:.2f} sec")

    # -------------------- 3. Delete Duplicates --------------------
    delete_progress_var.set(0)
    delete_percentage_label.config(text="0%")
    start_delete = time.time()
    delete_files(duplicates, progress_callback=update_delete_progress)
    end_delete = time.time()
    delete_elapsed = end_delete - start_delete
    delete_time_label.config(text=f"Time taken: {delete_elapsed:.2f} sec")

    # -------------------- 4. Extract Phone Numbers (Multithreaded with 4 Threads) --------------------
    extract_progress_var.set(0)
    extract_percentage_label.config(text="0%")
    start_extract = time.time()
    numbers = extract_phone_numbers_from_frames_multithreaded(folder_path, progress_callback=update_extract_progress)
    end_extract = time.time()
    extract_elapsed = end_extract - start_extract
    extract_time_label.config(text=f"Time taken: {extract_elapsed:.2f} sec")

    total_elapsed = time.time() - start_total
    total_time_label.config(text=f"Total time: {total_elapsed:.2f} sec")

    if numbers:
        numbers_file_path = os.path.join(os.getcwd(), 'extracted_phone_numbers.txt')
        save_numbers_to_file(numbers, numbers_file_path)
        messagebox.showinfo("Result", f"Numbers have been saved to:\n{numbers_file_path}")
    else:
        messagebox.showinfo("Result", "No phone numbers have been found.")

    # Prompt to delete frames after extraction
    if messagebox.askyesno("Delete Frames", "Do you want to delete the frames?"):
        try:
            shutil.rmtree(folder_path)
            messagebox.showinfo("Frames Deleted", "Frames have been successfully deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Error deleting frames: {e}")

# -------------------- Main Application UI --------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Video to Frames & Phone Number Extractor")
    root.geometry("800x600")
    root.configure(bg="#e6f7ff")

    main_frame = tk.Frame(root, bg="#e6f7ff")
    main_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

    select_button = tk.Button(main_frame, text="Select Video", command=select_video_file)
    select_button.pack(pady=10)
    exit_button = tk.Button(main_frame, text="Exit", command=root.quit)
    exit_button.pack(pady=10)

    progress_frame = tk.Frame(main_frame, bg="#e6f7ff")
    progress_frame.pack(pady=10, fill=tk.X)

    # --- Conversion Progress ---
    convert_frame = tk.Frame(progress_frame, bg="#e6f7ff")
    convert_frame.pack(fill=tk.X, pady=5)
    convert_label = tk.Label(convert_frame, text="Conversion Progress:", bg="#e6f7ff")
    convert_label.pack(side=tk.LEFT)
    convert_progress_var = tk.IntVar()
    convert_progress_bar = ttk.Progressbar(convert_frame, variable=convert_progress_var, maximum=100)
    convert_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
    convert_percentage_label = tk.Label(convert_frame, text="0%", bg="#e6f7ff")
    convert_percentage_label.pack(side=tk.LEFT)
    convert_time_label = tk.Label(progress_frame, text="", bg="#e6f7ff")
    convert_time_label.pack(fill=tk.X)

    # --- Duplicate Scan Progress ---
    scan_frame = tk.Frame(progress_frame, bg="#e6f7ff")
    scan_frame.pack(fill=tk.X, pady=5)
    scan_label = tk.Label(scan_frame, text="Duplicate Scan Progress:", bg="#e6f7ff")
    scan_label.pack(side=tk.LEFT)
    scan_progress_var = tk.IntVar()
    scan_progress_bar = ttk.Progressbar(scan_frame, variable=scan_progress_var, maximum=100)
    scan_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
    scan_percentage_label = tk.Label(scan_frame, text="0%", bg="#e6f7ff")
    scan_percentage_label.pack(side=tk.LEFT)
    scan_time_label = tk.Label(progress_frame, text="", bg="#e6f7ff")
    scan_time_label.pack(fill=tk.X)

    # --- Delete Duplicates Progress ---
    delete_frame = tk.Frame(progress_frame, bg="#e6f7ff")
    delete_frame.pack(fill=tk.X, pady=5)
    delete_label = tk.Label(delete_frame, text="Deleting Duplicates Progress:", bg="#e6f7ff")
    delete_label.pack(side=tk.LEFT)
    delete_progress_var = tk.IntVar()
    delete_progress_bar = ttk.Progressbar(delete_frame, variable=delete_progress_var, maximum=100)
    delete_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
    delete_percentage_label = tk.Label(delete_frame, text="0%", bg="#e6f7ff")
    delete_percentage_label.pack(side=tk.LEFT)
    delete_time_label = tk.Label(progress_frame, text="", bg="#e6f7ff")
    delete_time_label.pack(fill=tk.X)

    # --- Extraction Progress ---
    extract_frame = tk.Frame(progress_frame, bg="#e6f7ff")
    extract_frame.pack(fill=tk.X, pady=5)
    extract_label = tk.Label(extract_frame, text="Extraction Progress:", bg="#e6f7ff")
    extract_label.pack(side=tk.LEFT)
    extract_progress_var = tk.IntVar()
    extract_progress_bar = ttk.Progressbar(extract_frame, variable=extract_progress_var, maximum=100)
    extract_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
    extract_percentage_label = tk.Label(extract_frame, text="0%", bg="#e6f7ff")
    extract_percentage_label.pack(side=tk.LEFT)
    extract_time_label = tk.Label(progress_frame, text="", bg="#e6f7ff")
    extract_time_label.pack(fill=tk.X)

    total_time_label = tk.Label(main_frame, text="", bg="#e6f7ff", font=("Arial", 12, "bold"))
    total_time_label.pack(pady=10)

    root.mainloop()
