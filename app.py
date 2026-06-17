import streamlit as st
from openai import OpenAI
from docx import Document
import PyPDF2
import io

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="AI Document Translator",
    layout="wide"
)

st.title("AI Document Translator")
st.write("Upload a PDF, DOCX, or TXT file and translate it into English, German, or both.")

# =========================
# API CLIENT
# =========================
client = OpenAI(
    api_key=st.secrets["API_KEY"],
    base_url="https://api.hrz.uni-giessen.de"
)

# =========================
# OPTIONAL APP PASSWORD
# =========================
if "APP_PASSWORD" in st.secrets:
    password = st.text_input("Enter app password", type="password")
    if password != st.secrets["APP_PASSWORD"]:
        st.warning("Please enter the correct password.")
        st.stop()

# =========================
# FILE READERS
# =========================
def read_txt(file):
    return file.read().decode("utf-8", errors="ignore")


def read_pdf(file):
    text = ""
    reader = PyPDF2.PdfReader(file)

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text


def read_docx(file):
    doc = Document(file)
    paragraphs = []

    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)

    return "\n".join(paragraphs)


# =========================
# TEXT SPLITTING
# =========================
def split_text(text, chunk_size=10000):
    return [
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]


# =========================
# TRANSLATION
# =========================
def translate_chunk(chunk, target_language, model_name):
    system_prompt = f"""
You are a professional academic translator.

Translate the following document into {target_language}.

Rules:
- Preserve the original meaning accurately.
- Preserve headings and structure.
- Preserve academic terminology.
- Preserve citations and references.
- Preserve tables as clearly as possible.
- Do not summarize.
- Do not omit content.
- Do not add new information.
"""

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chunk}
        ]
    )

    return response.choices[0].message.content


def translate_document(text, target_language, model_name):
    chunks = split_text(text)
    translated_chunks = []

    progress = st.progress(0)

    for i, chunk in enumerate(chunks):
        translated = translate_chunk(chunk, target_language, model_name)
        translated_chunks.append(translated)
        progress.progress((i + 1) / len(chunks))

    return "\n\n".join(translated_chunks)


# =========================
# OUTPUT FILES
# =========================
def create_docx(text, title):
    doc = Document()
    doc.add_heading(title, level=1)

    for line in text.split("\n"):
        if line.strip():
            doc.add_paragraph(line)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return buffer


def create_txt(text):
    buffer = io.BytesIO()
    buffer.write(text.encode("utf-8"))
    buffer.seek(0)
    return buffer


# =========================
# SIDEBAR SETTINGS
# =========================
st.sidebar.header("Settings")

model_name = st.sidebar.selectbox(
    "Choose model",
    [
        "openai/gpt-5.5",
        "openai/gpt-5.4"
    ],
    index=0
)

translation_option = st.sidebar.selectbox(
    "Translate to",
    [
        "English",
        "German",
        "Both English and German"
    ],
    index=2
)

# =========================
# FILE UPLOAD
# =========================
uploaded_file = st.file_uploader(
    "Upload your file",
    type=["pdf", "docx", "txt"]
)

if uploaded_file is not None:
    file_name = uploaded_file.name
    file_extension = file_name.split(".")[-1].lower()

    st.info(f"Uploaded file: {file_name}")

    try:
        if file_extension == "pdf":
            extracted_text = read_pdf(uploaded_file)
        elif file_extension == "docx":
            extracted_text = read_docx(uploaded_file)
        elif file_extension == "txt":
            extracted_text = read_txt(uploaded_file)
        else:
            st.error("Unsupported file type.")
            st.stop()

        if not extracted_text.strip():
            st.error("No readable text found in this file.")
            st.stop()

        st.subheader("Extracted Text Preview")
        st.text_area("Preview", extracted_text[:5000], height=250)

        st.write(f"Characters extracted: {len(extracted_text)}")

        if st.button("Translate Document"):
            results = {}

            with st.spinner("Translating... Please wait."):
                if translation_option in ["English", "Both English and German"]:
                    results["English"] = translate_document(
                        extracted_text,
                        "English",
                        model_name
                    )

                if translation_option in ["German", "Both English and German"]:
                    results["German"] = translate_document(
                        extracted_text,
                        "German",
                        model_name
                    )

            st.success("Translation completed!")

            for language, translated_text in results.items():
                st.subheader(f"{language} Translation Preview")
                st.text_area(
                    f"{language} Translation",
                    translated_text[:5000],
                    height=300
                )

                docx_file = create_docx(
                    translated_text,
                    f"Translated Document - {language}"
                )

                txt_file = create_txt(translated_text)

                col1, col2 = st.columns(2)

                with col1:
                    st.download_button(
                        label=f"Download {language} DOCX",
                        data=docx_file,
                        file_name=f"translated_{language.lower()}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                with col2:
                    st.download_button(
                        label=f"Download {language} TXT",
                        data=txt_file,
                        file_name=f"translated_{language.lower()}.txt",
                        mime="text/plain"
                    )

    except Exception as e:
        st.error(f"Error: {e}")
