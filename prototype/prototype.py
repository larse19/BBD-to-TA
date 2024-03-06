import os

from bddProcessor import parse
from lark import Token

dirname = os.path.dirname(__file__)


startString = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' 'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>
<nta>'''

full_text_file = startString

outfile = open(os.path.join(dirname, "prototype.xml"), "w")


declarationStart = '<declaration>'
declarationEnd = '</declaration>'
globalDeclarations = ""

text = open(os.path.join(dirname, "BDD.text"), "r")
ast = parse(text.read())
text.close

# Rule 1: The <domain model name> is converted into the name of the NTA, which consists of a set of TAs.
# for test in ast.find_data("model"):
#     for child in test.children:
#         print(child)
#         print("\n")
model_name = next(ast.find_data("model")).children[0].lstrip(" ").rstrip("\n")


location_names = []

#Rule 2 The <entity name> of the first entity (main entity) is implemented as the name of the TA.
ta_name = next(ast.find_data("entity")).children[0].lstrip(" ").rstrip("\n")

#Rule 3 The <state name> that appears in the Given clause of the first scenario is mapped to initial location of the TA.
first_scenario = next(ast.find_data("scenario"))
given_clause = next(first_scenario.find_data("given")).children[0]
initial_location = ""
for child in given_clause.children:
    if isinstance(child, Token):
        if(child.type == "STATE_NAME"):
            initial_location = child.value
            location_names.append(child.value)
            break

#R4 The <state name> placed after is or is in is modeled as location name in the TA.
for then_clause in first_scenario.find_data("then"):
    for entity_property in then_clause.children:
        for child in entity_property.children:
            if isinstance(child, Token):
                if(child.type == "STATE_NAME" and child.value not in location_names):
                    location_names.append(child.value)
                    break

#R5 Whenever properties are mentioned in the scenarios, the <property name> becomes a variable of any type in the TA




globalDeclarationFinal = declarationStart + globalDeclarations + declarationEnd
full_text_file += globalDeclarationFinal
full_text_file += "<template>"
full_text_file += "<name>" + ta_name + "</name>"


location_dict = {}
location_index = 0
for location_name in location_names:
    id = "id" + location_index.__str__()
    location_dict[location_name] = id
    location_text = f'''<location id="{id}" x="{location_index * 50}" y="0"> 
        <name x="{location_index * 50}" y="20">{location_name}</name>
    </location>'''
    full_text_file += location_text

    location_index += 1


full_text_file += f'<init ref="{location_dict[initial_location]}"/>'
full_text_file += "</template>"    
full_text_file += f"<system>{ta_name}</system>"

full_text_file += "</nta>"

outfile.write(full_text_file)

outfile.close()

