from langchain_community.llms.huggingface_hub import HuggingFaceHub
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from typing import Callable

import os
from dotenv import load_dotenv

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

def get_conversation_chain(retriever: Callable, model_name: str = "gpt-3.5-turbo") -> RunnableLambda:
    """
    Params:
    * retriever: a function that given a query, return a string of context
    * model: the model to use for the conversation (default: gpt-3.5-turbo)
    Returns:
    * conversation_chain: a chained conversation that can be invoked to get the answer to a question
    """
    model = None
    if model_name == "gpt-3.5-turbo":
        model = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, api_key=openai_api_key)
    elif model_name == "flan-t5-base":
        model = HuggingFaceHub(repo_id="google/flan-t5-base", model_kwargs={"temperature":0.5, "max_length":1000})
    elif model_name == "James449/nlp-t5-qa-model":
        model = HuggingFaceHub(repo_id="James449/nlp-t5-qa-model")
    
    
    # Reformulating the question based on the chat history and the latest user question for better understanding
    contextualize_q_system_prompt = """Given a chat history and the latest user question \
                                        which might reference context in the chat history, formulate a standalone question \
                                        which can be understood without the chat history. Do NOT answer the question, \
                                        just reformulate it if needed and otherwise return it as is."""
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )
    contextualize_q_chain = contextualize_q_prompt | model | StrOutputParser()
    
    # Contextualizing the question only if there is a chat history
    def contextualized_question(input: dict):
        if input.get("chat_history"):
            return contextualize_q_chain
        else:
            return input["question"]
    
    
    
    
    # Get the asnwers only based on the given context and the conversation history
    qa_system_prompt = """you are an AI assistant. I will give you the given context, and you will have to answer only base on given knowledge, using Natural Language. You can not use your own knowledge or public sources and databases. Things to remember:
                            1. The answer has to be from the given context that I give you.
                            2. You can not use your own knowledge or public sources and databases. This will help to avoid hallucination
                            3. If the answer is not in the given context, just say I don't know
                            4. You could use the given confidence score to decide how confident you are in your answer.
                            5. If the context is an empty string, just say I don't know.
                            Here is the given context:
                        {context}"""
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )

    conversation_chain = (
        RunnablePassthrough.assign(
            context=contextualized_question | retriever
        )
        | qa_prompt
        | model
    )
    
    return conversation_chain
    