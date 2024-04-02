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

location_x_offset = 200
positive_transition_index = 1
negative_transition_index = 1

variable_names = []
channels = []
label_positions = []
nail_positions = []

class Position:

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __repr__(self):
        return f"({self.x}, {self.y})"

    def __eq__(self, __value: object) -> bool:
        return self.x == __value.x and self.y == __value.y


class Nails:
    def __init__(self, nail1: Position, nail2: Position):
        self.nail1 = nail1
        self.nail2 = nail2
    
    def __str__(self):
        return f"{self.nail1}, {self.nail2}"
    
    def __repr__(self):
        return f"{self.nail1}, {self.nail2}"
    
    # Note: only one of the nails needs to overlap in order to be considered equal
    def __eq__(self, __value: object) -> bool:
        return self.nail1 == __value.nail1 or self.nail2 == __value.nail2

class Entity:
    def __init__(self, name, states, actions, properties):
        self.name = name
        self.states = states
        self.actions = actions
        self.properties = properties

    def __str__(self):
        return f"Name: {self.name}\nStates: {self.states}\nActions: {self.actions}\nProperties: {self.properties}"


class Transition:
    def __init__(self, source: "Location", target: "Location", action: str, labels: list["Label"]):
        self.source = source
        self.target = target
        self.action = action
        self.labels = labels

    def add_label(self, label: "Label"):
        if(label in self.labels):
            return
        self.labels.append(label)

    def __str__(self):
        return f"\nSource: {self.source}\nTarget: {self.target}\nAction: {self.action}\nLabels: {self.labels}\n"
    
    def __repr__(self):
        return f"({self.source.name} -> {self.target.name} : {self.action})"
    
    def __eq__(self, __value: object) -> bool:
        return self.source == __value.source and self.target == __value.target and self.action == __value.action

class Label:
    def __init__(self, kind: str, text: str):
        self.kind = kind
        self.text = text
        self.position = Position(0, 0)

    def __str__(self):
        return f"Kind: {self.kind}\nText: {self.text}"

    def __repr__(self):
        return f"{self.text}"

    def __eq__(self, __value: object) -> bool:
        return self.text == __value.text and self.kind == __value.kind

class Location:

    def __init__(self, name: str, id: str, transitions: list["Transition"], init: bool=False, pos_x: int=0, pos_y: int=0):
        self.name = name
        self.id = id
        self.init = init
        self.position = Position(pos_x, pos_y)
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

def find_first_data(tree: Tree, data: str):
    for child in tree.children:
        if isinstance(child, Tree) and child.data == data:
            return child
    return None

entities = []
main_entity = None
entity_names = []
synchronizations = []
location_index = -1
invariant_index = -1
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

    for action_name in entity.find_data("actions"):
        actions = list(map(lambda a: a.value, action_name.children ))
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

# returns a tuple (action mode, time variable, value)
def get_action_constraint(action: Tree):
    action_mode = find_child(action, "ACTION_MODE")
    constraint = find_first_data(action, "within_time")
    if(constraint):
        value = find_child(constraint, "TIME_VARIABLE_VALUE")
        time_variable = find_child(constraint, "TIME_VARIABLE")
        return (action_mode.value, time_variable.value if time_variable else "", value.value if value else "")
    return None

def constraint_to_string(constraint: tuple):
    return f'x  &lt;= {constraint[2] * ( 60 if constraint[1] == "minutes" else 3600 if constraint[1] == "hours" else 1)}'


def create_channel_name(action: Tree):
    channel_name = ""
    name = filter(lambda c: c.type == "ACTION_NAME", action.children)
    action_mode = filter(lambda c: c.type == "ACTION_MODE", action.children)
    if(get_action_constraint(action)):
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



    

def create_transition(source: Location, target: Location, action: str, label: Label):
    transition = Transition(source, target, action, [])

    # Check if transition already exists, add label if it does
    for t in source.transitions:
        if t == transition:
            t.add_label(label)
            return t

    transition.add_label(label)
    source.transitions.append(transition)
    return transition

