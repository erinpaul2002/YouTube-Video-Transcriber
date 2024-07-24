import gradio as gr
from pytubefix import YouTube
import moviepy.editor as mp
import assemblyai as aai
from dotenv import load_dotenv
import os

# Set your AssemblyAI API key
load_dotenv()
aai.settings.api_key = os.getenv(API_KEY) #"6ec9984d3fb94cba862817809576a596"  # Replace with your actual API key

def download_video(youtube_link):
    yt = YouTube(youtube_link)
    video_stream = yt.streams.filter(progressive=True, file_extension="mp4").first()
    video_stream.download(filename="downloaded_video.mp4")
    return "downloaded_video.mp4"

def extract_audio(video_path):
    video_clip = mp.VideoFileClip(video_path)
    audio_path = "audio.wav"
    video_clip.audio.write_audiofile(audio_path)
    return audio_path

def parse_timecode_to_seconds(timecode):
    hours, minutes, seconds = timecode.split(':')
    seconds, milliseconds = seconds.split(',')
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000

def format_time(seconds):
    """Converts seconds to a formatted time string hh:mm:ss."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:05.2f}"

def combine_chunks(entries):
    max_duration = 15.0
    output_list = []
    chunk_id = 1

    current_text = []
    current_start_time = None
    current_duration = 0.0

    for entry in entries:
        lines = entry.split('\n')
        timecodes = lines[1]
        text = '\n'.join(lines[2:])
        
        start_time, end_time = timecodes.split(' --> ')
        start_seconds = parse_timecode_to_seconds(start_time)
        end_seconds = parse_timecode_to_seconds(end_time)
        duration = end_seconds - start_seconds

        if current_start_time is None:
            current_start_time = start_seconds

        if current_duration + duration > max_duration:
            output_list.append({
                "chunk_id": chunk_id,
                "chunk_length": current_duration,
                "text": ' '.join(current_text),
                "start_time": current_start_time,
                "end_time": start_seconds
            })
            chunk_id += 1
            current_text = [text]
            current_start_time = start_seconds
            current_duration = duration
        else:
            current_text.append(text)
            current_duration += duration

    if current_text:
        output_list.append({
            "chunk_id": chunk_id,
            "chunk_length": current_duration,
            "text": ' '.join(current_text),
            "start_time": current_start_time,
            "end_time": current_start_time + current_duration
        })

    return output_list

def process_video(youtube_link):
    video_path = download_video(youtube_link)
    audio_path = extract_audio(video_path)
    
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_path)
    srt = transcript.export_subtitles_srt()

    if transcript.status == aai.TranscriptStatus.error:
        return "Error in transcription: " + transcript.error
    else:
        entries = srt.strip().split('\n\n')
        output_list = combine_chunks(entries)
        return "\n\n".join([f"Chunk {chunk['chunk_id']} (duration:{chunk['chunk_length']:.2f}s,start:{format_time(chunk['start_time'])} --> end:{format_time(chunk['end_time'])}): {chunk['text']}" for chunk in output_list])

# Gradio interface
iface = gr.Interface(
    fn=process_video,
    inputs=gr.Textbox(label="Enter YouTube Video Link"),
    outputs=gr.Textbox(label="Transcribed Text"),
    title="YouTube Video Transcriber",
    description="Enter a YouTube link to get a transcribed text divided into chunks of up to 15 seconds."
)

iface.launch()
