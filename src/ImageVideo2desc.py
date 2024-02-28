import csv
import os
import base64
from openai import OpenAI
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
import cv2
import pytesseract
from tqdm import tqdm
from config import api_key, tesseract_install_path

# Global variables
client = None
stop_words = None
image_prompt = ""
video_prompt = ""


def initialize():
    global client, stop_words, image_prompt, video_prompt
    # OpenAI API Key - Replace with your own API key
    client = OpenAI(api_key=api_key)

    # Download and set stopwords
    nltk.download('stopwords')
    # setting stopwords:
    stop_words = set(stopwords.words('english'))

    # Prompts for image and video
    image_prompt = "Describe this image: 1. Who is in this image 2. what he or she is doing 3. what objects or people he or she is interacting with 4. the location or scene where he or she is in 5. his or her style of clothing, including what he or she wears and the different colors of his or her clothing 6. emotional state - write only in this format in precise, consistent, and orderly manner."
    video_prompt = "These are frames from a video. Describe this video: 1. Who is in this image 2. what he or she is doing 3. what objects he or she is interacting with 4. the location or scene where he or she is in 5. his or her style of clothing, including what she or he wears and the different colors of his or her clothing 6. emotional state - write only in this format in precise, consistent, and orderly manner."


# Function to encode the media (image or video frame) to base64
def encode_media(media_path, is_video=False):
    if is_video:
        video = cv2.VideoCapture(media_path)
        success, frame = video.read()
        if success:
            _, buffer = cv2.imencode(".jpg", frame)
            video.release()
            return base64.b64encode(buffer).decode("utf-8")
    else:
        with open(media_path, "rb") as media_file:
            return base64.b64encode(media_file.read()).decode('utf-8')


