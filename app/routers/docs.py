import bz2
import glob
import logging
import os
import random
from typing import List

from fastapi import APIRouter

from app.utils import get_args, get_conll_reader, Sentence, Token

logger = logging.getLogger(__name__)

router = APIRouter()
args = get_args()

DOCS = {}
SENTS = []


def load_documents(corpus, corpus_path, limit=0):
    global DOCS, SENTS
    for doc_i, doc in enumerate(get_conll_reader(corpus_path)):
        if limit and doc_i > limit:
            return
        meta = doc[0].metadata
        DOCS[(corpus, meta["DDC:meta.basename"])] = doc
        SENTS.extend(doc)


@router.on_event("startup")
async def startup_event():
    global SENTS
    args = get_args()
    for corpus_path in glob.glob(os.path.join(args.data, '*.conll.bz2')):
        corpus = os.path.basename(corpus_path).split('.')[0]
        with bz2.open(corpus_path, 'rt') as fh:
            load_documents(corpus, fh, args.limit)
        logger.info(f'Loaded corpus {corpus_path}')
        logger.info(f'Loaded #documents: {len(DOCS)}')
    random.shuffle(SENTS)


@router.get('/')
async def get_docs():
    return [{'corpus': corpus, 'docId': doc_id} for corpus, doc_id in DOCS.keys()]


@router.get('/info')
async def get_info():
    return {
        'tags': sorted({t['upos'] for s in SENTS for t in s}),
        'deprels': sorted({t['deprel'] for s in SENTS for t in s}),
    }


@router.get('/sentence/random', response_model=List[Token])
async def get_random_sentence():
    sent = random.choice(SENTS)
    return sent


@router.get('/doc', response_model=List[Sentence])
async def get_doc(corpus: str, doc_id: str):
    return DOCS.get((corpus, doc_id), [])
