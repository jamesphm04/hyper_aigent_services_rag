import re
import numpy as np

def clean_text(text):
    text = re.sub(r'(\s\?)',' ',text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r"\b\?\b", "\'", text)
    text = re.sub(r"(,\?)",",", text)
    text = re.sub(r"\?+", "?", text)
    text = text.strip()
    return text
def cosine_similarity(str1, str2, model):
    vec1 = model.encode([str1])
    vec2 = model.encode([str2])
    vec2 = vec2.reshape(-1)
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    return dot_product / (norm_vec1 * norm_vec2)