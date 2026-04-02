import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for faster rendering
import matplotlib.pyplot as plt
import numpy as np
import imageio
import os
import multiprocessing
from tqdm import tqdm
from functools import partial
import io
import hashlib
import pickle


def generate_settings_hash(df, window_size, step_size, bin_edges, bin_labels, y_axis_limit):
    """Generate a hash of all settings to check if anything has changed"""
    # Get the first and last timestamp as part of the configuration
    first_ts = df.iloc[0]["timestamp"] if not df.empty else 0
    last_ts = df.iloc[-1]["timestamp"] if not df.empty else 0
    
    # Combine all settings into a string
    settings_str = f"{first_ts}_{last_ts}_{window_size}_{step_size}_{bin_edges}_{bin_labels}_{y_axis_limit}"
    return hashlib.md5(settings_str.encode()).hexdigest()


def save_animation_metadata(settings_hash, total_frames, df_size):
    """Save metadata about the animation"""
    metadata = {
        "settings_hash": settings_hash,
        "total_frames": total_frames,
        "df_size": df_size,
        "timestamp": pd.Timestamp.now().isoformat()
    }
    
    os.makedirs("frames", exist_ok=True)
    with open("frames/metadata.json", "w") as f:
        json.dump(metadata, f)


def load_animation_metadata():
    """Load metadata about the previous animation"""
    try:
        if os.path.exists("frames/metadata.json"):
            with open("frames/metadata.json", "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading metadata: {e}")
    return None


def save_frame(index, frame_data):
    """Save a frame to disk"""
    os.makedirs("frames", exist_ok=True)
    frame_path = f"frames/frame_{index:05d}.png"
    imageio.imwrite(frame_path, frame_data)
    return frame_path


def load_cached_frames(num_frames):
    """Load existing frames from disk"""
    frames = []
    for i in range(num_frames):
        try:
            frame_path = f"frames/frame_{i:05d}.png"
            if os.path.exists(frame_path):
                frames.append(imageio.imread(frame_path))
            else:
                return frames  # Stop if we hit a missing frame
        except Exception as e:
            print(f"Error loading frame {i}: {e}")
            return frames
    return frames


def create_frame(start, df, window_size, bin_edges, bin_labels, y_axis_limit):
    """Function to create a single frame"""
    # Get the window data
    window = df.iloc[start:start+window_size]
    middle_date = window.iloc[window_size // 2]["date"].strftime('%Y-%m-%d')
    
    # Calculate distribution
    counts = pd.cut(window["wpm"], bins=bin_edges, labels=bin_labels, include_lowest=True).value_counts()
    counts = counts.sort_index()
    
    # Create plot in memory
    fig, ax = plt.subplots(figsize=(10, 4), dpi=100)
    bars = ax.bar(counts.index, counts.values, color="#dfd7af")
    
    # Style the plot
    ax.set_ylim(0, y_axis_limit)
    ax.set_title(f"WPM Distribution - {middle_date}", color="white")
    ax.set_ylabel("Tests", color="white")
    ax.set_facecolor("#1c1c1c")
    fig.patch.set_facecolor("#1c1c1c")
    ax.tick_params(colors="white")
    ax.spines['bottom'].set_color('white')
    ax.spines['left'].set_color('white')
    
    # Annotate bars with counts
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.annotate(f'{int(height)}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', color='white', fontsize=8)
    
    # Save figure to in-memory buffer
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    
    # Return the image data and frame index for ordering
    return (start, imageio.imread(buf))

def main():
    # Load the typing test results
    with open("monkeytype_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Building dataframe...")
    # Build DataFrame
    df = pd.DataFrame([{
        "wpm": entry["wpm"],
        "timestamp": entry["timestamp"]
    } for entry in data])

    # Define WPM bins
    bin_edges = list(range(0, 100, 10))
    bin_labels = [f"{i} - {i+9}" for i in bin_edges[:-1]]

    # Settings
    window_size = 200
    step_size = 20  # move by 10 tests per frame
    y_axis_limit = 150

    # Convert timestamps to datetime
    df["date"] = pd.to_datetime(df["timestamp"], unit='ms')
    
    # Define frame indices
    start_indices = list(range(0, len(df) - window_size + 1, step_size))
    total_frames = len(start_indices)
    
    # Generate a hash of the current settings
    settings_hash = generate_settings_hash(
        df, window_size, step_size, bin_edges, bin_labels, y_axis_limit
    )
    
    # Try to load existing metadata and frames
    metadata = load_animation_metadata()
    cached_frames = []
    
    # Check if we can reuse existing frames
    if metadata and metadata.get("settings_hash") == settings_hash:
        print("Settings haven't changed. Checking for cached frames...")
        cached_frames = load_cached_frames(metadata.get("total_frames", 0))
        print(f"Loaded {len(cached_frames)} cached frames out of {total_frames} total needed.")
    
    # Determine how many new frames we need to generate
    frames_to_generate = total_frames - len(cached_frames)
    
    if frames_to_generate > 0:
        print(f"Generating {frames_to_generate} new frames using parallel processing...")
        
        # Calculate which indices we need to generate
        indices_to_generate = start_indices[-frames_to_generate:] if cached_frames else start_indices
        
        # Use multiprocessing to create frames in parallel
        num_cpus = max(1, multiprocessing.cpu_count() - 1)  # Leave one CPU free
        print(f"Using {num_cpus} CPU cores")
        
        with multiprocessing.Pool(processes=num_cpus) as pool:
            # Create a partial function with fixed parameters
            create_frame_partial = partial(
                create_frame, 
                df=df, 
                window_size=window_size,
                bin_edges=bin_edges,
                bin_labels=bin_labels,
                y_axis_limit=y_axis_limit
            )
            
            # Process frames in parallel with progress bar
            results = list(tqdm(
                pool.imap(create_frame_partial, indices_to_generate),
                total=len(indices_to_generate)
            ))
        
        # Sort results by frame index
        results.sort(key=lambda x: x[0])
        
        # Save each new frame to disk and collect them
        new_frames = []
        for idx, img_data in results:
            # Calculate relative position in the frame sequence
            frame_pos = start_indices.index(idx)
            save_frame(frame_pos, img_data)
            new_frames.append(img_data)
        
        # Save metadata for future runs
        save_animation_metadata(settings_hash, total_frames, len(df))
        
        # Combine cached frames with new frames
        frames = cached_frames + new_frames
    else:
        print("All frames are already cached. Using existing frames.")
        frames = cached_frames
    
    print("Creating GIF...")
    # Create GIF from frames
    with imageio.get_writer("wpm_progression.gif", mode="I", duration=0.1) as writer:
        for frame in frames:
            writer.append_data(frame)
    
    print("GIF saved as wpm_progression.gif")

if __name__ == "__main__":
    main()
