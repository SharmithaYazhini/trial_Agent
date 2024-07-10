from langchain_community.callbacks import StreamlitCallbackHandler
import streamlit as st

from langchain_openai import ChatOpenAI
from langchain.agents import  initialize_agent
import streamlit as st
# from langchain.document_loaders import PyMuPDFLoader


# Build a sample vectorDB
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.agents.agent_toolkits import create_retriever_tool

from langchain.prompts import SystemMessagePromptTemplate

from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import FAISS
import fitz
from langchain_community.chat_message_histories import StreamlitChatMessageHistory


import sqlite3
import sys
from sqlite3 import Error
#sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')



st.title('👪  Caregiving Handbook')
st.markdown('🙏🏼 Welcome to the Handbook Healthcare Assistant! We have provided the assistant with helpful information to support you in navigating the world of caregiving for children with cancer. It has access to the Children\'s Oncology Group Family Handbook, a trusted resource for pediatric oncology information. Please give it a moment to set itself up.')

user_id = st.text_input("User ID")

class Document:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata

def process_entire_document_for_splits(doc):
    all_documents = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text_blocks = page.get_text("dict")["blocks"]
        labeled_page_number = None
        page_header = []
        page_chunks = []

        for block in text_blocks:
            if block['type'] == 0:  # text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        font = span["font"]
                        size = span["size"]

                        # Capture the full page header and labeled page number
                        if font == "Archer-Bold" and size == 8.0:
                            page_header.append(text)
                        if font == "Archer-Bold" and size == 10.0 and text.isdigit():
                            labeled_page_number = text

                        # Process text block with heading levels
                        current_heading_level = None
                        if font == "Archer-MediumItalic" and size == 38.0:
                            current_heading_level = 1
                        elif font == "Archer-SemiboldItalic" and size == 12.0:
                            current_heading_level = 2
                        elif font == "Archer-Bold" and size == 9.5:
                            current_heading_level = 3
                        elif font == "Frutiger-Italic" and size == 9.5:
                            current_heading_level = 4
                        
                        if current_heading_level:
                            page_chunks.append(f"Heading {current_heading_level}: {text}")
                        else:
                            page_chunks.append(f"Normal Text: {text}")

        if labeled_page_number:
                full_page_header = " ".join(page_header)
                page_content = " ".join(page_chunks)
                metadata = {"labeled_page_number": labeled_page_number, "page_header": full_page_header}
                document = Document(page_content, metadata)
                all_documents.append(document)

    return all_documents

# Load the PDF document
data = fitz.open("English_COG_Family_Handbook.pdf")
# data = loader.load()


# Process the document and create splits
document_splits = process_entire_document_for_splits(data)

openai_key = st.secrets["andrew_openai_api_key"]

# VectorDB setup
embedding = OpenAIEmbeddings(openai_api_key=openai_key)
vectordb = Chroma.from_documents(documents=document_splits, embedding=embedding)
retriever = vectordb.as_retriever()


# Tool
HandbookTool = create_retriever_tool(
    retriever,
    "Handbook Tool",
    "A tool to get relevant information from the children's oncology group family handbook.",
)


# Initialize chat history
if 'messages' not in st.session_state:
    # Start with first message from assistant
    st.session_state['messages'] = [{"role": "assistant", 
                                  "content": "Hi, How can I help!"}]


llm = ChatOpenAI( model_name="gpt-4-1106-preview", temperature=0, streaming=True,openai_api_key=openai_key)


tools = [HandbookTool]
# agent = create_conversational_retrieval_agent(llm, tools, verbose=True)

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
msgs = StreamlitChatMessageHistory()
memory = ConversationBufferMemory(memory_key='chat_history', chat_memory=msgs, return_messages=True)
# Create memory 'chat_history' 


system_prompt_template = SystemMessagePromptTemplate.from_template("""
You are a Handbook Healthcare Assistant with access to the Children's Oncology Group Family Handbook.
""")

agent = initialize_agent(
    tools, llm, agent="chat-conversational-react-description",
    verbose=True,
    system_prompt=system_prompt_template,
    memory=memory
)


st_callback = StreamlitCallbackHandler(st.container())
company_logo="https://www.iu.edu/images/brand/brand-expression/iu-trident-promo.jpg"


# Display chat messages from history on app rerun
# Custom avatar for the assistant, default avatar for user
for message in st.session_state.messages:
    if message["role"] == 'assistant':
        with st.chat_message(message["role"], avatar=company_logo):
            st.markdown(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


format = """
Make sure the answer is primarily based only on the document pages retireved. The answer should be dense with citations to the orginal material. Keep the answer about one paragraph long.
- Include inline citations in square brackets within the paragraph.
- List all references at the end under 'References' with the format: 'Most relevant heading, **Page Header, Page Number**'.

Example:
User Question: {
    "action": "Handbook Tool",
    "action_input": "What is the treatment for cancer?"
}
Agent Response: {
    "action": "Final Answer",
    "action_input": "
        The treatment for leukemia includes chemotherapy and radiation therapy [1].The treatment for ALL includes chemotherapy and radiation therapy [2].
        References:
        1. Leukemia Treatment Overview, **Treatment Procedures**, Page 23"
        2. ALL Treatment Overview, **Treatment Procedures**, Page 36"
}
"""








# Chat logic
if query := st.chat_input("Ask me anything"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": query})
    st.session_state.chat_history.append({"role": "user", "content": query})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant", avatar=company_logo):
        # Send user's question to our chain
        response = agent.invoke({"input": query+format, "chat_history": st.session_state.chat_history}, config={"callbacks":[st_callback]})["output"]
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.markdown(response)
        interaction = (user_id, query, response)
        #insert_interaction(conn, interaction)
        #with open("interaction_logs.txt", "a") as file:
        #    file.write(f"User ID: {user_id}, Message Prompt: {query}, Output: {response}\n")
    # Add assistant message to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