def create_location(name: str, init: bool, pos_x: int, pos_y: int):
    location = Location(name, generateId(), [], init, pos_x, pos_y)
    if(location in all_locations):
        return
    all_locations.append(location)
    return location

def get_location(name: str):
    for location in all_locations:
        if location.name == name:
            return location
    return None

def create_entity_type(entity: Entity):
    global globalDeclarations
    variable_string = 'struct {\n'
    for state in entity.states:
        variable_string += f'\t{"bool"} {state};\n'
    for property in entity.properties:
        variable_string += f'\t{"int"} {property};\n'
    variable_string += f'{"}"} {entity.name};\n'
    globalDeclarations += variable_string

def get_state_guard_boolean(token: Token):
    if(token.type == "STATE_GUARD"):
        return "true" if token.value == "is" else "true" if token.value == "are" else "false"
    return None

# new Rule 3: The first <state name> in the list of states, of the first entity, is mapped to the initial location of the TA
initial_location = create_location(main_entity.states[0],  True, 0 * location_x_offset, 0)

# Create locations for all states in the main entity
for state in entities[0].states:
    create_location(state,  False, location_index * location_x_offset, 0)

# Create all other entities as structs
for i in range(1, len(entities)):
    create_entity_type(entities[i])


def guard_to_operator(guard: str):
    return "==" if guard == "equal to" else "&gt;" if guard == "greater than" else "&lt;"

for scenario in scenarios:
    current_location = None
    labels = []
    for given in scenario.find_data("given"):
        print(given)
        given_entity = ""
        property_name = ""
        guard = ""
        for child in given.children:
            if(isinstance(child, Token)):
                if(child.type == "GUARD"):
                    guard = guard_to_operator(child.value)
            if(isinstance(child, Tree)):
                entity_name = find_child(child, "ENTITY_NAME")
                if(entity_name):
                    given_entity = entity_name.value
                _property_name = find_child(child, "PROPERTY_NAME")
                if(_property_name):
                    property_name = _property_name.value
            elif(given_entity):
                if(child.type == "PROPERTY_VALUE"):
                    labels.append(Label("guard", f'{(given_entity + ".") if given_entity != main_entity.name else ""}{property_name} {guard} {child.value}'))

        entity = given.children[0]
        source = find_child(given, "STATE_NAME")
        if(not source):
            continue
        current_location = get_location(source.value)
    if(current_location):
        for action in chain(scenario.find_data("action"), scenario.find_data("concurrent_action")):
            action_name = create_channel_name(action)
            next_location = commit_action(current_location, action)


            if(not next_location):
                target = next_location
                # labels = [] 
                # constraint = get_action_constraint(action)
                # if(constraint):
                #     labels.append(Label("guard", constraint_to_string(constraint)))
                for then_clause in scenario.find_data("then"):
                    then_entity = ""
                    then_property = ""
                    last_guard = "true"
                    for child in then_clause.children:
                        if(isinstance(child, Tree)):
                            entity_name = find_child(child, "ENTITY_NAME")
                            if(entity_name):
                                then_entity = entity_name.value
                            property_name = find_child(child, "PROPERTY_NAME")
                            if(property_name):
                                then_property = property_name.value
                        else:
                            if(then_entity == main_entity.name):
                                if(child.type == "STATE_NAME"):
                                    target = get_location(child.value)
                                    # TODO: add ! sync to user template
                                    labels.append(Label("synchronisation", action_name + "?"))
                                    if(not target):
                                        print("!!!",child.value)
                            else:
                                if(child.type == "STATE_GUARD"):
                                    last_guard = get_state_guard_boolean(child)
                                print(child.type, child.value)
                                # TODO: update entity struct
                                if(child.type == "STATE_NAME"):
                                    labels.append(Label("assignment", f'{then_entity}.{child.value} := {last_guard}'))
                                elif(child.type == "PROPERTY_VALUE"):
                                    labels.append(Label("assignment", f'{then_entity}.{then_property} := {child.value}'))
                    
                for label in labels:
                    create_transition(current_location, target, action_name, label)
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
locations_text = ""
transitions_text = ""
init_text = ""


