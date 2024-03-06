import os

from bddProcessor import parse
from lark import Token, Tree

dirname = os.path.dirname(__file__)


startString = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' 'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>
<nta>\n'''

full_text_file = startString

outfile = open(os.path.join(dirname, "prototype.xml"), "w")


declarationStart = '<declaration>\n'
declarationEnd = '</declaration>\n'
globalDeclarations = ""

text = open(os.path.join(dirname, "BDD.text"), "r")
ast = parse(text.read())
text.close

location_names = []
variable_names = []

class Entity:
    def __init__(self, name, states, actions, properties):
        self.name = name
        self.states = states
        self.actions = actions
        self.properties = properties

    def __str__(self):
        return f"Name: {self.name}\nStates: {self.states}\nActions: {self.actions}\nProperties: {self.properties}"

entities = []
entity_names = []

# Collect all entities
for entity in ast.find_data("entity"):
    entity_name = entity.children[0].lstrip(" ").rstrip("\n")
    entity_names.append(entity_name)
    states = []
    actions = []
    properties = []
    for state in entity.find_data("states"):
        states = list(map(lambda s: s.value, state.children ))
    for action in entity.find_data("actions"):
        actions = list(map(lambda a: a.value, action.children ))
    for property in entity.find_data("properties"):
        properties = list(map(lambda p: p.value, property.children ))
    entities.append(Entity(entity_name, states, actions, properties))

# go through ast. if any tokens of type "ENTITY_NAME" has a value that is not in entity_names, then change the type to "PROPERTY_NAME"
for tree in ast.iter_subtrees():
    for token in tree.children:
        if not isinstance(token, Token):
            continue
        if token.type == "ENTITY_NAME" and token.value not in entity_names:
            token.type = "PROPERTY_NAME"

# Rule 1: The <domain model name> is converted into the name of the NTA, which consists of a set of TAs.
# for test in ast.find_data("model"):
#     for child in test.children:
#         print(child)
#         print("\n")
model_name = next(ast.find_data("model")).children[0].lstrip(" ").rstrip("\n")



#Rule 2 The <entity name> of the first entity (main entity) is implemented as the name of the TA.
ta_name = next(ast.find_data("entity")).children[0].lstrip(" ").rstrip("\n")


scenarios = ast.find_data("scenario")

#Rule 3 The <state name> that appears in the Given clause of the first scenario is mapped to initial location of the TA.
first_scenario = next(ast.find_data("scenario"))
given_clause = next(first_scenario.find_data("given"))
initial_location = ""

for child in given_clause.children:
    if isinstance(child, Token):
        if(child.type == "STATE_NAME"):
            initial_location = child.value
            location_names.append(child.value)
            break

# From here on out, all the rules are implemented in on each scenario
for scenario in scenarios:
    #R4 The <state name> placed after is or is in is modeled as location name in the TA.
    for then_clause in scenario.find_data("then"):
        for state_name in then_clause.children:
            if isinstance(state_name, Token):
                if(state_name.type == "STATE_NAME" and state_name.value not in location_names):
                    location_names.append(state_name.value)
                    break

    #R5 Whenever properties are mentioned in the scenarios, the <property name> becomes a variable of any type in the TA
    # def get_entity(child):
    #     if isinstance(child, Token):
    #         if(child.type == )
    #for entity_property in scenario.find_data("entity_property"):
        #print(entity_property)

globalDeclarationFinal = declarationStart + globalDeclarations + declarationEnd
full_text_file += globalDeclarationFinal
full_text_file += "<template>\n"
full_text_file += "\t<name>" + ta_name + "</name>\n"


location_dict = {}
location_index = 0
for location_name in location_names:
    id = "id" + location_index.__str__()
    location_dict[location_name] = id
    location_text = f'''\t<location id="{id}" x="{location_index * 50}" y="0"> 
        <name x="{location_index * 50}" y="20">{location_name}</name>
    </location>\n'''
    full_text_file += location_text

    location_index += 1


full_text_file += f'\t<init ref="{location_dict[initial_location]}"/>\n'
full_text_file += "</template>"    
full_text_file += f"<system>{ta_name}</system>\n"

full_text_file += "</nta>"

outfile.write(full_text_file)

outfile.close()

