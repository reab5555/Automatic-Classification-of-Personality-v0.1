import statistics
import openai
import os
import csv
import re
from tkinter import filedialog
import time
import pandas as pd
from tqdm import tqdm
from openai import OpenAI
from deep_translator import GoogleTranslator
from config import api_key


openai.api_key = api_key
client = OpenAI(api_key=api_key)

# This value is flexible as how much segments there are (higher number = fewer segments):
N_CHUNKS_INDEXES = 80


# Get the current working directory
current_directory = os.getcwd()
# File paths for various resources
general_task_path = current_directory + "/tasks/general_task.txt"
attachments_intro_path = current_directory + "/knowledge/bartholomew_attachments_definitions.txt"
attachments_job_path = current_directory + "/tasks/Attachments_task.txt"
personalities_intro_path = current_directory + "/knowledge/personalities_definitions.txt"
personalities_job_path = current_directory + "/tasks/Personalities_task.txt"
bigfive_intro_path = current_directory + "/knowledge/bigfive_definitions.txt"
bigfive_job_path = current_directory + "/tasks/BigFive_task.txt"


# Function to read text file content
def read_file_content(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


# Reading other necessary files
general_definitions = read_file_content(general_task_path)
bartholomew_definitions = read_file_content(attachments_intro_path)
JOB = read_file_content(attachments_job_path)
ptaxonomy_definitions = read_file_content(personalities_intro_path)
JOB_P = read_file_content(personalities_job_path)
bigfive_definitions = read_file_content(bigfive_intro_path)
JOB_BIGFIVE = read_file_content(bigfive_job_path)

# reading the srt file content:
def read_srt_content(srt_file_path):
    try:
        with open(srt_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Failed to read SRT file at {srt_file_path}: {e}")
        return None


# Main function to process SRT file
def process_srt_file(srt_file_path, output_directory):
    try:
        srt_text = read_srt_content(srt_file_path)
        if srt_text is None:
            raise ValueError(f"Failed to read content from {srt_file_path}")

        speaker_chunks = split_srt_to_chunks(srt_file_path)

        attachment_styles_extraction(srt_file_path, output_directory, speaker_chunks)
        personalities_extraction(srt_file_path, output_directory, speaker_chunks)
        big_five_extraction(srt_file_path, output_directory, speaker_chunks)
        general_extraction(srt_file_path, output_directory, srt_text)
        print('Getting Speakers Names...')
        get_characters_names(output_file_path_attachment, output_file_path_personalities, output_file_path_bigfive, output_file_path_general, srt_file_path, output_directory, srt_text)

        print('Processing complete.')
        # Return or handle the results as needed
    except Exception as e:
        print(f"An error occurred: {e}")
        # Handle exceptions or pass them up to the caller
        raise


# splitting the srt content into several chunks or segments to be analyzed independently:
def split_srt_to_chunks(srt_path, max_indexes=N_CHUNKS_INDEXES):
    with open(srt_path, 'r', encoding='utf-8') as file:
        srt_text = file.read()
    regex = re.compile(r'(\d+)\s+(\d{2}:\d{2}:\d{2}),\d{3}\s+-->\s+(\d{2}:\d{2}:\d{2}),\d{3}\s+(.+?)(\n\n|$)',
                       re.DOTALL)
    matches = regex.findall(srt_text)
    chunks = []
    current_chunk = ''
    current_indexes = 0
    chunk_start_time = None
    for match in matches:
        index, start_time, end_time, text = match[:4]
        speaker_match = re.search(r'Speaker (\d+):', text)
        if speaker_match:
            speaker = int(speaker_match.group(1))
            text = re.sub(r'Speaker \d+:', '', text).strip()

            if not chunk_start_time:
                chunk_start_time = start_time
            if current_indexes < max_indexes:
                current_chunk += f"Speaker {speaker}: {text} | "
                current_indexes += 1
            else:
                chunks.append((current_chunk[:-3], chunk_start_time))
                current_chunk = f"Speaker {speaker}: {text} | "
                current_indexes = 1
                chunk_start_time = start_time

    if current_chunk:
        chunks.append((current_chunk[:-3], chunk_start_time))
    return {1: chunks}


# extracting attachment styles per chunk using AI:
def attachment_styles_extraction(srt_file_path, output_file_directory, speaker_chunks):
    def classify_attachment_style(bartholomew_definitions, JOB, chunk, speaker):
        system_prompt = f"{bartholomew_definitions}\n{JOB}"
        prompt = f"text or dialogue:\n{chunk}"
        while True:  # Keep trying indefinitely
            try:
                response = client.chat.completions.create(
                    model="gpt-4-1106-preview", max_tokens=4096,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                content = response.choices[0].message.content
                return content
            except (openai.APIConnectionError, openai.InternalServerError, openai.RateLimitError):
                print("Service unavailable or rate limit exceeded. Retrying in 30 seconds...")
                time.sleep(30)

    def extract_probability_for_style(data, style):
        # Look for the style followed by ": ", with or without a space, and a decimal number
        matches = re.findall(f'{style}:\s*(0\.\d+)', data, re.IGNORECASE)
        if matches:
            return float(matches[0])
        else:
            return 0

    def extract_probabilities_for_styles(data):
        styles = ['Secured', 'Anxious-Preoccupied', 'Dismissive-Avoidant', 'Fearful-Avoidant']
        probabilities = {}
        for style in styles:
            probabilities[style] = extract_probability_for_style(data, style)
        return probabilities

    def extract_sentiment_from_explanation(data):
        matches = re.findall(r'Sentiment: (-?0\.\d+)', data, re.IGNORECASE)
        if matches:
            return float(matches[0])
        else:
            return 0


    def extract_self_from_explanation(data):
        matches = re.findall(r'Self: (-?\d+)', data)
        if matches:
            return int(matches[0])
        else:
            return 0

    def extract_emotionality_level(data):
        matches = re.findall(r'Emotionality: (\d+\.?\d*)', data)
        if matches:
            emotionality = float(matches[0])
            if 0 <= emotionality <= 10:
                return emotionality
            else:
                return 0
        else:
            return 0

    def extract_others_from_explanation(data):
        matches = re.findall(r'Others: (-?\d+)', data)
        if matches:
            return int(matches[0])
        else:
            return 0

    def extract_anxiety_avoidance(data):
        anxiety_pattern = "Anxiety: (-?[0-9]+(?:\.[0-9]+)?)"
        avoidance_pattern = "Avoidance: (-?[0-9]+(?:\.[0-9]+)?)"
        anxiety = re.search(anxiety_pattern, data)
        avoidance = re.search(avoidance_pattern, data)
        anxiety_value = float(anxiety.group(1)) if anxiety else 0
        avoidance_value = float(avoidance.group(1)) if avoidance else 0
        return anxiety_value, avoidance_value

    def extract_explanation(answer):
        matches = re.findall(r'Explanation: (.+)', answer, re.DOTALL)
        if matches:
            explanation = matches[0].strip()
        else:
            explanation = "No Explanation Found"
        return explanation

    def extract_exp_sentence(answer):
        matches = re.findall(r'Sentence: (.+)', answer, re.DOTALL)
        if matches:
            exp_sentence = matches[0].strip()
        else:
            exp_sentence = "No Sentence Found"
        return exp_sentence

# extracting individual speakers and their texts:
    def extract_speakers_answers(answer):
        # Split the text into individual speaker segments
        segments = re.split(r"(Speaker:\s*\d+)", answer)[1:]
        speakers = []
        current_speaker = ""
        # Process each segment and extract speaker information
        for segment in segments:
            if segment.startswith("Speaker"):
                if current_speaker:  # If there's an existing speaker, append it to the speakers list before resetting
                    speakers.append(current_speaker)
                current_speaker = segment.strip(":")
            else:
                split_segment = re.split(r":\s*", segment.strip(), maxsplit=1)
                if len(split_segment) == 2:  # If segment was successfully split into two parts
                    key, value = split_segment
                    current_speaker += f'\n{key.strip()}:{value.strip()}'
                else:  # If segment does not contain ":", add it as it is
                    current_speaker += f'\n{split_segment[0]}'
        # Append the last speaker to the list
        if current_speaker:
            speakers.append(current_speaker.strip())
        return speakers

    def extract_speaker_number(data):
        speaker_number_match = re.search(r"Speaker (\d+)", data)
        if speaker_number_match:
            return speaker_number_match.group(1)
        else:
            return None  # or an empty string ''

    # Initialize a dictionary to store speaker data
    speaker_data = {}

    total_chunks = sum([len(chunks) for chunks in speaker_chunks.values()])

    # Run the code for processing chunks
    chunk_counter = 0

# extracting data for each speaker, for each chunk:
    for speaker, chunks in speaker_chunks.items():
        speaker_data[speaker] = {
            'answer': [],
            'speaker_n': [],
            'chunk_index': [],
            'start_time': [],
            'chunk_text': [],
            'secured': [],
            'preoccupied': [],
            'dismissive-avoidant': [],
            'fearful-avoidant': [],
            'sentiment': [],
            'emotionality': [],
            'self_value': [],
            'others_value': [],
            'anxiety_value': [],
            'avoidance_value': [],
            'attachment_explanation': [],
            'exp_sentence': []
        }

        # Perform the calculations
        for chunk, start_time in tqdm(chunks, total=total_chunks, desc=f"Processing chunks for Attachments"):
            chunk_counter += 1

            answer = classify_attachment_style(bartholomew_definitions, JOB, chunk, speaker)
            speakers_results = extract_speakers_answers(answer)
            # Process each speaker's results
            for data in speakers_results:
                speaker_n = extract_speaker_number(data)
                probabilities = extract_probabilities_for_styles(data)
                sentiment = extract_sentiment_from_explanation(data)
                emotionality = extract_emotionality_level(data)
                self_value = extract_self_from_explanation(data)
                others_value = extract_others_from_explanation(data)
                anxiety_value, avoidance_value = extract_anxiety_avoidance(data)
                explanation = extract_explanation(data)
                exp_sentence = extract_exp_sentence(data)
                chunk_index = chunk_counter

                speaker_data[speaker]['answer'].append(speakers_results)
                speaker_data[speaker]['speaker_n'].append(speaker_n)
                speaker_data[speaker]['chunk_index'].append(chunk_index)
                speaker_data[speaker]['start_time'].append(start_time)
                speaker_data[speaker]['chunk_text'].append(chunk)
                speaker_data[speaker]['secured'].append(probabilities['Secured'])
                speaker_data[speaker]['preoccupied'].append(probabilities['Anxious-Preoccupied'])
                speaker_data[speaker]['dismissive-avoidant'].append(probabilities['Dismissive-Avoidant'])
                speaker_data[speaker]['fearful-avoidant'].append(probabilities['Fearful-Avoidant'])
                speaker_data[speaker]['sentiment'].append(sentiment)
                speaker_data[speaker]['emotionality'].append(emotionality)
                speaker_data[speaker]['self_value'].append(self_value)
                speaker_data[speaker]['others_value'].append(others_value)
                speaker_data[speaker]['anxiety_value'].append(anxiety_value)
                speaker_data[speaker]['avoidance_value'].append(avoidance_value)
                speaker_data[speaker]['attachment_explanation'].append(explanation)
                speaker_data[speaker]['exp_sentence'].append(exp_sentence)

    # Write the results for each speaker into a single CSV file
    output_file_basename = os.path.basename(srt_file_path)
    output_file_name, _ = os.path.splitext(output_file_basename)
    output_file_path = os.path.join(output_file_directory, output_file_name + ' - attachments' + ' - ' + str(
        N_CHUNKS_INDEXES) + ' chunks' + '.csv')

    global output_file_name_saved
    global output_file_path_saved
    global output_file_path_attachment
    output_file_name_saved = output_file_name
    output_file_path_saved = output_file_path
    output_file_path_attachment = output_file_path

    with open(output_file_path, "w", newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Index', 'Chunk Index', 'Timecode', 'Text', 'Speaker',
                      'Secured', 'Anxious-Preoccupied', 'Dismissive-Avoidant', 'Fearful-Avoidant',
                      'Sentiment', 'Emotionality', 'Self', 'Others', 'Anxiety', 'Avoidance', 'Attachment Explanation',
                      'Exemplary Sentence']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for speaker, data in speaker_data.items():
            for index, (answer_chunk) in enumerate(zip(data['answer']), start=1):
                speaker_number = data['speaker_n'][index - 1]  # Get the speaker number from the speaker_n list
                # Create the row dict
                row = {
                    'Index': index,
                    'Chunk Index': data['chunk_index'][index - 1],
                    'Timecode': data['start_time'][index - 1],
                    'Text': data['chunk_text'][index - 1],
                    'Speaker': speaker_number,
                    'Secured': data['secured'][index - 1],
                    'Anxious-Preoccupied': data['preoccupied'][index - 1],
                    'Dismissive-Avoidant': data['dismissive-avoidant'][index - 1],
                    'Fearful-Avoidant': data['fearful-avoidant'][index - 1],
                    'Sentiment': data['sentiment'][index - 1],
                    'Emotionality': data['emotionality'][index - 1],
                    'Self': data['self_value'][index - 1],
                    'Others': data['others_value'][index - 1],
                    'Anxiety': data['anxiety_value'][index - 1],
                    'Avoidance': data['avoidance_value'][index - 1],
                    'Attachment Explanation': data['attachment_explanation'][index - 1],
                    'Exemplary Sentence': data['exp_sentence'][index - 1],
                }
                writer.writerow(row)


# extracting personalities per chunk using AI:
def personalities_extraction(srt_file_path, output_file_directory, speaker_chunks):
    def classify_pdisorder(ptaxonomy_definitions, JOB_P, chunk, speaker):
        system_prompt = f"{ptaxonomy_definitions}\n{JOB_P}"
        prompt = f"text or dialogue:\n{chunk}"
        while True:  # Keep trying indefinitely
            try:
                response = client.chat.completions.create(
                    model="gpt-4-1106-preview", max_tokens=4096,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                content = response.choices[0].message.content
                return content
            except (openai.error.ServiceUnavailableError, openai.error.RateLimitError):
                print("Service unavailable or rate limit exceeded. Retrying in 30 seconds...")
                time.sleep(30)

    def extract_rating_for_personality(data, personality):
        # Look for the style followed by ": ", with or without a space, and a decimal number
        matches = re.findall(f'{personality}:\s*(-?\d+)', data, re.IGNORECASE)
        if matches:
            return float(matches[0])
        else:
            return 0

    def extract_ratings_for_personalities(data):
        personalities = ['Depressive', 'Paranoid', 'Schizoid-Schizotypal',
                         'Antisocial-Psychopathic', 'Borderline-Dysregulated', 'Hysteric-Histrionic', 'Narcissistic', 'Anxious-Avoidant',
                         'Dependent-Victimized', 'Obsessional']
        ratings = {}
        for personality in personalities:
            ratings[personality] = extract_rating_for_personality(data, personality)
        return ratings

    def extract_explanation_p(answer):
        matches = re.findall(r'Explanation: (.+)', answer, re.DOTALL)
        if matches:
            explanation_p = matches[0].strip()
        else:
            explanation_p = "No Explanation Found"
        return explanation_p

    def extract_exp_sentence_p(answer):
        matches = re.findall(r'Sentence: (.+)', answer, re.DOTALL)
        if matches:
            exp_sentence_p = matches[0].strip()
        else:
            exp_sentence_p = "No Sentence Found"
        return exp_sentence_p

    def extract_sentiment_from_explanation(data):
        matches = re.findall(r'Sentiment: (-?0\.\d+)', data, re.IGNORECASE)
        if matches:
            return float(matches[0])
        else:
            return 0

    def extract_depression_from_explanation(data):
        matches = re.findall(r'Depression: (-?0\.\d+)', data, re.IGNORECASE)
        if matches:
            return float(matches[0])
        else:
            return 0

    def extract_emotionality_level(data):
        matches = re.findall(r'Emotionality: (\d+\.?\d*)', data)
        if matches:
            emotionality = float(matches[0])
            if 0 <= emotionality <= 10:
                return emotionality
            else:
                return 0
        else:
            return 0

    def extract_speakers_answers_p(answer_p):
        # Split the text into individual speaker segments
        segments = re.split(r"(Speaker:\s*\d+)", answer_p)[1:]
        speakers = []
        current_speaker = ""
        # Process each segment and extract speaker information
        for segment in segments:
            if segment.startswith("Speaker"):
                if current_speaker:  # If there's an existing speaker, append it to the speakers list before resetting
                    speakers.append(current_speaker)
                current_speaker = segment.strip(":")
            else:
                split_segment = re.split(r":\s*", segment.strip(), maxsplit=1)
                if len(split_segment) == 2:  # If segment was successfully split into two parts
                    key, value = split_segment
                    current_speaker += f'\n{key.strip()}:{value.strip()}'
                else:  # If segment does not contain ":", add it as it is
                    current_speaker += f'\n{split_segment[0]}'
        # Append the last speaker to the list
        if current_speaker:
            speakers.append(current_speaker.strip())
        return speakers

    def extract_speaker_number(data):
        speaker_number_match = re.search(r"Speaker (\d+)", data)
        if speaker_number_match:
            return speaker_number_match.group(1)
        else:
            return None  # or an empty string ''

    # Initialize a dictionary to store speaker data
    speaker_data = {}

    total_chunks = sum([len(chunks) for chunks in speaker_chunks.values()])

# extracting data for each speaker per each chunk:
    for speaker, chunks in speaker_chunks.items():
        speaker_data[speaker] = {
            'chunk_index': [],
            'start_time': [],
            'speaker_n': [],
            'answer_p': [],
            'chunk_text': [],
            'depressive': [],
            'avoidant': [],
            'dependent': [],
            'schizoid-schizotypal': [],
            'antisocial': [],
            'paranoid': [],
            'narcissistic': [],
            'borderline': [],
            'obsessive–compulsive': [],
            'histrionic': [],
            'sentiment': [],
            'emotionality': [],
            'depression': [],
            'personality_explanation': [],
            'exp_sentence_p': []
        }

        chunk_counter = 0

        for chunk, start_time in tqdm(chunks, total=total_chunks, desc=f"Processing chunks for Personalities"):
            chunk_counter += 1

            answer_p = classify_pdisorder(ptaxonomy_definitions, JOB_P, chunk, speaker)
            speakers_results_p = extract_speakers_answers_p(answer_p)

            for data in speakers_results_p:
                speaker_n = extract_speaker_number(data)
                ratings_p = extract_ratings_for_personalities(data)
                explanation_p = extract_explanation_p(data)
                exp_sentence_p = extract_exp_sentence_p(data)
                sentiment = extract_sentiment_from_explanation(data)
                emotionality = extract_emotionality_level(data)
                depression = extract_depression_from_explanation(data)
                chunk_index = chunk_counter

                speaker_data[speaker]['answer_p'].append(speakers_results_p)
                speaker_data[speaker]['speaker_n'].append(speaker_n)
                speaker_data[speaker]['chunk_index'].append(chunk_index)
                speaker_data[speaker]['start_time'].append(start_time)
                speaker_data[speaker]['chunk_text'].append(chunk)
                speaker_data[speaker]['depressive'].append(ratings_p['Depressive'])
                speaker_data[speaker]['avoidant'].append(ratings_p['Anxious-Avoidant'])
                speaker_data[speaker]['dependent'].append(ratings_p['Dependent-Victimized'])
                speaker_data[speaker]['schizoid-schizotypal'].append(ratings_p['Schizoid-Schizotypal'])
                speaker_data[speaker]['antisocial'].append(ratings_p['Antisocial-Psychopathic'])
                speaker_data[speaker]['paranoid'].append(ratings_p['Paranoid'])
                speaker_data[speaker]['narcissistic'].append(ratings_p['Narcissistic'])
                speaker_data[speaker]['borderline'].append(ratings_p['Borderline-Dysregulated'])
                speaker_data[speaker]['obsessive–compulsive'].append(ratings_p['Obsessional'])
                speaker_data[speaker]['histrionic'].append(ratings_p['Hysteric-Histrionic'])
                speaker_data[speaker]['sentiment'].append(sentiment)
                speaker_data[speaker]['emotionality'].append(emotionality)
                speaker_data[speaker]['depression'].append(depression)
                speaker_data[speaker]['personality_explanation'].append(explanation_p)
                speaker_data[speaker]['exp_sentence_p'].append(exp_sentence_p)

    # Write the results for each speaker into a single CSV file
    output_file_basename = os.path.basename(srt_file_path)
    output_file_name, _ = os.path.splitext(output_file_basename)
    output_file_path = os.path.join(output_file_directory, output_file_name + " - personalities"  + ' - ' + str(
        N_CHUNKS_INDEXES) + ' chunks' + '.csv')

    global output_file_path_personalities
    output_file_path_personalities = output_file_path

    with open(output_file_path, "w", newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Index', 'Chunk Index', 'Timecode', 'Text', 'Speaker',
                      'Depressive', 'Anxious-Avoidant', 'Dependent-Victimized',
                      'Schizoid-Schizotypal', 'Antisocial-Psychopathic', 'Paranoid', 'Narcissistic',
                      'Borderline-Dysregulated', 'Obsessional', 'Hysteric-Histrionic',
                      'Sentiment', 'Emotionality', 'Depression', 'Personality Explanation', 'Exemplary Sentence']

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for speaker, data in speaker_data.items():
            for index, (answer_p_chunk) in enumerate(zip(data['answer_p']), start=1):
                speaker_number = data['speaker_n'][index - 1]  # Get the speaker number from the speaker_n list
                # Create the row dict
                row = {
                    'Index': index,
                    'Chunk Index': data['chunk_index'][index - 1],
                    'Timecode': data['start_time'][index - 1],
                    'Text': data['chunk_text'][index - 1],
                    'Speaker': speaker_number,
                    'Depressive': data['depressive'][index - 1],
                    'Anxious-Avoidant': data['avoidant'][index - 1],
                    'Dependent-Victimized': data['dependent'][index - 1],
                    'Schizoid-Schizotypal': data['schizoid-schizotypal'][index - 1],
                    'Antisocial-Psychopathic': data['antisocial'][index - 1],
                    'Paranoid': data['paranoid'][index - 1],
                    'Narcissistic': data['narcissistic'][index - 1],
                    'Borderline-Dysregulated': data['borderline'][index - 1],
                    'Obsessional': data['obsessive–compulsive'][index - 1],
                    'Hysteric-Histrionic': data['histrionic'][index - 1],
                    'Sentiment': data['sentiment'][index - 1],
                    'Emotionality': data['emotionality'][index - 1],
                    'Depression': data['depression'][index - 1],
                    'Personality Explanation': data['personality_explanation'][index - 1],
                    'Exemplary Sentence': data['exp_sentence_p'][index - 1]
                }
                writer.writerow(row)


# extracting big five traits per chunk using AI:
def big_five_extraction(srt_file_path, output_file_directory, speaker_chunks):
    def classify_bigfive(bigfive_definitions, JOB_BIGFIVE, chunk, speaker):
        system_prompt = f"{bigfive_definitions}\n{JOB_BIGFIVE}"
        prompt = f"text or dialogue:\n{chunk}"
        while True:  # Keep trying indefinitely
            try:
                response = client.chat.completions.create(
                    model="gpt-4-1106-preview", max_tokens=4096,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                content = response.choices[0].message.content
                return content
            except openai.error.RateLimitError:
                print("Rate limit exceeded. Retrying in 15 seconds...")
                time.sleep(20)  # Wait for 15 seconds before retrying

    def extract_ratings_for_trait(data, trait):
        # Look for the style followed by ": ", with or without a space, and an integer
        matches = re.findall(f'{trait}:\s*(-?\d+)', data, re.IGNORECASE)
        if matches:
            return int(matches[0])  # Return as integer, not float
        else:
            return 0

    def extract_ratings_for_traits(data):
        traits = ['Extraversion', 'Agreeableness', 'Conscientiousness', 'Neuroticism', 'Openness']
        ratings = {}
        for trait in traits:
            ratings[trait] = extract_ratings_for_trait(data, trait)
        return ratings

    def extract_explanation_bigfive(answer_bigfive):
        matches = re.findall(r'Explanation: (.+)', answer_bigfive, re.DOTALL)
        if matches:
            return matches[0].strip()
        else:
            return "No Explanation Found"

    def extract_sentiment_from_explanation(data):
        matches = re.findall(r'Sentiment: (-?0\.\d+)', data, re.IGNORECASE)
        if matches:
            return float(matches[0])
        else:
            return 0

    def extract_speakers_answers_bigfive(answer):
        # Split the text into individual speaker segments
        segments = re.split(r"(Speaker:\s*\d+)", answer)[1:]
        speakers = []
        current_speaker = ""
        # Process each segment and extract speaker information
        for segment in segments:
            if segment.startswith("Speaker"):
                if current_speaker:  # If there's an existing speaker, append it to the speakers list before resetting
                    speakers.append(current_speaker)
                current_speaker = segment.strip(":")
            else:
                split_segment = re.split(r":\s*", segment.strip(), maxsplit=1)
                if len(split_segment) == 2:  # If segment was successfully split into two parts
                    key, value = split_segment
                    current_speaker += f'\n{key.strip()}:{value.strip()}'
                else:  # If segment does not contain ":", add it as it is
                    current_speaker += f'\n{split_segment[0]}'
        # Append the last speaker to the list
        if current_speaker:
            speakers.append(current_speaker.strip())
        return speakers

    def extract_speaker_number(data):
        speaker_number_match = re.search(r"Speaker (\d+)", data)
        if speaker_number_match:
            return speaker_number_match.group(1)
        else:
            return None  # or an empty string ''

    # Initialize a dictionary to store speaker data
    speaker_data = {}

    total_chunks = sum([len(chunks) for chunks in speaker_chunks.values()])

    for speaker, chunks in speaker_chunks.items():
        speaker_data[speaker] = {
            'chunk_index': [],
            'start_time': [],
            'speaker_n': [],
            'answer_bigfive': [],
            'chunk_text': [],
            'extraversion': [],
            'agreeableness': [],
            'conscientiousness': [],
            'neuroticism': [],
            'openness': [],
            'sentiment': [],
            'bigfive_explanation': [],
        }

        chunk_counter = 0

        for chunk, start_time in tqdm(chunks, total=total_chunks, desc=f"Processing chunks for Big Five traits"):
            chunk_counter += 1

            answer_bigfive = classify_bigfive(bigfive_definitions, JOB_BIGFIVE, chunk, speaker)
            speakers_results_bigfive = extract_speakers_answers_bigfive(answer_bigfive)

            for data in speakers_results_bigfive:
                speaker_n = extract_speaker_number(data)
                ratings_bigfive = extract_ratings_for_traits(data)
                explanation_bigfive = extract_explanation_bigfive(data)
                sentiment = extract_sentiment_from_explanation(data)
                chunk_index = chunk_counter

                speaker_data[speaker]['answer_bigfive'].append(speakers_results_bigfive)
                speaker_data[speaker]['speaker_n'].append(speaker_n)
                speaker_data[speaker]['chunk_index'].append(chunk_index)
                speaker_data[speaker]['start_time'].append(start_time)
                speaker_data[speaker]['chunk_text'].append(chunk)
                speaker_data[speaker]['extraversion'].append(ratings_bigfive['Extraversion'])
                speaker_data[speaker]['agreeableness'].append(ratings_bigfive['Agreeableness'])
                speaker_data[speaker]['conscientiousness'].append(ratings_bigfive['Conscientiousness'])
                speaker_data[speaker]['neuroticism'].append(ratings_bigfive['Neuroticism'])
                speaker_data[speaker]['openness'].append(ratings_bigfive['Openness'])
                speaker_data[speaker]['sentiment'].append(sentiment)
                speaker_data[speaker]['bigfive_explanation'].append(explanation_bigfive)

    # Write the results for each speaker into a single CSV file
    output_file_basename = os.path.basename(srt_file_path)
    output_file_name, _ = os.path.splitext(output_file_basename)
    output_file_path = os.path.join(output_file_directory, output_file_name + ' - bigfive' + ' - ' + str(
        N_CHUNKS_INDEXES) + ' chunks' + '.csv')

    global output_file_path_bigfive
    output_file_path_bigfive = output_file_path

    with open(output_file_path, "w", newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Index', 'Chunk Index', 'Timecode', 'Text', 'Speaker',
                      'Extraversion', 'Agreeableness', 'Conscientiousness', 'Neuroticism', 'Openness',
                      'Sentiment', 'Big Five Explanation']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for speaker, data in speaker_data.items():
            for index, (answer_bigfive_chunk) in enumerate(zip(data['answer_bigfive']), start=1):
                speaker_number = data['speaker_n'][index - 1]  # Get the speaker number from the speaker_n list
                # Create the row dict
                row = {
                    'Index': index,
                    'Chunk Index': data['chunk_index'][index - 1],
                    'Timecode': data['start_time'][index - 1],
                    'Text': data['chunk_text'][index - 1],
                    'Speaker': speaker_number,
                    'Extraversion': data['extraversion'][index - 1],
                    'Agreeableness': data['agreeableness'][index - 1],
                    'Conscientiousness': data['conscientiousness'][index - 1],
                    'Neuroticism': data['neuroticism'][index - 1],
                    'Openness': data['openness'][index - 1],
                    'Sentiment': data['sentiment'][index - 1],
                    'Big Five Explanation': data['bigfive_explanation'][index - 1]
                }
                writer.writerow(row)

# extracting general assessment using AI:
def general_extraction(srt_file_path, output_directory, srt_text):
    def general(general_definitions, srt_text):
        system_prompt = f"{general_definitions}"
        prompt = f"text or dialogue:[{srt_text}]"
        while True:  # Keep trying indefinitely
            try:
                response = client.chat.completions.create(
                    model="gpt-4-1106-preview", max_tokens=4096,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                content = response.choices[0].message.content
                return content
            except openai.error.RateLimitError:
                print("Rate limit exceeded. Retrying in 15 seconds...")
                time.sleep(15)  # Wait for 15 seconds before retrying

    general_results = general(general_definitions, srt_text)

    # Write the results for each speaker into a single CSV file
    output_file_basename = os.path.basename(srt_file_path)
    output_file_name, _ = os.path.splitext(output_file_basename)
    global output_file_path_general
    output_file_path_general = os.path.join(output_directory, output_file_name + ' - general_assessments.txt')

    # Write the results for all speakers into a single text file
    with open(output_file_path_general, "w", encoding='utf-8') as textfile:
        textfile.write(general_results)
    print('General assessment saved to:', output_file_path_general)


# extracting characters or speakers names using AI:
def get_characters_names(output_file_path_attachment, output_file_path_personalities, output_file_path_bigfive, output_file_path_general, srt_file_path, output_directory, srt_text):
    # Read the csv file
    df = pd.read_csv(output_file_path_attachment)
    random_sample = df['Text'].drop_duplicates()
    # Convert the Series to a single string
    texts_sample = " ".join(random_sample)
    system_prompt = "Please determine for the following text or dialogue the speakers movie or tv series character name. if it is not movie or tv series character, findout the speaker name from the text. (The output format must be in this format for example - Speaker 1: Name | Speaker 2: Name):"
    prompt_characters = f"{texts_sample}\nIt is possible that the text is a dialogue from the movie or tv series title: {output_file_name_saved}"

    response = client.chat.completions.create(
        model="gpt-4-1106-preview", max_tokens=4096,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt_characters}])
    content = response.choices[0].message.content
    try:
        # Extract the speaker numbers and names using regex
        speakers = re.findall(r'Speaker (\d+): ([\w\s]+)', content)
        # Create a dictionary where the keys are the speaker numbers (as integers) and the values are the speaker names
        # along with the speaker number
        speakers_dict = {int(number): f"{name if name.strip() != 'N/A' else 'unknown'} (Speaker {number})" for
                         number, name in speakers}
        # Load the CSV file into a DataFrame
        df = pd.read_csv(output_file_path_attachment)
        # Check 'Speaker' column values
        # Convert 'Speaker' column to integer type
        df['Speaker'] = df['Speaker'].astype(int)
        # Replace the numbers with the corresponding speaker names
        df['Speaker'] = df['Speaker'].replace(speakers_dict)
        # Check 'Speaker' column after replacement
        # Save the updated DataFrame back into the CSV file
        df.to_csv(output_file_path_attachment, index=False)
    except Exception as e:
        print(f"An error occurred: {e}")
    try:
        # Extract the speaker numbers and names using regex
        speakers = re.findall(r'Speaker (\d+): ([\w\s]+)', content)
        # Create a dictionary where the keys are the speaker numbers (as integers) and the values are the speaker names
        # along with the speaker number
        speakers_dict = {int(number): f"{name if name.strip() != 'N/A' else 'unknown'} (Speaker {number})" for
                         number, name in speakers}
        df = pd.read_csv(output_file_path_personalities)
        # Check 'Speaker' column values
        # Convert 'Speaker' column to integer type
        df['Speaker'] = df['Speaker'].astype(int)
        # Replace the numbers with the corresponding speaker names
        df['Speaker'] = df['Speaker'].replace(speakers_dict)
        # Check 'Speaker' column after replacement
        # Save the updated DataFrame back into the CSV file
        df.to_csv(output_file_path_personalities, index=False)
    except Exception as e:
        print(f"An error occurred: {e}")
    try:
        # Extract the speaker numbers and names using regex
        speakers = re.findall(r'Speaker (\d+): ([\w\s]+)', content)
        # Create a dictionary where the keys are the speaker numbers (as integers) and the values are the speaker names
        # along with the speaker number
        speakers_dict = {int(number): f"{name if name.strip() != 'N/A' else 'unknown'} (Speaker {number})" for
                         number, name in speakers}
        df = pd.read_csv(output_file_path_bigfive)
        # Check 'Speaker' column values
        # Convert 'Speaker' column to integer type
        df['Speaker'] = df['Speaker'].astype(int)
        # Replace the numbers with the corresponding speaker names
        df['Speaker'] = df['Speaker'].replace(speakers_dict)
        # Check 'Speaker' column after replacement
        # Save the updated DataFrame back into the CSV file
        df.to_csv(output_file_path_bigfive, index=False)
    except Exception as e:
        print(f"An error occurred: {e}")

    try:
        # Extract speaker numbers and names using regex from the 'content' variable
        speakers = re.findall(r'Speaker (\d+): ([\w\s]+)', content)
        # Create a dictionary with speaker numbers as keys and names as values
        speakers_dict = {int(number): name.strip() for number, name in speakers}

        # Read the content of the text file
        with open(output_file_path_general, 'r', encoding='utf-8') as file:
            text_content = file.read()

        # Replace 'Speaker 1', 'Speaker 2', etc., with the corresponding names
        for speaker_number, speaker_name in speakers_dict.items():
            # Create the pattern to search for each speaker
            pattern = rf"Speaker {speaker_number}"
            # Replace the pattern in the text with 'Name (Speaker Number)'
            text_content = re.sub(pattern, f"{speaker_name} (Speaker {speaker_number})", text_content)

        # Write the modified content back to the text file or a new file
        with open(output_file_path_general, 'w', encoding='utf-8') as file:
            file.write(text_content)
    except Exception as e:
        print(f"An error occurred: {e}")


# Utility function to save analysis results to a CSV file
def save_results(results, filepath):
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as file:
            # Assuming 'results' is a list of dictionaries
            if results and isinstance(results[0], dict):
                fieldnames = results[0].keys()
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                for result in results:
                    writer.writerow(result)
            else:
                print("Invalid data format for CSV.")
    except Exception as e:
        print(f"An error occurred while saving results to {filepath}: {e}")


# Utility function to save the general assessment to a text file
def save_general_assessment(assessment, filepath):
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(assessment)
    except Exception as e:
        print(f"An error occurred while saving the general assessment to {filepath}: {e}")