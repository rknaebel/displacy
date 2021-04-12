import bz2
import glob
import logging
import os
import random
from argparse import ArgumentParser

import conllu
from fastapi import APIRouter

parser = ArgumentParser()
parser.add_argument("--hostname", default="localhost", type=str, help="REST API hostname")
parser.add_argument("--port", default=8086, type=int, help="REST API port")
parser.add_argument("--debug", action='store_true', help="set to debug mode")
parser.add_argument("--data", default="", type=str, help="Path to conll data")
parser.add_argument("--limit", default=0, type=int, help="Limits sentences per corpus.")

logger = logging.getLogger(__name__)

router = APIRouter()
DOCS = {}
SENTS = []


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
