import openai
import time
import os
import math
from collections import defaultdict
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


# Replace 'your_api_key_here' with your actual API key
api_key = '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'

# Configure the OpenAI API client
openai.api_key = api_key

def classify_attachment_style(text):
    while True:  # Keep trying until the API call is successful
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content" : text}]
            )
            #print(response)
            content = response['choices'][0]['message']['content']
            answer = content
            return answer

        except openai.error.RateLimitError:
            print("Rate limit exceeded. Retrying in 15 seconds...")
            time.sleep(15)  # Wait for 15 seconds before retrying


def answer_to_attachment_style(answer):
    if "Secure" in answer:
        return "Secure Attachment Style"
    elif "Preoccupied" in answer:
        return "Preoccupied Attachment Style"
    elif "Dismissing" in answer:
        return "Dismissive-Avoidant Attachment Style"
    elif "Fearful" in answer:
        return "Fearful-Avoidant Attachment Style"
    else:
        return "Unknown Attachment Style"

sentences = [

    # SECURE:
    #Original:
    "It is relatively easy for me to become emotionally close to others  - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I am comfortable depending on others and having others depend on me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I don’t worry about being alone or having others not accept me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    #Confidence:
    "I find it relatively easy to get close to others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I feel comfortable sharing my private thoughts and feelings with others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I'm comfortable depending on others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I'm confident that others will be there for me when I need them - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I'm confident that others find me to be a valuable person - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I am comfortable developing close relationships with others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I'm confident that most people are happy to have me as a friend - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I find it easy to be emotionally close to others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I am comfortable with other people depending on me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I'm comfortable having others share their feelings with me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    #ASQ:
    "I feel at ease in emotional relationships - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I trust other people and I like it when other people can rely on me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I find it easy to get engaged in close relationships with other people - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I feel at ease in intimate relationships - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I think it is important that people can rely on each other - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I trust that others will be there for me when I need them - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    #RSQ:
    "I want to be completely emotionally intimate with others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I don't worry excessively about others not accepting me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I don't worry excessively about being alone - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I am comfortable having others depend on me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I am comfortable depending on others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I do not often worry about being abandoned - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I know that others will be there when I need them - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I am comfortable with my partner depending on me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I am confident that most people are happy to have me as a friend - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",

    # PREOCUPPIED:
    #Original:
    "I want to be completely emotionally intimate with others, but I often find that others are reluctant to get as close as I would like - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I am uncomfortable being without close relationships, but I sometimes worry that others don’t value me as much as I value them - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    #Need for Approval:
    "I often worry that romantic partners don't really love me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    ###"I worry about being alone or abandoned - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I worry about having others not accept me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I worry that others don't value me as much as I value them - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I worry that I won't measure up to other people - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I often worry about what others think of me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    ###"I often feel that others won't want to stay with me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    ###"I worry about being abandoned by those I am close to - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    ###"I worry that others won't like me if they get to know the real me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    # Preoccupation with Relationships:
    "I worry a lot about my relationships - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I want to merge completely with another person - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I sometimes feel that I force others to show more feeling and commitment than they would like - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I find that others are reluctant to get as close as I would like - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I often worry that my partner doesn't really care for me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I worry that others will not care about me as much as I care about them - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    #ASQ:
    "I often wonder whether people like me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I have the impression that usually I like others better than they like me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "It is important to me to know if others like me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    #RSQ:
    "I am often worried that my partner does not really love me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "My desire to merge completely sometimes scares people away - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I worry that romantic partners won't care about me as much as I care about  - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",


    # DISMISSING:
    #Original:
    "I am comfortable without close emotional relationships - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "It is very important to me to feel independent and self-sufficient, and I prefer not to depend on others or have others depend on me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    #Discomfort with Closeness:
    "I find it difficult to allow myself to depend on others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    ###"I find it difficult to trust others completely - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    ###"I feel uncomfortable when someone gets too close to me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    ###"I am somewhat uncomfortable being close to others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I prefer not to show others how I feel deep down - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I find it difficult to depend on other people - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    ###"I worry about others getting too close to me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    ###"I worry that I will be hurt if I allow myself to get too close to others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    #Relationships as Secondary:
    ###"I often worry that romantic partners will want to get too close to me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I don't feel the need to have close relationships - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I don't feel the need to have close emotional relationships - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    #ASQ:
    "I prefer that others are independent of me and I am independent of them - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I don't worry about being alone: I don't need other people that strongly - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    #RSQ:
    "I prefer not to have others depend on me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I prefer not to depend on others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    ###"It is very important to me to feel self-sufficient - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    ###"I find it difficult to get close to others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I try to avoid getting too close to my partner - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    ###"It is important to me to feel independent - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",

    # FEARFUL:
    #Original:
    "I am somewhat uncomfortable getting close to others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I want emotionally close relationships, but I find it difficult to trust others completely, or to depend on them - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    "I sometimes worry that I will be hurt if I allow myself to become too close to others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style",
    #ASQ:
    "I would like to be open to others but I feel that I can't trust other people - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I would like to have close relationships with other people but I find it difficult to fully trust them - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I am afraid that I will be deceived when I get too close with others - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I am wary to get engaged in close relationships because I am afraid to get hurt - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    #RSQ:
    "I am nervous when anyone gets too close to me - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    ###"I often worry about being alone - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",
    "I worry about being abandoned by those I am close to - what attachment style this sentence fit best? Secure Attachment Style, Preoccupied Attachment Style, Dismissing Attachment Style, Fearful Attachment Style.",

]


