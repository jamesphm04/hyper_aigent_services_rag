from question import get_answer
from langchain_core.messages import HumanMessage
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from conversation import get_conversation_chain

class CustomRetriever(BaseRetriever):
    
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ):
        return get_answer(query)

retriever = CustomRetriever()
rag_chain = get_conversation_chain(retriever)

chat_history = []

def handle_qa(query):
    ai_msg = rag_chain.invoke({"question": query, "chat_history": chat_history})
    if len(chat_history) >= 10:
        chat_history.pop(0)
        chat_history.pop(0)
    chat_history.extend([HumanMessage(content=query), ai_msg])
    return chat_history[-1].content

def del_history():
    global chat_history
    chat_history = []