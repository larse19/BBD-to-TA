import os

from lark import Token, Tree

from bddProcessor import parse

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
text.close()



location_x_offset = 100

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
    
    def __repr__(self):
        return f"{self.name}"

class Transition:
    def __init__(self, source: Location, target: Location, label: str, kind: str):
        self.source = source
        self.target = target
        self.label = label
        self.kind = kind

    def __str__(self):
        return f"Source: {self.source}\nTarget: {self.target}\nLabel: {self.label}"
    
    def __repr__(self):
        return f"({self.source} -> {self.target} : {self.label})"

class Template:
    def __init__(self, name: str, locations: list[Location], transitions: list[Transition], channels: list[str] = []):
        self.name = name
        self.locations = locations
        self.transitions = transitions
        self.channels = channels

    def get_location(self, name: str):
        for location in self.locations:
            if location.name == name:
                return location
        location = Location(name, generateId(), False, self.locations.__len__() * location_x_offset, 0)
        self.add_location(location)
        return location
    
    def get_location_names(self):
        return list(map(lambda l: l.name, self.locations))
    
    def add_location(self, location: Location):
        self.locations.append(location)

    def add_transition(self, transition: Transition):
        if transition.source not in self.locations:
            self.add_location(transition.source)
        if transition.target not in self.locations:
            self.add_location(transition.target)
        self.transitions.append(transition)

    def add_channel(self, channel: str):
        if(not channel in self.channels):
            self.channels.append(channel)

    def __str__(self):
        return f'Name: {self.name}\nLocations: {self.locations}\nTransitions: {self.transitions}"'
#Rule 2 The <entity name> of the first entity (main entity) is implemented as the name of the TA.
ta_name = next(ast.find_data("entity")).children[0].lstrip(" ").rstrip("\n")

main_template = Template(ta_name, [], [])
user_template = Template("user", [], [])
templates = [main_template, user_template]
entities = []
main_entity = None
entity_names = []
synchronizations = []
location_index = -1

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
# channels = ""
# for entity in entities:
#     for action in entity.actions:
#         globalDeclarations += "chan " + action + ";\n"

# Rule 1: The <domain model name> is converted into the name of the NTA, which consists of a set of TAs.
# for test in ast.find_data("model"):
#     for child in test.children:

model_name = next(ast.find_data("model")).children[0].lstrip(" ").rstrip("\n")


scenarios = ast.find_data("scenario")

first_scenario = next(ast.find_data("scenario"))

# # old Rule 3 The <state name> that appears in the Given clause of the first scenario is mapped to initial location of the TA.
# given_clause = next(first_scenario.find_data("given"))
# initial_location = ""
# for child in given_clause.children:
#     if isinstance(child, Token):
#         if(child.type == "STATE_NAME"):
#             initial_location = child.value
#             main_template.add_location(Location(initial_location, generateId(), True, len(main_template.locations) * location_x_offset, 0))
#             user_template.add_location(Location(initial_location, generateId(), True, len(user_template.locations) * location_x_offset, 0))

#             # location_names.append(child.value)
#             break

# new Rule 3: The first <state name> in the list of states, of the first entity, is mapped to the initial location of the TA
initial_location = main_entity.states[0]
main_template.add_location(Location(initial_location, generateId(), True, len(main_template.locations) * location_x_offset, 0))
user_template.add_location(Location(initial_location, generateId(), True, len(user_template.locations) * location_x_offset, 0))

