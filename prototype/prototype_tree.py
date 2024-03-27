import os
from itertools import chain

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

text = open(os.path.join(dirname, "BDD_full.txt"), "r")
ast = parse(text.read())
text.close

location_x_offset = 100

variable_names = []
channels = []


class Entity:
    def __init__(self, name, states, actions, properties):
        self.name = name
        self.states = states
        self.actions = actions
        self.properties = properties

    def __str__(self):
        return f"Name: {self.name}\nStates: {self.states}\nActions: {self.actions}\nProperties: {self.properties}"


class Transition:
    def __init__(self, source: "Location", target: "Location", action: str, label: str, kind: str):
        self.source = source
        self.target = target
        self.action = action
        self.label = label
        self.kind = kind

    def __str__(self):
        return f"Source: {self.source}\nTarget: {self.target}\nLabel: {self.label}"
    
    def __repr__(self):
        return f"({self.source.name} -> {self.target.name} : {self.label})"
    
    def __eq__(self, __value: object) -> bool:
        return self.source == __value.source and self.target == __value.target and self.action == __value.action and self.label == __value.label and self.kind == __value.kind


class Location:

    def __init__(self, name: str, id: str, transitions: list["Transition"], init: bool=False, pos_x: int=0, pos_y: int=0):
        self.name = name
        self.id = id
        self.init = init
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.transitions = transitions
        self.committed = False

    def __str__(self):
        return f"({self.name}, {self.transitions})"
    
    def __repr__(self):
        return f"{self.name}{'(init)' if self.init else ''}"
    
    def __eq__(self, __value: object) -> bool:
        if(__value is None):
            return False
        return self.name == __value.name
    
    def set_committed(self, committed: bool):
        self.committed = committed

def find_child(tree: Tree, type: str):
    for child in tree.children:
        if isinstance(child, Token) and child.type == type:
            return child
    return None

entities = []
main_entity = None
entity_names = []
synchronizations = []
location_index = -1
all_locations = []


def generateId():
    global location_index
    location_index += 1
    return "id" + location_index.__str__()

# Collect all entities
for entity in ast.find_data("entity"):
    entity_name = entity.children[0].lstrip(" ").rstrip("\n")
    entity_names.append(entity_name)
    states = []
    actions = []
    properties = []

    for state in entity.find_data("states"):
        states = list(map(lambda s: s.value, state.children ))
    single_state = find_child(entity, "STATE_NAME")
    if(single_state and single_state not in states):
        states.append(single_state.value)

    for action in entity.find_data("actions"):
        actions = list(map(lambda a: a.value, action.children ))
    single_action = find_child(entity, "ACTION_NAME")
    if(single_action and single_action not in actions):
        actions.append(single_action.value)

    for property in entity.find_data("properties"):
        properties = list(map(lambda p: p.value, property.children ))
    single_property = find_child(entity, "PROPERTY_NAME")
    if(single_property and single_property not in properties):
        properties.append(single_property.value)

    entities.append(Entity(entity_name, states, actions, properties))

main_entity = entities[0]
# go through ast. if any tokens of type "ENTITY_NAME" has a value that is not in entity_names, then change the type to "PROPERTY_NAME"
for tree in ast.iter_subtrees():
    for token in tree.children:
        if not isinstance(token, Token):
            continue
        if token.type == "ENTITY_NAME" and token.value not in entity_names:
            token.type = "PROPERTY_NAME"
            continue

# Rule 1: The <domain model name> is converted into the name of the NTA, which consists of a set of TAs.
model_name = next(ast.find_data("model")).children[0].lstrip(" ").rstrip("\n")

#Rule 2 The <entity name> of the first entity (main entity) is implemented as the name of the TA.
ta_name = next(ast.find_data("entity")).children[0].lstrip(" ").rstrip("\n")



scenarios = ast.find_data("scenario")
first_scenario = next(ast.find_data("scenario"))

# new Rule 3: The first <state name> in the list of states, of the first entity, is mapped to the initial location of the TA




