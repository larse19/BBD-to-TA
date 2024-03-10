from lark import Lark
import os

dsl_grammar = ""
dirname = os.path.dirname(__file__)
with open(os.path.join(dirname, 'grammar.lark'), 'r') as file:
    dsl_grammar = file.read()

dsl_parser = Lark(dsl_grammar, start='start')

def parse (text):
    return dsl_parser.parse(text)

# ast = dsl_parser.parse(text)
if __name__ == "__main__":
    text = open(os.path.join(dirname, "BDD.text"), "r")
    ast = parse(text.read())
    print(ast.pretty())
    print("\n")
    for sub in ast.iter_subtrees_topdown():
        print(sub)
        print("\n")

