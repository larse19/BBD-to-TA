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
globalDeclarations = "clock x;\n"

text = open(os.path.join(dirname, "BDD.txt"), "r")
ast = parse(text.read())
text.close

variable_names = []


class Entity:
    def __init__(self, name, states, actions, properties):
        self.name = name
        self.states = states
        self.actions = actions
        self.properties = properties

    def __str__(self):
        return f"Name: {self.name}\nStates: {self.states}\nActions: {self.actions}\nProperties: {self.properties}"

class Location:
    def __init__(self, name: str, id: str, init: bool=False, pos_x: int=0, pos_y: int=0):
        self.name = name
        self.id = id
        self.init = init
        self.pos_x = pos_x
        self.pos_y = pos_y

    def __str__(self):
        return f"Name: {self.name}"

class Transition:
    def __init__(self, source: Location, target: Location, label: str):
        self.source = source
        self.target = target
        self.label = label

    def __str__(self):
        return f"Source: {self.source}\nTarget: {self.target}\nLabel: {self.label}"

class Template:
    def __init__(self, name: str, locations: list[Location]=[], transitions: list[Transition]=[]):
        self.name = name
        self.locations = locations
        self.transitions = transitions

    def get_location(self, name: str):
        for location in self.locations:
            if location.name == name:
                return location
        return None
    
    def get_location_names(self):
        return list(map(lambda l: l.name, self.locations))
    
    def add_location(self, location: Location):
        self.locations.append(location)

    def add_transition(self, transition: Transition):
        self.transitions.append(transition)

    def __str__(self):
        return f'Name: {self.name}\nLocations: {self.locations}\nTransitions: {self.transitions}\n{"Init: {self.init}" if self.init else ""}"'
#Rule 2 The <entity name> of the first entity (main entity) is implemented as the name of the TA.
ta_name = next(ast.find_data("entity")).children[0].lstrip(" ").rstrip("\n")

main_template = Template(ta_name)
user_template = Template("user")
templates = [main_template, user_template]
entities = []
main_entity = None
entity_names = []
synchronizations = []
location_index = 0

def generateId(index: int):
    return "id" + index.__str__()

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

main_entity = entities[0]
# go through ast. if any tokens of type "ENTITY_NAME" has a value that is not in entity_names, then change the type to "PROPERTY_NAME"
for tree in ast.iter_subtrees():
    for token in tree.children:
        if not isinstance(token, Token):
            continue
        # if token.type == "ENTITY_NAME" and (token.value not in entity_names or token.value in main_entity.properties):
        #     token.type = "PROPERTY_NAME"
        #     continue
        if token.type == "ENTITY_NAME" and token.value not in entity_names:
            token.type = "PROPERTY_NAME"
            continue


# create a chanel for each action
channels = ""
for entity in entities:
    for action in entity.actions:
        channels += f" {action},"

globalDeclarations += "chan" + channels.rstrip(",") + ";\n"
# Rule 1: The <domain model name> is converted into the name of the NTA, which consists of a set of TAs.
# for test in ast.find_data("model"):
#     for child in test.children:
#         print(child)
#         print("\n")
model_name = next(ast.find_data("model")).children[0].lstrip(" ").rstrip("\n")


scenarios = ast.find_data("scenario")

#Rule 3 The <state name> that appears in the Given clause of the first scenario is mapped to initial location of the TA.
first_scenario = next(ast.find_data("scenario"))
given_clause = next(first_scenario.find_data("given"))
initial_location = ""

for child in given_clause.children:
    if isinstance(child, Token):
        if(child.type == "STATE_NAME"):
            initial_location = child.value
            main_template.add_location(Location(initial_location, generateId(location_index), True, location_index * 50, 0))
            location_index += 1
            # location_names.append(child.value)
            break

# From here on out, all the rules are implemented in on each scenario
for scenario in scenarios:

    #R4 The <state name> placed after is or is in is modeled as location name in the TA.
    for then_clause in scenario.find_data("then"):
        for state_name in then_clause.children:
            if isinstance(state_name, Token):
                if(state_name.type == "STATE_NAME" and state_name.value in main_entity.states and state_name.value not in main_template.get_location_names()):
                    main_template.add_location(Location(state_name.value, generateId(location_index),False, location_index * 50, 0))
                    location_index += 1
                    break

    #R5 Whenever properties are mentioned in the scenarios, the <property name> becomes a variable of any type in the TA
    for entity in entities:
        for property in entity.properties:
            if property not in variable_names:
                variable_names.append(property)
                # Assume string for now
                globalDeclarations += f"string {property};\n"
                
    #R6 The <property instance> affected by actions is mapped to synchronization action in the TA.
    
    
    
    #R7 States from secondary entities are implemented as a synchronization action of the TA.
    for action in scenario.find_data("action"):
        # get source
        given_clause = next(first_scenario.find_data("given"))
        source = ""

        for child in given_clause.children:
            if isinstance(child, Token):
                if(child.type == "STATE_NAME"):
                    source = child.value
                    break

        # get action (syncronization)
        action_names = [child for child in action.children if (isinstance(child, Token) and child.type == "ACTION_NAME")]    
        for action_name in action_names:
            for target in scenario.find_data("then"):
                for state_name in target.children:
                    if isinstance(state_name, Token):
                        if(state_name.type == "STATE_NAME" and state_name.value in main_entity.states):
                            main_template.add_transition(Transition(main_template.get_location(source), main_template.get_location(state_name.value), action_name.value + "?"))
                            


globalDeclarationFinal = declarationStart + globalDeclarations + declarationEnd
full_text_file += globalDeclarationFinal

for template in templates:
    template_text = "<template>\n"
    template_text += "\t<name>" + template.name + "</name>\n"

    for location in template.locations:
        location_text = f'''\t<location id="{id}" x="{location.pos_x}" y="{location.pos_y}"> 
            <name x="{location.pos_x}" y="{location.pos_y + 20}">{location.name}</name>
        </location>\n'''
        template_text += location_text

    synchronization_index = 0
    for sync in template.transitions:
        id = "id" + synchronization_index.__str__()
        template_text += f'\t<transition id="{id}"><source ref="{sync.source.id}"/><target ref="{sync.target.id}"/><label kind="synchronisation" x="0" y="0">{sync.label}</label></transition>\n'
        synchronization_index += 1

    for location in template.locations:
        if(location.init):
            template_text += f'\t<init ref="{location.id}"/>\n'
    template_text += "</template>" 
    full_text_file += template_text   

full_text_file += f"<system>{ta_name}, user</system>\n"

full_text_file += "</nta>"

outfile.write(full_text_file)

outfile.close()

