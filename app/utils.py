from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("--hostname", default="localhost", type=str, help="REST API hostname")
parser.add_argument("--port", default=8086, type=int, help="REST API port")
parser.add_argument("--debug", action='store_true', help="set to debug mode")
parser.add_argument("--data", default="", type=str, help="Path to conll data")
parser.add_argument("--limit", default=0, type=int, help="Limits sentences per corpus.")


def get_args():
    return parser.parse_args()
