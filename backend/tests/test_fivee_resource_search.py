import asyncio
from pathlib import Path

from fiveE.functions import resources


def test_missing_index_returns_without_loading_model(monkeypatch, tmp_path):
    monkeypatch.setattr(resources, 'CHROMA_PERSIST_DIRECTORY', str(tmp_path))
    monkeypatch.setattr(resources, '_cached_embedding', lambda: (_ for _ in ()).throw(AssertionError('Must not load model')))
    result=asyncio.run(resources.query_resources_content('course concept'))
    assert result['status']=='unavailable' and result['documents']==[]


def test_prepared_search_returns_actual_document_text(monkeypatch,tmp_path):
    (tmp_path/'chroma.sqlite3').touch()
    monkeypatch.setattr(resources,'CHROMA_PERSIST_DIRECTORY',str(tmp_path))
    monkeypatch.setattr(resources,'_cached_embedding',lambda: object())
    class Store:
        _collection=type('Collection',(),{'count':lambda self:1})()
        def __init__(self,**kwargs):
            assert kwargs['persist_directory']==str(tmp_path)
            assert kwargs['collection_name']=='course_materials'
        def similarity_search(self,**kwargs):
            return [type('Doc',(),{'page_content':'Actual course evidence','metadata':{'source':'course.pdf'}})()]
    monkeypatch.setattr(resources,'Chroma',Store)
    result=asyncio.run(resources.query_resources_content('course concept'))
    assert result['documents'][0]['content']=='Actual course evidence'
