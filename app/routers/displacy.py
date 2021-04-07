import bz2
import glob
import logging
import os
import xml.etree.cElementTree as ETree

import conllu
from fastapi import APIRouter

from app.utils import get_args

logger = logging.getLogger(__name__)

router = APIRouter()
args = get_args()

DOCS = {}


class Displacy:
    def __init__(self, options=None):
        if options is None:
            options = {}
        self.word_distance = options.get('wordDistance', 150)
        self.arc_distance = options.get('arcDistance', 25)
        self.highest_level = 1
        self.offset_x = options.get('offsetX', 25)
        self.offset_y = self.arc_distance * self.highest_level
        self.arrow_spacing = options.get('arrowSpacing', 10)
        self.arrow_width = options.get('arrowWidth', 10)
        self.arrow_stroke = options.get('arrowStroke', 2)
        self.word_spacing = options.get('wordSpacing', 25)
        self.font = options.get('font', 'inherit')
        self.color = options.get('color', '#000000')
        self.bg = options.get('bg', '#ffffff')

    @staticmethod
    def words_and_arcs(sent, index_offset=0):
        words = [{'text': "root", 'tag': "root"}] + [{'text': w['form'], 'tag': w['upos']} for w in sent]
        arcs = []
        for word in sent:
            word_id = int(word['id'])
            head_id = int(word['head'])
            if word_id < head_id:
                arcs.append({'start': word_id - index_offset,
                             'end': head_id - index_offset,
                             'label': word['deprel'],
                             'dir': 'left'})
            elif word_id > head_id:
                arcs.append({'start': head_id - index_offset,
                             'end': word_id - index_offset,
                             'label': word['deprel'],
                             'dir': 'right'})
        return {'words': words, 'arcs': arcs}

    @staticmethod
    def check_levels(arcs):
        levels = []
        for arc in arcs:
            level = arc['end'] - arc['start']
            if level not in levels:
                levels.append(arc['end'] - arc['start'])
        levels = list(sorted(levels))

        for arc in arcs:
            arc['level'] = levels.index(arc['end'] - arc['start']) + 1
        return levels

    def render(self, parse, settings=None):
        if settings is None:
            settings = {}

        levels = self.check_levels(parse['arcs'])
        self.highest_level = len(levels) + 1
        self.offset_y = self.arc_distance * self.highest_level

        width = self.offset_x + len(parse['words']) * self.word_distance
        height = self.offset_y + 3 * self.word_spacing

        el = self._el('svg', {
            'id': f'displacy-svg-{settings.get("index_base", 0)}',
            'classnames': ['displacy'],
            'attributes': [
                ['width', int(width * 0.80)],
                ['height', 'auto'],
                ['viewBox', '0 0 {} {}'.format(width, height)],
                ['preserveAspectRatio', 'xMinYMax meet'],
                ['data-format', 'spacy']
            ],
            'style': [
                ['color', settings.get('color', self.color)],
                ['background', settings.get('bg', self.bg)],
                ['fontFamily', settings.get('font', self.font)]
            ],
            'children': self.render_items(parse['words'], self.get_word_tag, settings.get('index_base', 0))
                        + self.render_items(parse['arcs'], self.get_arrow_tag, settings.get('index_base', 0)),
        })
        return ETree.tostring(el, encoding='unicode')

    @staticmethod
    def get_data_attributes(data):
        result = []
        for item in data:
            result.append(['data-' + item['attr'].replace(' ', '-'), item['value']])
        return result

    @staticmethod
    def render_items(items, tag_method, tag_index_base):
        result = []
        index = 0
        for item in items:
            item['index'] = index
            item['tag_index'] = tag_index_base
            result.append(tag_method(item))
            index += 1
        return result

    def get_word_tag(self, word):
        text = word.get('text')
        tag = word.get('tag')
        data = word.get('data', [])
        index = word.get('index')
        return self._el('text', {
            'classnames': ['displacy-token'],
            'attributes': [
                              ['fill', 'currentColor'],
                              ['data-tag', tag],
                              ['text-anchor', 'middle'],
                              ['y', str(self.offset_y + self.word_spacing)],
                          ] + self.get_data_attributes(data),
            'children': [
                self._el('tspan', {
                    'classnames': ['displacy-word'],
                    'attributes': [
                        ['x', str(self.offset_x + index * self.word_distance)],
                        ['fill', 'currentColor'],
                        ['data-tag', tag],
                    ],
                    'text': text,
                }),
                self._el('tspan', {
                    'classnames': ['displacy-tag'],
                    'attributes': [
                        ['x', str(self.offset_x + index * self.word_distance)],
                        ['dy', '2em'],
                        ['fill', 'currentColor'],
                        ['data-tag', tag],
                    ],
                    'text': tag,
                })
            ],
        })

    def get_arrow_tag(self, arc):
        label = arc.get('label')
        end = arc.get('end')
        start = arc.get('start')
        direction = arc.get('dir')
        level = arc.get('level')
        data = arc.get('data', [])
        index = arc.get('index')
        tag_index = arc.get('tag_index')

        start_x = self.offset_x + start * self.word_distance + self.arrow_spacing * (self.highest_level - level) / 4
        start_y = self.offset_y
        endpoint = self.offset_x + (end - start) * self.word_distance + start * self.word_distance \
                   - self.arrow_spacing * (self.highest_level - level) / 4

        curve = self.offset_y - level * self.arc_distance
        if curve == 0 and self.highest_level >= 5:
            curve = -self.word_distance

        aw2 = self.arrow_width - 2

        return self._el('g', {
            'classnames': ['displacy-arrow'],
            'attributes': [
                              ['data-dir', dir],
                              ['data-label', label],
                          ] + self.get_data_attributes(data),
            'children': [
                self._el('path', {
                    'id': 'arrow-' + str(tag_index) + '-' + str(index),
                    'classnames': ['displacy-arc'],
                    'attributes': [
                        ['d', 'M{},{} C{},{} {},{} {},{}'.format(
                            start_x, start_y,
                            start_x, curve,
                            endpoint, curve,
                            endpoint, start_y
                        )],
                        ['stroke-width', str(self.arrow_stroke) + 'px'],
                        ['fill', 'none'],
                        ['stroke', 'currentColor'],
                        ['data-dir', direction],
                        ['data-label', label]
                    ]
                }),
                self._el('text', {
                    'attributes': [
                        ['dy', '1em']
                    ],
                    'children': [
                        self._el('textPath', {
                            'xlink': '#arrow-' + str(tag_index) + '-' + str(index),
                            'classnames': ['displacy-label'],
                            'attributes': [
                                ['startOffset', '50%'],
                                ['fill', 'currentColor'],
                                ['text-anchor', 'middle'],
                                ['data-label', label],
                                ['data-dir', direction]
                            ],
                            'text': label,
                        })
                    ]
                }),
                self._el('path', {
                    'classnames': ['displacy-arrowhead'],
                    'attributes': [
                        ['d', 'M{},{} L{},{} {},{}'.format(
                            start_x if direction == 'left' else endpoint, start_y + 2,
                            start_x - aw2 if direction == 'left' else endpoint + aw2, start_y - self.arrow_width,
                            start_x + aw2 if direction == 'left' else endpoint - aw2, start_y - self.arrow_width
                        )],
                        ['fill', 'currentColor'],
                        ['data-label', label],
                        ['data-dir', direction]
                    ]
                })
            ]
        })

    @staticmethod
    def _el(tag, options):
        el = ETree.Element(tag)
        attributes = options.get('attributes', [])
        if 'classnames' in options:
            attributes.append(['class', ' '.join(options['classnames'])])
        if 'style' in options:
            styles = []
            for style in options['style']:
                styles.append(': '.join(style))
            attributes.append(['style', '; '.join(styles)])
        if 'xlink' in options:
            attributes.append(['xlink:href', options['xlink']])
        if 'text' in options:
            el.text = options['text']
        if 'id' in options:
            attributes.append(['id', options['id']])

        for attribute in attributes:
            key, value = attribute
            el.set(key, str(value))
        if 'children' in options:
            el.extend(options['children'])
        return el


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


