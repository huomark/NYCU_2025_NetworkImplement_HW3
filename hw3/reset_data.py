import shutil
import os

def remove_dir(path):
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            print(f"Removed {path}")
        except Exception as e:
            print(f"Failed to remove {path}: {e}")

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    
    # Server Data
    server_data = os.path.join(root, "server_data")
    remove_dir(server_data)
    
    # Player Downloads
    player_downloads = os.path.join(root, "player", "downloads")
    remove_dir(player_downloads)
    
    print("Cleanup complete.")

if __name__ == "__main__":
    main()
