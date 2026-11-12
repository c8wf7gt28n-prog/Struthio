"""Reference-compatible P17 adapter; non-PDF native locators stay unchanged."""
from pathlib import Path
import hashlib
from . import reference_extract as legacy,pdf_evidence as pdf
from .reference_extract import digest,search_text,scripts

def rule_hash():return hashlib.sha256((legacy.rule_hash()+pdf.rule_hash()).encode()+Path(__file__).read_bytes()).hexdigest()
def bounded(name,path,digest_expected):
    if Path(name).suffix.lower()!='.pdf':return legacy.bounded(name,path,digest_expected)
    return pdf.bounded('extract',path,digest_expected)
