from enum import Enum
from FlagEmbedding import BGEM3FlagModel

class EmbeddingModel(Enum):
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    TEXT_EMBEDDING_3_MEDIUM = "text-embedding-3-medium"
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"   
    
    BGE_M3 = "BAAI/bge-m3"
    BGE_UPSKYY_KOREAN = "upskyy/bge-m3-korean"
    
