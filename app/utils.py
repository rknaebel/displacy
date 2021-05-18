import logging
from argparse import ArgumentParser
from typing import List

import conllu
from fastapi import APIRouter
from pydantic import BaseModel

parser = ArgumentParser()
parser.add_argument("--hostname", default="localhost", type=str, help="REST API hostname")
parser.add_argument("--port", default=8086, type=int, help="REST API port")
parser.add_argument("--debug", action='store_true', help="set to debug mode")
parser.add_argument("--data", default="", type=str, help="Path to conll data")
parser.add_argument("--limit", default=0, type=int, help="Limits sentences per corpus.")

logger = logging.getLogger(__name__)

router = APIRouter()


def get_args():
    return parser.parse_args()


def get_conll_reader(fh):
    conll_sentences = conllu.parse_incr(fh, fields=conllu.parser.DEFAULT_FIELDS)
    doc = []
    for sent in conll_sentences:
        if "DDC:meta.file_" in sent.metadata:
            if doc:
                yield doc
            doc = []
        doc.append(sent)
    yield doc


class Token(BaseModel):
    id: int
    form: str
    upos: str
    xpos: str = ""
    head: int
    deprel: str


class Sentence(BaseModel):
    tokens: List[Token]
