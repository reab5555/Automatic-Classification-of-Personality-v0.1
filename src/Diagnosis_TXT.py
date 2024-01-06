import time
from openai import OpenAI
import os
from config import api_key


# waiting couple of seconds before connecting to server:
time.sleep(5)
# Initialize the OpenAI client with your API key
client = OpenAI(api_key=api_key)


# Function to read text file content
def read_file_content(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


# analyzing the text file using AI:
def analyze_text_file(description_txt_file):
    # Check if the file path is a text file
    if not description_txt_file.endswith('.txt'):
        raise ValueError("Unsupported file type")

    # Reading the description text file
    text_to_analyze = read_file_content(description_txt_file)

    # Get the current working directory
    current_directory = os.getcwd()
    # File paths for various resources
    instructions_for_general_path = current_directory + "/tasks/general_task - Single_Speaker.txt"
    attachments_intro_path = current_directory + "/knowledge/bartholomew_attachments_definitions.txt"
    attachments_job_path = current_directory + "/tasks/Attachments_task - Single_Speaker.txt"
    personalities_intro_path = current_directory + "/knowledge/personalities_definitions.txt"
    personalities_job_path = current_directory + "/tasks/Personalities_task - Single_Speaker.txt"
    bigfive_intro_path = current_directory + "/knowledge/bigfive_definitions.txt"
    bigfive_job_path = current_directory + "/tasks/BigFive_task - Single_Speaker.txt"

    # Reading other necessary files
    instructions_for_general_summary = read_file_content(instructions_for_general_path)
    bartholomew_definitions = read_file_content(attachments_intro_path)
    JOB = read_file_content(attachments_job_path)
    ptaxonomy_definitions = read_file_content(personalities_intro_path)
    JOB_P = read_file_content(personalities_job_path)
    bigfive_definitions = read_file_content(bigfive_intro_path)
    JOB_BIGFIVE = read_file_content(bigfive_job_path)

    # Analysis part with all selected columns analyzed as a single text
    base_name = os.path.splitext(os.path.basename(description_txt_file))[0]
    output_file_path = os.path.join(os.path.dirname(description_txt_file), f"{base_name} - diagnosis results.txt")
    print('Analyzing...')

# saving results:
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        # Updated variable name to match the new function output
        task = f"tasks: first task: {instructions_for_general_summary}\nsecond task: {JOB}\n{JOB_P}\n{JOB_BIGFIVE}\ndefinitions: {bartholomew_definitions}\n{ptaxonomy_definitions}\n{bigfive_definitions}"
        prompt = f"input text:[{text_to_analyze}]\n"
        response = client.chat.completions.create(model="gpt-4-1106-preview", max_tokens=4096,
        messages=[
        {"role": "system", "content": task},
        {"role": "user", "content": prompt}])
        content = response.choices[0].message.content
        #print('Text input:', single_text_to_analyze)
        #print(f"Results: {content}")
        output_file.write(content)
        print(f"Results saved to {output_file_path}")


