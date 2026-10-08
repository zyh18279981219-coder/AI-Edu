import asyncio
from pathlib import Path
import pytest
from fastapi import HTTPException

import app


@pytest.mark.parametrize('folder,suffix',[('backend','.pdf'),('backend','.PDF'),('root','.pdf')])
def test_pdf_read_and_selection_use_same_runtime_file(monkeypatch,tmp_path,folder,suffix):
    project=tmp_path/'root';backend=tmp_path/'backend'
    target=(backend if folder=='backend' else project)/'data/Book'/('1'+suffix)
    target.parent.mkdir(parents=True);target.write_bytes(b'%PDF-1.4')
    monkeypatch.setattr(app,'PROJECT_ROOT',project);monkeypatch.setattr(app,'BASE_DIR',backend)
    response=asyncio.run(app.get_pdf('backend/data/Book/1.PDF'))
    assert Path(response.path)==target
    result=asyncio.run(app.select_pdf(app.PDFSelection(pdf_path='data/Book/1.PDF'),session_id=None))
    assert result['success']