def create_channel_name(action):
    channel_name = ""
    name = filter(lambda c: c.type == "ACTION_NAME", action.children)
    action_mode = filter(lambda c: c.type == "ACTION_MODE", action.children)
    try:
        channel_name += "no_"  if next(action_mode).value == "I do not" else ""
    except StopIteration:
        pass
    try:
        channel_name += next(name).value
    except StopIteration:
        pass
    action_values = filter(lambda c: isinstance(c, Token) and c.type == "ACTION_VALUE", action.children)
    try:
        channel_name += f'_{next(action_values).value}'
    except StopIteration:
        pass
    for entity in action.find_data("entity_property"):
        property_instances = filter(lambda c: c.type == "PROPERTY_INSTANCE", entity.children)
        try:
            channel_name += f'_{next(property_instances).value}'
        except StopIteration:
            pass
        entity_instances = filter(lambda c: c.type == "ENTITY_INSTANCE", entity.children)
        try:
            channel_name += f'_{next(entity_instances).value}'
        except StopIteration:
            pass

    return channel_name

def commit_action(current: Location, action: Tree):
    action_name = find_child(action, "ACTION_NAME").value
    if(not action_name):
        return None
    channel_name = create_channel_name(action)
    channels.append(channel_name)
    if(action.data == "concurrent_action"):
        current.set_committed(True)
    for transition in current.transitions:
        if transition.action == channel_name:
            return transition.target
    return None


def create_transition(source: Location, target: Location, action: str, label: str, kind: str):
    transition = Transition(source, target, action, label, kind)
    if(transition in source.transitions):
        return
    source.transitions.append(transition)
    return transition

def create_location(name: str, id: str, init: bool, pos_x: int, pos_y: int):
    location = Location(name, id, [], init, pos_x, pos_y)
    if(location in all_locations):
        return
    all_locations.append(location)
    return location

def get_location(name: str):
    for location in all_locations:
        if location.name == name:
            return location
    return None

initial_location = create_location(main_entity.states[0], generateId(), True, 0 * location_x_offset, 0)

for entity in entities:
    # print(entity)
    for state in entity.states:
        create_location(state, generateId(), False, 0, 0)


for scenario in scenarios:
    current_location = None
    for given in scenario.find_data("given"):
        entity = given.children[0]
        source = find_child(given, "STATE_NAME")
        if(not source):
            continue
        current_location = get_location(source.value)
    if(current_location):
        for _action in chain(scenario.find_data("action"), scenario.find_data("concurrent_action")):
            action = create_channel_name(_action)
            next_location = commit_action(current_location, _action)
            if(not next_location):
                target = None
                for then_clause in scenario.find_data("then"):
                    target_name = find_child(then_clause, "STATE_NAME")
                    if(target_name):
                        target = get_location(target_name.value)
                        if(not target):
                            print("!!!",target_name.value)
                create_transition(current_location, target, action, action + "?", "synchronisation")
                current_location = target
            else:
                current_location = next_location
                

print(all_locations[0])

for channel in channels:
        globalDeclarations += f"chan {channel};\n"

globalDeclarationFinal = declarationStart + globalDeclarations + declarationEnd
full_text_file += globalDeclarationFinal

explored_locations = []

template_text = "<template>\n"
template_text += "\t<name>" + ta_name + "</name>\n"
init_text = ""


def print_transitions_to_file(transition: Transition):
    global template_text
    template_text += f'\t<transition><source ref="{transition.source.id}"/><target ref="{transition.target.id}"/><label kind="{transition.kind}" x="0" y="0">{transition.label}</label></transition>\n'


def print_location_to_file(location: Location):
    global init_text, template_text
    if(location in explored_locations):
        return
    explored_locations.append(location)
    location_text = f'''\t<location id="{location.id}" x="{location.pos_x}" y="{location.pos_y}"> 
        <name x="{location.pos_x}" y="{location.pos_y + 20}">{location.name}</name>
        {f'<committed/>' if location.committed else ''}
    </location>\n'''
    template_text += location_text
    if(location.init):
        init_text = f'\t<init ref="{location.id}"/>\n'
    
    for transition in location.transitions:
        print_location_to_file(transition.target)
        print_transitions_to_file(transition)

print_location_to_file(all_locations[0])

template_text += init_text

template_text += "</template>\n" 
full_text_file += template_text   

full_text_file += f"<system>\nsystem {ta_name}, user;\n</system>\n"

full_text_file += "</nta>"

outfile.write(full_text_file)

outfile.close()
