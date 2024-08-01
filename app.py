import streamlit as st
import pandas as pd
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
import tempfile

# Prompt template
prompt = PromptTemplate(
    input_variables=["chat_history", "question"],
    template="""You are a very kind and friendly AI assistant. You are
    currently having a conversation with a human. Answer the questions
    in a kind and friendly tone but in a professional manner. 
    
    chat_history: {chat_history},
    Human: {question}
    AI:"""
)

# Streamlit page configuration
st.set_page_config(
    page_title="CSV Chatbot",
    page_icon="📄",
    layout="wide"
)

# Sidebar inputs for API key and CSV upload or DB URL
st.sidebar.title("Settings")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
db_url = st.sidebar.text_input("Database Engine URL")
uploaded_csv = st.sidebar.file_uploader("Upload CSV", type=["csv"])

# Chat title
st.title("CSV Chatbot")

# Check if messages exist in session state, if not initialize
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello there, I am your CSV chatbot."}
    ]
if "db_engine" not in st.session_state:
    st.session_state.db_engine = None

# Display all chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Handle CSV upload or DB URL input
if uploaded_csv is not None:
    # Save uploaded CSV to a temporary file
    df = pd.read_csv(uploaded_csv)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        tmp_file_path = tmp_file.name
        engine = create_engine(f"sqlite:///{tmp_file_path}")
        df.to_sql("uploaded_data", engine, index=False)

    # Save DB engine in session state
    st.session_state.db_engine = engine

    # Notify user of successful CSV processing
    st.success("CSV uploaded and processed successfully!")
elif db_url:
    # Connect to the database engine
    engine = create_engine(db_url)
    db = SQLDatabase(engine=engine)

    # Save DB engine in session state
    st.session_state.db_engine = engine

    # Notify user of successful DB connection
    st.success("Connected to the database engine successfully!")

# User input
user_prompt = st.chat_input()

if user_prompt is not None and st.session_state.db_engine is not None:
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.write(user_prompt)

    # Generate AI response using the database
    llm = ChatOpenAI(openai_api_key=openai_api_key, model='gpt-4o-mini')
    memory = ConversationBufferWindowMemory(memory_key="chat_history", k=10)
    
    with st.chat_message("assistant"):
        with st.spinner("Loading..."):
            # Query the database
            agent_executor = create_sql_agent(llm, db=SQLDatabase(engine=st.session_state.db_engine), agent_type="openai-tools", verbose=True)
            response = agent_executor.invoke({"input": user_prompt})
            ai_response = response['output']
            st.write(ai_response)

    # Add assistant message to session state
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
elif user_prompt is not None:
    st.error("Please upload a CSV or provide a database engine URL first.")
