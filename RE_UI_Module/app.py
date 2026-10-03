import streamlit as st

from functions import (
    display_response,
    preprocess_text,
    ask_question_service,
    extract_answer_text,
)


# =========================================================
# Page Configuration
# =========================================================

st.set_page_config(
    page_title="Persian Knowledge Chatbot",
    page_icon="🤖",
    layout="centered",
)


# =========================================================
# Persian Font + RTL Style
# =========================================================

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap" rel="stylesheet">

<style>

/* =========================================================
   Persian Font
   ========================================================= */

p, h1, h2, h3, h4, h5, h6,
textarea, input, button {
    font-family: 'Vazirmatn', sans-serif;
}


/* =========================================================
   Titles and Normal Text
   ========================================================= */

p, h1, h2, h3, h4, h5, h6 {
    direction: rtl;
    text-align: right;
}


/* =========================================================
   Text Area
   ========================================================= */

textarea {
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Vazirmatn', sans-serif;
}

textarea::placeholder {
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Vazirmatn', sans-serif;
}


/* =========================================================
   Buttons
   ========================================================= */

button {
    font-family: 'Vazirmatn', sans-serif;
}


/* =========================================================
   DataFrame
   ========================================================= */

[data-testid="stDataFrame"] {
    direction: rtl;
}


/* =========================================================
   Chat Messages
   ========================================================= */

/*
   کل پیام RTL می‌شود تا آواتار سمت راست قرار بگیرد.
*/

[data-testid="stChatMessage"] {
    direction: rtl !important;
    text-align: right;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 10px;
}


/* =========================================================
   User Message
   ========================================================= */

[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageAvatarUser"]
) {
    background-color: #1b1d24;
}


/* =========================================================
   Assistant Message
   ========================================================= */

[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageAvatarAssistant"]
) {
    background-color: #20232b;
}


/* =========================================================
   Chat Message Content
   ========================================================= */

[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Vazirmatn', sans-serif;
}


/* متن داخل پیام */

[data-testid="stChatMessage"] p {
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Vazirmatn', sans-serif;
    margin: 0;
}


/* =========================================================
   Chat Avatar
   ========================================================= */

[data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] {
    direction: ltr !important;
    unicode-bidi: isolate;
    flex-shrink: 0;
}


/* =========================================================
   Chat Input
   ========================================================= */

[data-testid="stChatInput"] {
    direction: rtl;
    font-family: 'Vazirmatn', sans-serif;
    text-align: right;
}

[data-testid="stChatInput"] textarea {
    direction: rtl;
    text-align: right;
    font-family: 'Vazirmatn', sans-serif;
}

