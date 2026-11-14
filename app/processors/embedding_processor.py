
from sentence_transformers import SentenceTransformer


model = None


def load_embedding_model():
    global model

    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")

    return model


def create_embedding(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Text for embedding cannot be empty.")

    embedding_model = load_embedding_model()

    embedding = embedding_model.encode(
        text,
        convert_to_numpy=True
    )

    return embedding.tolist()
