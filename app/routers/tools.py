import logging
import os
import sys
from typing import List

import stanza
import trankit
from fastapi import APIRouter
from pydantic import BaseModel

from app.utils import Token

logger = logging.getLogger(__name__)

router = APIRouter()


class StanzaParser:
    def __init__(self):
        self.parser = stanza.Pipeline(lang='de', package="hdt", tokenize_pretokenized=True)
        self.parser("Init")

    def __call__(self, sentence: List[Token]):
        sentence_in = [[token.form if token.form else '---' for token in sentence]]
        doc = self.parser(sentence_in)
        words = doc.sentences[0].words
        for tok_i, token in enumerate(sentence):
            token.xpos = words[tok_i].xpos
            token.upos = words[tok_i].upos
            token.head = words[tok_i].head
            token.deprel = words[tok_i].deprel
        return sentence


class TrankitParser:
    def __init__(self):
        tmp_stdout = sys.stdout
        sys.stdout = sys.stderr
        self.parser = trankit.Pipeline('german-hdt', cache_dir=os.path.expanduser('~/.trankit/'))
        self.parser("Init")
        sys.stdout = tmp_stdout

    def __call__(self, sentence: List[Token]):
        sentence_in = [[token.form if token.form else '---' for token in sentence]]
        res = self.parser(sentence_in)
        words = res['sentences'][0]['tokens']
        for tok_i, token in enumerate(sentence):
            token.xpos = words[tok_i]['xpos']
            token.upos = words[tok_i]['upos']
            token.head = words[tok_i]['head']
            token.deprel = words[tok_i]['deprel']
        return sentence


TOOLS = {}


@router.on_event("startup")
async def startup_event():
    logger.info(f'Load stanza')
    TOOLS['stanza'] = StanzaParser()
    logger.info(f'Load trankit')
    TOOLS['trankit'] = TrankitParser()


class ToolRequest(BaseModel):
    tokens: List[Token]
    parser: str = "stanza"


@router.post('/', response_model=List[Token])
async def get_parses(r: ToolRequest):
    if r.parser in TOOLS:
        return TOOLS[r.parser](r.tokens)
