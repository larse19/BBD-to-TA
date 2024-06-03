import os

from lark import Lark

dsl_grammar = ""
dirname = os.path.dirname(__file__)
with open(os.path.join(dirname, 'grammar.lark'), 'r') as file:
    dsl_grammar = file.read()

dsl_parser = Lark(dsl_grammar, start='start')

def parse (text):
    return dsl_parser.parse(text)


