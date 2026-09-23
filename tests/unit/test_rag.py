from services.rag_service.service import chunk_text, lexical_score
def test_chunking():
    assert len(chunk_text("word "*1000))>1
def test_lexical_score():
    assert lexical_score("password reset","password reset process")>lexical_score("password reset","billing invoice")
