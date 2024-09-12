import pandas as pd
from utils import clean_text
import faiss
from transformers import pipeline

from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder

embedding_model = SentenceTransformer('msmarco-distilbert-base-dot-prod-v3')
cross_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)

snippet_model = "huggingface-course/bert-finetuned-squad"
snippet_question_answerer = pipeline("question-answering", model=snippet_model)

index = faiss.read_index('data_article_100.index')
data_chunk = pd.read_csv('data_chunk_100.csv')

def fetch_data_info(dataframe_idx, score):

    '''Data should be data_chunk'''
    info = data_chunk.iloc[dataframe_idx]
    meta_dict = {}
    meta_dict['id'] = info['id']
    meta_dict['article'] = info['article']
    meta_dict['score'] = score

    return meta_dict
  
def search(query, top_k, index, model):

    query_vector = model.encode([query])
    top_k = index.search(query_vector, top_k)

    top_k_ids = list(top_k[1].tolist()[0])
    score = list(top_k[0].tolist()[0])

    results =  [fetch_data_info(idx, score) for idx, score in zip(top_k_ids, score)]

    return results

def cross_score(model_inputs):
    scores = cross_model.predict(model_inputs)
    return scores
def top_k_article(query, top_k=3):
    query = clean_text(query)

    # Search top 20 related documents
    results = search(query, top_k=20, index=index, model=embedding_model)

    # Sort the scores in descendinga order
    model_inputs = [[query, result['article']] for result in results]
    scores = cross_score(model_inputs)

    ranked_results = [{'id': result['id'], 'article': result['article'], 'score': score} for result, score in zip(results, scores)]
    ranked_results = sorted(ranked_results, key=lambda x: x['score'], reverse=True)
    
    return pd.DataFrame(ranked_results[:top_k])

def get_sorounding_words(article, start_pos, end_pos, num_words=5):
    s_pos = len(article[:start_pos].split())
    e_pos = len(article[:end_pos].split())
    
    return ' '.join(article.split()[max(0,s_pos-num_words):e_pos+num_words])

def get_answer(query, top_k=2, num_words=20):
    article_retriever_df = top_k_article(query, top_k= top_k)
    
    answer = ''
    for _, row in article_retriever_df.iterrows():
        snippet = snippet_question_answerer(question=query, context=row['article'])
        longer_snippet = get_sorounding_words(row['article'], start_pos=snippet['start'], end_pos=snippet['end'], num_words=num_words)

        if snippet['score'] > 0.5:
            answer += f"confidence score: {round(snippet['score'],3)}\ncontext: {longer_snippet}\n"
        else:
            answer += ""
        
    return answer
    