# Function to process video and get frames as base64 at 1 fps
def get_video_frames(video_path):
    video = cv2.VideoCapture(video_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    frame_skip_ratio = int(fps)  # Skip frames to achieve ~1 fps

    base64_frames = []
    frame_count = 0
    while video.isOpened():
        success, frame = video.read()
        if not success:
            break

        if frame_count % frame_skip_ratio == 0:
            _, buffer = cv2.imencode('.jpg', frame)
            base64_frames.append(base64.b64encode(buffer).decode('utf-8'))

        frame_count += 1

    video.release()
    return base64_frames


# Function to parse the response content into the predefined categories
def parse_content(content):
    lines = content.split('\n')
    categories = {'Who': 'N/A', 'Action': 'N/A', 'Objects': 'N/A', 'Location': 'N/A', 'Clothing': 'N/A', 'Emotion': 'N/A', 'Media': 'N/A'}

    for line in lines:
        if line.startswith('1.'):
            categories['Who'] = line[3:].strip()
        elif line.startswith('2.'):
            categories['Action'] = line[3:].strip()
        elif line.startswith('3.'):
            categories['Objects'] = line[3:].strip()
        elif line.startswith('4.'):
            categories['Location'] = line[3:].strip()
        elif line.startswith('5.'):
            categories['Clothing'] = line[3:].strip()
        elif line.startswith('6.'):
            categories['Emotion'] = line[3:].strip()
    return categories


# analyzing images and videos from the selected folder using AI:
def get_response_from_openai(prompt, base64_media):
    try:
        messages = [
            {
                "role": "user",
                "content": [
                    prompt,
                    *([{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{media}"}}
                      for media in base64_media] if isinstance(base64_media, list) else
                      [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_media}"}}])
                ],
            },
        ]
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            temperature=1, max_tokens=4096,
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting response from OpenAI: {e}")
        return None


# Function to clean text from emojis, non-standard characters, and specified symbols
def clean_text(text):
    # Regex pattern to match emojis, non-standard characters, and symbols
    combined_pattern = re.compile("["
                                  u"\U0001F600-\U0001F64F"  # emoticons
                                  u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                  r"/\\\[\]=|<>"  # Additional symbols to exclude
                                  "]+", flags=re.UNICODE)
    return combined_pattern.sub(r'', text)


# Function to extract keywords from text. here we have a list of hebrew stop words for example.
def extract_keywords(text):
    # List of Hebrew stop words, you can add more to this list
    hebrew_stop_words = set([
        "את", "הוא", "על", "זה", "עם", "כי", "אני", "מה", "לא", "היא",
        "כמו", "אבל", "אם", "יש", "אתה", "אחד", "או", "רק", "עוד", "לי",
        "כל", "אז", "טוב", "מאוד", "לו", "של", "להיות", "בין", "עלי", "גם",
        "מנת", "לך", "מי", "כך", "תחת", "כן", "אין", "מן", "מעל", "מתוך",
        "זו", "עד", "אל", "אך", "כבר", "אפשר", "בלי", "בכל", "פי", "גדול",
        "כיון", "אחר", "אחרי", "במקום", "לעומת", "לפני", "מבלי", "מדי", "סביב", "עצמו",
        "עצמי", "עצמם", "עצמן", "עצמה", "עצמך", "עצמכם", "עצמכן", "זהה", "זהים", "זהות",
        "לעצמו", "לעצמי", "לעצמם", "לעצמן", "לעצמה", "לעצמך", "לעצמכם", "לעצמכן", "איזה", "איך",
        "איפה", "איתו", "איתי", "איתך", "איתכם", "איתכן", "איתם", "איתן", "איתנו", "אלה",
        "אלו", "אם", "אנחנו", "אני", "אס", "אשר", "את", "אתה", "אתכם", "אתכן",
        "אתם", "אתן", "באיזו", "באמצע", "באמצעות", "בגלל", "בין", "בלי", "במידה", "במקום שבו",
        "ברם", "בשביל", "בשעה ש", "בתוך", "גם", "דרך", "הוא", "היא", "היה", "היכן"
    ])  # Add your own stop words here

    # Regular expression pattern for Hebrew words, including cases that may have English letters within them
    hebrew_pattern = re.compile(r"[\u05D0-\u05EA]+[\u05D0-\u05EA'’]*|[\u05D0-\u05EA]+")

    # Find all Hebrew words in the text using the pattern
    hebrew_words = hebrew_pattern.findall(text)

    # Filter out stop words
    keywords = [word for word in hebrew_words if word not in hebrew_stop_words]
    return keywords


# Function to extract unique words/keywords from a string
def extract_unique_words(text):
    words = set(re.findall(r'\w+', text.lower()))
    return words


# Combine all unique words from both prompts
prompt_keywords = extract_unique_words(image_prompt) | extract_unique_words(video_prompt)


# Function to extract text from an image using Tesseract OCR
def extract_text_from_image(image_path):
    # Ensure the path to Tesseract-OCR executable is correct. this is the default path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_install_path

    img = cv2.imread(image_path)
    text = pytesseract.image_to_string(img, lang='eng+heb')  # specify languages as needed
    return text


# Function to extract text from the middle frame of a video (for extracting text from a video we prefer only to use a single frame and not all the frames)
def extract_text_from_middle_frame(video_path):
    # Ensure the path to Tesseract-OCR executable is correct
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    middle_frame_index = total_frames // 2
    cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_index)
    ret, frame = cap.read()
    if not ret:
        print(f"Failed to read the middle frame from {video_path}")
        return ""
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray_frame, lang='eng+heb')  # specify languages as needed
    cap.release()
    return text


# Function to process either images or videos in a given folder
def process_media(folder_path):
    results = []
    all_keywords = []  # List to store all keywords for later frequency analysis
    file_list = os.listdir(folder_path)  # List of files in the folder
    for filename in tqdm(file_list, desc='Processing files', unit='file'):
        file_path = os.path.join(folder_path, filename)
        text = ''  # Variable to hold extracted text
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            media_type = 'image'
            base64_media = encode_media(file_path)
            prompt_text = image_prompt
            # Extract text from the image using OCR
            text = clean_text(extract_text_from_image(file_path))
        elif filename.lower().endswith(('.mp4', '.avi', '.mov')):
            media_type = 'video'
            base64_media = get_video_frames(file_path)
            prompt_text = video_prompt
            # Extract text from the video's middle frame using OCR
            text = clean_text(extract_text_from_middle_frame(file_path))
        else:
            continue  # Skip non-media files

        content = get_response_from_openai(prompt_text, base64_media)
        if content:
            categories = parse_content(content)
            categories['Media'] = media_type
            categories['OCR'] = text

            # Extract keywords from the OCR text
            keywords = extract_keywords(text)
            all_keywords.extend(keywords)  # Add keywords to the all_keywords list

            categories['Keywords'] = ', '.join(keywords)
            results.append((filename, categories))
    return results, all_keywords


# Function to save results to a CSV file
def save_results_to_csv(results, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Filename', 'Who', 'Action', 'Objects', 'Location', 'Clothing', 'Emotion', 'OCR', 'Media', 'Keywords'])
        for filename, categories in results:
            writer.writerow([filename] + [categories[key] for key in ['Who', 'Action', 'Objects', 'Location', 'Clothing', 'Emotion', 'OCR', 'Media', 'Keywords']])


# Function to process the descriptions and count word frequencies
def process_and_count_words(results):
    word_details = []
    for _, categories in results:
        for category, phrase in categories.items():
            if category in ['Who', 'Action', 'Objects', 'Location', 'Clothing', 'Emotion']:  # Include 'Emotion' category
                words = phrase.split()  # Split the phrase into words based on whitespace
                for word in words:
                    word = re.sub(r'\W+', '', word.lower())
                    if word and word not in stop_words and word not in prompt_keywords:  # Check against prompt keywords
                        word_details.append((word, category))
    word_counts = Counter(word_details)
    return word_counts


# Function to save word frequencies and their corresponding types to a CSV file
def save_word_frequency_to_csv(word_counts, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Keyword', 'Type', 'Freq'])
        for (word, type), freq in word_counts.items():
            if type == 'Keywords':  # Check if type is 'Keywords' and change it to 'OCR'
                type = 'OCR'
            writer.writerow([word, type, freq])


# Function to save descriptions to a text file
def save_descriptions_to_txt(results, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        for index, (_, categories) in enumerate(results, start=1):  # Start index at 1
            file.write(f"Entry: {index}\n")  # Write the entry number instead of the filename
            for key in ['Who', 'Action', 'Objects', 'Location', 'Clothing', 'Emotion', 'OCR']:
                file.write(f"{key}: {categories[key]}\n")
            file.write("\n")  # Separate entries for readability


def main(folder_path):
    initialize()

    if folder_path:
        folder_name = os.path.basename(folder_path)
        results, _ = process_media(folder_path)

        description_output_file = os.path.join(folder_path, f'{folder_name}_media_descriptions.csv')
        save_results_to_csv(results, description_output_file)
        print(f"Results have been saved to {description_output_file}")

        word_counts = process_and_count_words(results)
        word_freq_file_path = os.path.join(folder_path, f'{folder_name}_word_frequencies.csv')
        save_word_frequency_to_csv(word_counts, word_freq_file_path)
        print(f"Word frequencies have been saved to {word_freq_file_path}")

        description_txt_file = os.path.join(folder_path, f'{folder_name} - descriptions.txt')
        save_descriptions_to_txt(results, description_txt_file)
        print(f"Descriptions have been saved to {description_txt_file}")

        return description_txt_file