true_classifications = [
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",
    "Secure Attachment Style",

    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",
    "Preoccupied Attachment Style",

    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Dismissive-Avoidant Attachment Style",


    "Fearful-Avoidant Attachment Style",
    "Fearful-Avoidant Attachment Style",
    "Fearful-Avoidant Attachment Style",
    "Fearful-Avoidant Attachment Style",
    "Fearful-Avoidant Attachment Style",
    "Fearful-Avoidant Attachment Style",
    "Fearful-Avoidant Attachment Style",
    "Fearful-Avoidant Attachment Style",
    "Fearful-Avoidant Attachment Style",

]

attachment_styles = [
    "Secure Attachment Style",
    "Preoccupied Attachment Style",
    "Dismissive-Avoidant Attachment Style",
    "Fearful-Avoidant Attachment Style",
]

confusion_matrix = defaultdict(lambda: defaultdict(int))

for i, (sentence, true_style) in enumerate(zip(sentences, true_classifications)):
    print(f"Sentence {i + 1}: {sentence}")
    answer = classify_attachment_style(sentence)
    attachment_style = answer_to_attachment_style(answer)
    print(f"\nThe attachment style of the sentence is: {attachment_style}")
    print("\n" + "-" * 80 + "\n")

    # Update confusion matrix
    confusion_matrix[true_style][attachment_style] += 1

# Display confusion matrix
confusion_matrix_df = pd.DataFrame(confusion_matrix, index=attachment_styles, columns=attachment_styles)
print("Confusion Matrix:")
print(confusion_matrix_df)

# Calculate accuracy
total_predictions = sum(sum(values.values()) for values in confusion_matrix.values())
correct_predictions = sum(confusion_matrix[i][i] for i in attachment_styles)
accuracy = correct_predictions / total_predictions
print(f"Accuracy: {accuracy:.2f}")
# Calculate precision and recall
precision = np.diag(confusion_matrix_df) / np.sum(confusion_matrix_df, axis=0)
recall = np.diag(confusion_matrix_df) / np.sum(confusion_matrix_df, axis=1)

# Calculate overall precision and recall
overall_precision = np.mean(precision)
overall_recall = np.mean(recall)

# Visualize confusion matrix using seaborn
plt.figure(figsize=(8, 6))
sns.heatmap(confusion_matrix_df, annot=True, cmap='coolwarm', fmt='g', linewidths=0.5)
plt.xticks(fontsize=8)
plt.yticks(fontsize=8)
plt.xlabel("Predicted")
plt.ylabel("Actual")

# Display accuracy, overall precision, and overall recall
plt.text(0.5, -0.5, f"Accuracy: {accuracy:.2f}", fontsize=12)
plt.text(0.5, -1.0, f"Precision: {overall_precision:.2f}", fontsize=12)
plt.text(0.5, -1.5, f"Recall: {overall_recall:.2f}", fontsize=12)

plt.tight_layout()  # Add this line to adjust the layout
plt.show()