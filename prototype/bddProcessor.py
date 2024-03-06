from lark import Lark
import os

dsl_grammar = ""
dirname = os.path.dirname(__file__)
with open(os.path.join(dirname, 'grammar.lark'), 'r') as file:
    dsl_grammar = file.read()

dsl_parser = Lark(dsl_grammar, start='start')

text = '''
model vending system

entity vendingMachine {
  actions: insert, select, pick, cancel
  states: idle, dispensingMode, selectionMode, extraDispensingMode
  properties: option, insertedAmount, product
}

entity product {
  states: returned
}

entity inserted amount {
  states: returned
}

Scenario: Waiting_for_drink_selection
Given the vendingMachine is idle
When I insert $2
Then the vendingMachine is in selectionMode
'''

def parse (text):
    return dsl_parser.parse(text)

# ast = dsl_parser.parse(text)
# if __name__ == "__main__":
#     print(ast.pretty())
#     print("\n")
#     for sub in ast.iter_subtrees_topdown():
#         print(sub.data)
#         # print("\n")