def target_is_left_of_source(source: Location, target: Location):
    return target.position.x < source.position.x


def get_transition_nails(transition: Transition):
    global nail_positions

    if(target_is_left_of_source(transition.source, transition.target)):
        position = Nails(
            Position(transition.source.position.x - 10,  50),
            Position(transition.target.position.x + 10,  50)
        )
        while (position in nail_positions):
            position.nail1.y += 50
            position.nail2.y += 50
        nail_positions.append(position)
        return position
    

    position = Nails(
        Position(transition.source.position.x + 10, -  50),
        Position(transition.target.position.x - 10, -  50)
    )
    while (position in nail_positions):
        position.nail1.y -= 50
        position.nail2.y -= 50
    nail_positions.append(position)
    return position
    
def calculate_label_position(transition: Transition, nails: Nails):
    global positive_transition_index, label_positions
    increment =  15 if target_is_left_of_source(transition.source, transition.target) else - 15
    base = 0 if target_is_left_of_source(transition.source, transition.target) else 20

    source_x = nails.nail1.x
    target_x = nails.nail2.x
    source_y = nails.nail1.y
    base_x = source_x + ((target_x-source_x) / 2)
    base_y = source_y - base
    position = Position(int(base_x), int(base_y))
    while position in label_positions:
        print(position.y, increment, position.y + increment)
        position.y += increment
    label_positions.append(position)
    return position

def print_transitions_to_file(transition: Transition):
    global transitions_text, positive_transition_index
    transitions_text += f'\t<transition><source ref="{transition.source.id}"/><target ref="{transition.target.id}"/>\n'
    nails = get_transition_nails(transition)

    for label in transition.labels:
        position = calculate_label_position(transition, nails)
        transitions_text += f'\t<label kind="{label.kind}" x="{position.x}" y="{position.y}">{label.text}</label>\n'

    transitions_text += f'\t<nail x="{nails.nail1.x}" y="{nails.nail1.y}"/>\n'
    transitions_text += f'\t<nail x="{nails.nail2.x}" y="{nails.nail2.y}"/>\n'

    # if(positive_transition_index > 0):
    #     transitions_text += f'\t<nail x="{(transition.source.position.x- 10 if target_is_left_of_source(transition.source, transition.target) else transition.source.position.x+ 10)}" y="{-(positive_transition_index * 50)}"/>\n'
    #     transitions_text += f'\t<nail x="{(transition.target.position.x+ 10 if target_is_left_of_source(transition.source, transition.target) else transition.target.position.x- 10)}" y="{-(positive_transition_index * 50)}"/>\n'
    transitions_text += "</transition>\n"
 


def print_location_to_file(location: Location):
    global init_text, locations_text
    if(location in explored_locations):
        return
    explored_locations.append(location)
    location_text = f'''\t<location id="{location.id}" x="{location.position.x}" y="{location.position.y}"> 
        <name x="{location.position.x + 20}" y="{location.position.y }">{location.name}</name>
        {f'<committed/>' if location.committed else ''}
    </location>\n'''
    locations_text += location_text
    if(location.init):
        init_text = f'\t<init ref="{location.id}"/>\n'
    
    for transition in location.transitions:
        print_location_to_file(transition.target)
        print_transitions_to_file(transition)

print_location_to_file(all_locations[0])

template_text += locations_text

template_text += init_text

template_text += transitions_text

template_text += "</template>\n" 
full_text_file += template_text   

full_text_file += f"<system>\nsystem {ta_name}, user;\n</system>\n"

full_text_file += "</nta>"

outfile.write(full_text_file)

outfile.close()
