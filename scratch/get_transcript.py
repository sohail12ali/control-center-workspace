from youtube_transcript_api import YouTubeTranscriptApi

ytt = YouTubeTranscriptApi()
transcript_list = ytt.list(video_id='Zs3faMCDYNs')
transcript = transcript_list.find_transcript(['en']).fetch()

with open('scratch/transcript.txt', 'w', encoding='utf-8') as f:
    for entry in transcript:
        # Check if dict or object
        if hasattr(entry, 'text'):
            f.write(f"{entry.start:.1f}s: {entry.text}\n")
        elif isinstance(entry, dict):
            f.write(f"{entry.get('start', 0):.1f}s: {entry.get('text', '')}\n")
        else:
            f.write(f"{str(entry)}\n")
print(f"Transcript saved! {len(transcript)} entries.")