def load_documents(corpus, corpus_path):
    global DOCS
    for doc_i, doc in enumerate(get_conll_reader(corpus_path)):
        if args.limit and doc_i > args.limit:
            return
        meta = doc[0].metadata
        DOCS[(corpus, meta["DDC:meta.basename"])] = doc


@router.on_event("startup")
async def startup_event():
    for corpus_path in glob.glob(os.path.join(args.data, '*.conll.bz2')):
        corpus = os.path.basename(corpus_path).split('.')[0]
        with bz2.open(corpus_path, 'rt') as fh:
            load_documents(corpus, fh)
        logger.info(f'Loaded corpus {corpus_path}')
        logger.info(f'Loaded #documents: {len(DOCS)}')


@router.get('/docs')
async def get_docs():
    return [{'corpus': corpus, 'docId': doc_id} for corpus, doc_id in DOCS.keys()]


@router.get('/display')
async def visualize_tree(corpus: str, doc_id: str):
    d = Displacy()
    r = []
    doc = DOCS.get((corpus, doc_id), [])
    for s_i, s in enumerate(doc):
        word_and_arcs = Displacy.words_and_arcs(s)
        r.append({
            'txt': ' '.join(w['form'] for w in s),
            'svg': d.render(word_and_arcs, {'index_base': s_i}),
            'conll': s.serialize(),
        })
    return r
