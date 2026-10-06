import subprocess
import yt_dlp
import os

ydl_opts = {
    'format': 'bestvideo[height<=720]/best[height<=720]/best',
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info('https://www.youtube.com/watch?v=Zs3faMCDYNs', download=False)
    video_url = info['url']
    print("Direct video stream URL fetched successfully.")

timestamps = [
    (52, "01_dashboard_rings_view"),
    (89, "02_rings_detail"),
    (93, "03_circle_view"),
    (95, "04_areas_view"),
    (98, "05_links_view"),
    (104, "06_timeline_view"),
    (110, "07_3d_orbit_view"),
    (118, "08_links_filtered_business"),
    (130, "09_search_studio"),
    (140, "10_node_card_open_file"),
    (155, "11_left_panel_today_calendar"),
    (168, "12_right_panel_needs_action"),
    (180, "13_right_panel_routines_system"),
]

os.makedirs('scratch/frames', exist_ok=True)

for sec, name in timestamps:
    out_path = f"scratch/frames/{name}.jpg"
    cmd = [
        "ffmpeg", "-ss", str(sec), "-i", video_url,
        "-vframes", "1", "-q:v", "2", "-y", out_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if os.path.exists(out_path):
        print(f"Captured {name}.jpg at {sec}s")
    else:
        print(f"Failed to capture {name} at {sec}s")

