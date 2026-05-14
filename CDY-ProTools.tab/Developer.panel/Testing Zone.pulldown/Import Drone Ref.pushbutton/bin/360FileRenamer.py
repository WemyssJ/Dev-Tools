import os

# --------------------------
# CONFIG: set your folder here
# --------------------------
folder_path = r"C:\Users\wemyssj\Craddys\CraddysDrones - 13914 - Plots 2 - 3, Silverthorne Lane\20260318 Drone Canal Wall Photos"  # <-- replace with your folder path

# Loop through all files in the folder
for filename in os.listdir(folder_path):
    # Check if file ends with .jpg (case-insensitive)
    if filename.lower().endswith(".jpg"):
        old_path = os.path.join(folder_path, filename)
        # Replace .jpg with .360.jpg
        new_filename = filename[:-4] + ".360.jpg"
        new_path = os.path.join(folder_path, new_filename)
        
        # Rename the file
        os.rename(old_path, new_path)
        print(f"Renamed: {filename} -> {new_filename}")

print("All .jpg files have been renamed.")
