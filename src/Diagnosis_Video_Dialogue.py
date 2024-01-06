import os
import tqdm
import moviepy.editor as mp
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from config import api_key
from openai import OpenAI

client = OpenAI(api_key=api_key)

# Assuming your current directory setup and file paths are correct
current_directory = os.getcwd()
ffmpeg_path = current_directory + "/ffmpeg/bin"

# File paths for various resources
attachments_intro_path = os.path.join(current_directory, "knowledge", "bartholomew_attachments_definitions.txt")
attachments_job_path = os.path.join(current_directory, "tasks", "Attachments_task.txt")
personalities_intro_path = os.path.join(current_directory, "knowledge", "personalities_definitions.txt")
personalities_job_path = os.path.join(current_directory, "tasks", "Personalities_task.txt")
bigfive_intro_path = os.path.join(current_directory, "knowledge", "bigfive_definitions.txt")
bigfive_job_path = os.path.join(current_directory, "tasks", "BigFive_task.txt")


def read_file_content(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


# Reading other necessary files
bartholomew_definitions = read_file_content(attachments_intro_path)
JOB = read_file_content(attachments_job_path)
ptaxonomy_definitions = read_file_content(personalities_intro_path)
JOB_P = read_file_content(personalities_job_path)
bigfive_definitions = read_file_content(bigfive_intro_path)
JOB_BIGFIVE = read_file_content(bigfive_job_path)


# transcribing the video audio to text:
def transcribe_mp4(file_path):
    # Set the path for ffmpeg
    os.environ["PATH"] += os.pathsep + ffmpeg_path

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model_id = "openai/whisper-large-v3"
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    )
    model.to(device)

    processor = AutoProcessor.from_pretrained(model_id)

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        chunk_length_s=30,
        batch_size=16,
        return_timestamps=False,
        torch_dtype=torch_dtype,
        device=device,
    )

    # Convert MP4 to MP3
    video = mp.VideoFileClip(file_path)
    mp3_path = file_path.replace('.mp4', '.mp3')
    video.audio.write_audiofile(mp3_path)
    file_path = mp3_path  # Update file path to the converted MP3 file

    transcription = ""

    with open(file_path, 'rb') as audio_file:
        audio_data = audio_file.read()
        chunk_size = 30 * processor.feature_extractor.sampling_rate * 2
        total_chunks = len(audio_data) // chunk_size

        for i in tqdm.tqdm(range(total_chunks)):
            chunk = audio_data[i * chunk_size:(i + 1) * chunk_size]
            result = pipe(chunk)
            transcription += result["text"]

    # Define the save path based on the original file path with '- diagnosis results' added
    original_file_name = os.path.splitext(os.path.basename(file_path))[0]
    save_directory = os.path.dirname(file_path)
    save_path = os.path.join(save_directory, f"{original_file_name} - diagnosis results.txt")

    with open(save_path, 'w', encoding='utf-8') as file:
        file.write(transcription)

    # Delete the converted MP3 file
    if os.path.exists(mp3_path):
        os.remove(mp3_path)

    return transcription, save_path


# analyzing the transcribed text using AI:
def analyze_with_openai(text):
    response = client.chat.completions.create(model="gpt-4-1106-preview", max_tokens=4096,
                                              messages=[
                                                  {"role": "system", "content": f"tasks: {bartholomew_definitions}\n{ptaxonomy_definitions}\n{bigfive_definitions}\ntasks:\n{JOB}\n{JOB_P}\n{JOB_BIGFIVE}\n"},
                                                  {"role": "user", "content": f"input text:[{text}]\n"}])
    content = response.choices[0].message.content
    return content


def analyze_video_dialogue(file_path):
    if file_path and file_path.endswith('.mp4'):
        transcription, save_path = transcribe_mp4(file_path)
        analysis_result = analyze_with_openai(transcription)

        # Save the analysis result
        analysis_save_path = save_path.replace("diagnosis results", "analysis results")
        with open(analysis_save_path, 'w', encoding='utf-8') as file:
            file.write(analysis_result)

        print(f"Transcription saved to: {save_path}")
        print(f"Analysis saved to: {analysis_save_path}")
        return analysis_save_path
    else:
        raise ValueError("Unsupported file type, please select an MP4 file")
