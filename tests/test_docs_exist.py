from pathlib import Path

def test_docs_exist():
    assert Path('README.md').exists()
    assert Path('docs/USER_GUIDE.md').exists()