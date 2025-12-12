# from pypdf import PdfReader
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from core.common import get_src_path
# pdf_path = get_src_path() / "tests"/"fairy"/"2501.03468v1.pdf"

# def load_pdf(path):
#     reader = PdfReader(path)
#     texts = []
#     for page in reader.pages:
#         text = page.extract_text()
#         if text:
#             texts.append(text)
#     return "\n".join(texts)

# raw_text = load_pdf(pdf_path)
# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size=1000,       # bge-m3는 길이 강함. 800~1500 추천
#     chunk_overlap=200,
# )

# chunks = text_splitter.split_text(raw_text)

# from FlagEmbedding import BGEM3FlagModel
# model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

# import chromadb
# client = chromadb.PersistentClient(path="./chroma_bge_m3_demo")
# collection = client.get_or_create_collection(name="bge-m3-test")

# ids = [f"chunk-{i}" for i in range(len(chunks))]
# metas = [{"source": "2501.03468v1", "chunk_id": i} for i in range(len(chunks))]
# emb = model.encode(
#     chunks,
#     batch_size=8,
#     max_length=8192,
#     return_dense=True,
#     return_sparse=False,
#     return_colbert_vecs=False,
# )

# dense_vecs = emb["dense_vecs"].tolist()

# collection.add(
#     ids=ids,
#     documents=chunks,
#     embeddings=dense_vecs,
#     metadatas=metas,
# )

# query_text = "이 논문에서 multi-turn agent 구조는 어떻게 설명되고 있는가?"

# query_emb = model.encode(
#     [query_text],
#     return_dense=True,
#     return_sparse=False,
#     return_colbert_vecs=False,
# )["dense_vecs"].tolist()

# def get_collection():
#     collection.query(
#         query_embeddings=query_emb,
#         n_results=1,
#     )