# From here on out, all the rules are 
# implemented in on each scenario
for scenario in scenarios:

    #R4 The <state name> placed after is or is in is modeled as location name in the TA.
    for then_clause in scenario.find_data("then"):
        for state_name in then_clause.children:
            if isinstance(state_name, Token):
                if(state_name.type == "STATE_NAME" and state_name.value in main_entity.states and state_name.value not in main_template.get_location_names()):
                    main_template.add_location(Location(state_name.value, generateId(),False, len(main_template.locations) * location_x_offset, 0))
                    user_template.add_location(Location(state_name.value, generateId(),False, len(main_template.locations) * location_x_offset, 0))
                    break

    #R5 Whenever properties are mentioned in the scenarios, the <property name> becomes a variable of any type in the TA
    for entity in entities:
        for property in entity.properties:
            if property not in variable_names:
                variable_names.append(property)
                # Assume int for now
                globalDeclarations += f"int {property};\n"
                
    #R6 The <property instance> affected by actions is mapped to synchronization action in the TA.
    # Whenever an action is made, a channel is created with the naming structure of <action name>_(<property instance>_[entity instance])/<action value>/<entity instance>
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

    for action in scenario.find_data("action"):
        main_template.add_channel(create_channel_name(action))

    for concurrent_action in scenario.find_data("concurrent_action"):
        main_template.add_channel(create_channel_name(concurrent_action))

    
    # new rule. The <state name> mentioned in the given clause is mapped to the source of a transition, and the state name mentioned after the same entity in the then clause is mapped to the target of the transition.
    entity_name = ""
    source = ""
    target = ""
    action = ""
    for given in scenario.find_data("given"):
        entity = given.children[0]
        try:
            entity_name = next(filter(lambda c: isinstance(c, Token) and c.type == "ENTITY_NAME", entity.children)).value
        except StopIteration:
            break
        try:
            source = next(filter(lambda c: isinstance(c, Token) and c.type == "STATE_NAME", given.children)).value
            # for now, just consider the first entity
            break
        except StopIteration:
            break

    for then_clause in scenario.find_data("then"):
        _entity_name = ""
        for child in then_clause.children:
            if(isinstance(child, Tree)):
                _entity_name = child.children[0].value
            else:
                try:
                    if(entity_name == _entity_name):
                        try:
                            target = next(filter(lambda c: isinstance(c, Token) and c.type == "STATE_NAME", then_clause.children)).value
                            break
                        except StopIteration:
                            break
                except StopIteration:
                    break

    for _action in scenario.find_data("action"):
        action = create_channel_name(_action)
    

    for template in templates:
        if template.name == entity_name:
            template.add_transition(Transition(template.get_location(source), template.get_location(target), action + "?", "synchronisation"))
    
    #R7 States from secondary entities are implemented as a synchronization action of the TA.
    for action in scenario.find_data("action"):
        # get source
        given_clause = next(first_scenario.find_data("given"))
        source = ""
        action_name = ""

        for child in given_clause.children:
            if isinstance(child, Token):
                if(child.type == "STATE_NAME"):
                    source = child.value
                    break

        # get action (syncronization)
        # action_names = [child for child in action.children if (isinstance(child, Token) and child.type == "ACTION_NAME")]    
        # for action_name in action_names:
        for target in scenario.find_data("then"):
            for state_name in target.children:
                if isinstance(action, Token) and action.type == "ACTION_NAME":
                    action_name = action.value
                    if(state_name.type == "STATE_NAME" and state_name.value in main_entity.states):
                        main_template.add_transition(Transition(main_template.get_location(source), main_template.get_location(state_name.value), action.value + "?", "synchronisation"))
                        user_template.add_transition(Transition(user_template.get_location(source), user_template.get_location(state_name.value), action.value + "!", "synchronisation"))
                if isinstance(action, Token) and action.type == "ACTION_VALUE":
                    if(state_name.type == "STATE_NAME" and state_name.value in main_entity.states):
                        main_template.add_transition(Transition(main_template.get_location(source), main_template.get_location(state_name.value), f'{action_name}_value:={action.value}', "synchronisation"))
                        user_template.add_transition(Transition(user_template.get_location(source), user_template.get_location(state_name.value), f'{action_name}_value:={action.value}', "synchronisation"))
                            
# Add channels to global declarations
for channel in main_template.channels:
        globalDeclarations += f"chan {channel};\n"

globalDeclarationFinal = declarationStart + globalDeclarations + declarationEnd
full_text_file += globalDeclarationFinal

for template in templates:
    template_text = "<template>\n"
    template_text += "\t<name>" + template.name + "</name>\n"
    init_text = ""

    for location in template.locations:
        location_text = f'''\t<location id="{location.id}" x="{location.pos_x}" y="{location.pos_y}"> 
            <name x="{location.pos_x}" y="{location.pos_y + 20}">{location.name}</name>
        </location>\n'''
        template_text += location_text
        if(location.init):
            init_text = f'\t<init ref="{location.id}"/>\n'
    
    template_text += init_text

    for transition in template.transitions:
        template_text += f'\t<transition><source ref="{transition.source.id}"/><target ref="{transition.target.id}"/><label kind="{transition.kind}" x="0" y="0">{transition.label}</label></transition>\n'

    template_text += "</template>\n" 
    full_text_file += template_text   

full_text_file += f"<system>\nsystem {main_template.name}, user;\n</system>\n"

full_text_file += "</nta>"

outfile.write(full_text_file)

outfile.close()

