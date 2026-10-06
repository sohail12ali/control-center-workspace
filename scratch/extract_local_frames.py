import subprocess
import os

timestamps = [
    (52, "01_dashboard_full"),
    (92, "02_circle_view"),
    (95, "03_areas_view"),
    (98, "04_links_view"),
    (104, "05_timeline_view"),
    (110, "06_3d_orbit_view"),
    (117, "07_links_filtered_business"),
    (130, "08_search_studio"),
    (140, "09_node_card_open_file"),
    (155, "10_left_panel"),
    (168, "11_right_panel_needs_action"),
    (180, "12_right_panel_routines_system"),
]

os.makedirs('scratch/frames', exist_ok=True)

for sec, name in timestamps:
    out_path = f"scratch/frames/{name}.jpg"
    cmd = [
        "ffmpeg", "-ss", str(sec), "-i", "scratch/video.mp4",
        "-vframes", "1", "-q:v", "2", "-y", out_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"Extracted {name}.jpg at {sec}s: exists={os.path.exists(out_path)}")