[data-testid="stChatInput"] textarea::placeholder {
    direction: rtl;
    text-align: right;
    font-family: 'Vazirmatn', sans-serif;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# Session State
# =========================================================

# Chat history

if "messages" not in st.session_state:
    st.session_state.messages = []


# Relation Extraction

if "extraction_state" not in st.session_state:
    st.session_state.extraction_state = "idle"

if "extraction_text" not in st.session_state:
    st.session_state.extraction_text = ""

if "df_entities" not in st.session_state:
    st.session_state.df_entities = None

if "df_relations" not in st.session_state:
    st.session_state.df_relations = None


# =========================================================
# Main Title
# =========================================================

st.title("🤖 سامانه دانش فارسی")


# =========================================================
# Main Tabs
# =========================================================

tab_extraction, tab_qa = st.tabs([
    "🔗 استخراج روابط",
    "💬 پرسش و پاسخ"
])


# =========================================================
# Relation Extraction
# =========================================================

with tab_extraction:

    st.header("استخراج موجودیت و رابطه")

    st.write(
        "متن فارسی خود را وارد کنید تا موجودیت‌ها و روابط موجود در آن استخراج شوند."
    )


    # -----------------------------------------------------
    # Image
    # -----------------------------------------------------

    image_placeholder = st.empty()

    with image_placeholder.container():

        _, center, _ = st.columns([1, 2, 1])

        with center:

            if st.session_state.extraction_state == "idle":

                st.image(
                    "images/image1.png",
                    width=200
                )

            elif st.session_state.extraction_state == "loading":

                st.image(
                    "images/image2.png",
                    width=200
                )

            elif st.session_state.extraction_state == "success":

                st.image(
                    "images/image3.png",
                    width=200
                )


    # -----------------------------------------------------
    # Text Input
    # -----------------------------------------------------

    text = st.text_area(
        "",
        placeholder="پدرام در سن 25 سالگی به دلیل لاغری بیش از حد مرد!",
        height=150,
        key="extraction_input"
    )


    # -----------------------------------------------------
    # Extract Button
    # -----------------------------------------------------

    if st.button(
        "🔗 استخراج روابط",
        key="extract_relations_button"
    ):

        if not text.strip():

            st.warning("لطفاً ابتدا یک متن وارد کنید.")

        else:

            st.session_state.extraction_text = preprocess_text(text)
            st.session_state.extraction_state = "loading"

            st.rerun()


    # -----------------------------------------------------
    # Processing
    # -----------------------------------------------------

    if st.session_state.extraction_state == "loading":

        progress_text = st.empty()
        progress_bar = st.progress(0)

        def update_progress(current_batch, total_batches):
            progress_text.markdown(
                f"در حال پردازش دسته‌ی **{current_batch}** از **{total_batches}**..."
            )
            progress_bar.progress(current_batch / total_batches)

        with st.spinner(
            "در حال استخراج موجودیت‌ها و روابط..."
        ):

            df_entities, df_relations = display_response(
                st.session_state.extraction_text,
                on_progress=update_progress,
            )

        progress_text.empty()
        progress_bar.empty()

        st.session_state.df_entities = df_entities
        st.session_state.df_relations = df_relations

        st.session_state.extraction_state = "success"

        st.rerun()


    # -----------------------------------------------------
    # Results
    # -----------------------------------------------------

    if st.session_state.extraction_state == "success":

        st.subheader("Knowledge Graph")


        result_tab1, result_tab2 = st.tabs([
            "📌 Entities",
            "🔗 Relationships"
        ])


        # Entities

        with result_tab1:

            st.dataframe(
                st.session_state.df_entities,
                use_container_width=True,
                hide_index=True
            )


        # Relationships

        with result_tab2:

            st.dataframe(
                st.session_state.df_relations,
                use_container_width=True,
                hide_index=True
            )

# =========================================================
# Question Answering
# =========================================================

with tab_qa:

    st.header("💬 پرسش و پاسخ")

    st.write(
        "سؤال خود را درباره اطلاعات موجود در گراف وارد کنید."
    )


    # -----------------------------------------------------
    # New Chat
    # -----------------------------------------------------

    if st.button(
        "🗑️ چت جدید",
        key="new_chat_button"
    ):

        st.session_state.messages = []

        st.rerun()


    # -----------------------------------------------------
    # Chat History
    # -----------------------------------------------------

    chat_container = st.container()

    with chat_container:

        for message in st.session_state.messages:

            with st.chat_message(message["role"]):

                st.write(message["content"])


    # -----------------------------------------------------
    # Chat Input
    # -----------------------------------------------------

    question = st.chat_input(
        "سؤال خود را بنویسید..."
    )


    # -----------------------------------------------------
    # Process Question
    # -----------------------------------------------------

    if question:

        # Generate answer first
        # تا پاسخ و سؤال با هم به تاریخچه اضافه شوند

        try:
            result = ask_question_service(question)
            answer = extract_answer_text(result)

        except RuntimeError as e:
            answer = (
                "متأسفم، در حال حاضر امکان ارتباط با سرویس "
                f"پرسش‌وپاسخ وجود ندارد. ({e})"
            )


        # Add both messages to history

        st.session_state.messages.append({
            "role": "user",
            "content": question
        })

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })


        # Rerun so that both messages
        # appear before the chat input

        st.rerun()