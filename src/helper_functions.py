import json

from lark import Token, Tree

from classes import Label, Location, Transition


def get_state_guard_boolean(token: Token):
    if(token.type == "STATE_GUARD"):
        return "true" if token.value == "is" else "true" if token.value == "are" else "false"
    return None


def create_transition(source: Location, target: Location, action: str, label: Label |None):
    transition = Transition(source, target, action, [])

    # Check if transition already exists, add label if it does
    for t in source.transitions:
        if t == transition:
            if(label):
                if(label. kind == "guard" and label in t.labels):
                    break
                t.add_label(label)
            return t
    if(label):
        transition.add_label(label)
    source.transitions.append(transition)
    return transition

location_offset = 200
inv_index = 0

def create_location(name: str, init: bool, pos_x: int, pos_y: int, all_locations: list[Location], invariant=None):
    global inv_index
    location = Location(name, generateId(len(all_locations)), [], init, pos_x, pos_y)
    location.invariant = invariant

    for loc in all_locations:
        if loc == location:
            return loc
    if(location.name == "inv"):
        location.name = "inv" + str(inv_index)
        inv_index += 1
    location.position.x = len(all_locations) * location_offset
    all_locations.append(location)
    return location

def get_location(name: str, all_locations: list[Location]):
    for location in all_locations:
        if location.name == name:
            return location
    return None

def add_variable(variables: list[str], variable: str):
    if variable not in [x.split("=")[0] for x in variables]:
        variables.append(variable)

def add_label(labels: list[Label], newLabel: Label):
    for l in labels:
        if l == newLabel:
            for text in newLabel.text:
                l.add_text(text)
    labels.append(newLabel)
            


def commit_action(current: Location, action: Tree, channels: list[str], guard_labels: list[Label]) -> Transition | None:
    action_name = find_child(action, "ACTION_NAME").value

    if(not action_name):
        return None
    
    channel_name = create_channel_name(action)

    if(channel_name not in channels):
        channels.append(channel_name)

    if(action.data == "concurrent_action"):
        current.set_committed(True)

    for transition in current.transitions:
        if transition.action == channel_name:
            if(any(l.kind == "guard" for l in transition.labels)):
                if(set(guard_labels).issubset(set(transition.labels))):
                    return transition
            return transition
        
    return None


# returns a tuple (action mode, time variable, value)
def get_action_constraint(action: Tree):
    action_mode = find_child(action, "ACTION_MODE")
    constraint = find_first_data(action, "within_time")
    if(constraint):
        value = find_child(constraint, "TIME_VARIABLE_VALUE")
        time_variable = find_child(constraint, "TIME_VARIABLE")
        return (action_mode.value, time_variable.value if time_variable else "", value.value if value else "")
    return None

def get_then_constraint(then_clause: Tree):
    constraint = find_first_data(then_clause, "within_time")
    if(constraint):
        value = find_child(constraint, "TIME_VARIABLE_VALUE")
        time_variable = find_child(constraint, "TIME_VARIABLE")
        return ("I",time_variable.value if time_variable else "", value.value if value else "")
    return None

def constraint_to_string(constraint: tuple):
    return f'x &lt;= {constraint[2] * ( 60 if constraint[1] == "minutes" else 3600 if constraint[1] == "hours" else 1)}'



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

def generateId(index):
    #index += 1
    return "id" + index.__str__()


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


def guard_to_operator(guard: str):
    return "==" if guard == "equal to" else "&gt;" if guard == "greater than" else "&lt;"


def state_guard_to_ctl_operator(guard: str):
    return "" if guard == "is" else "" if guard == "are" else "not"

def guards_to_operator(state_guard: str, guard: str):
    state_guard_is_positive = state_guard == "is" or state_guard == "are"
    if(state_guard_is_positive):
        if(guard == "equal to"):
            return "=="
        if(guard == "greater than"):
            return "&gt;"
        if(guard == "less than"):
            return "&lt;"
    else:
        if(guard == "equal to"):
            return "!="
        if(guard == "greater than"):
            return "&lt;="
        if(guard == "less than"):
            return "&gt;="
        
def action_mode_is_positive(action_mode: str):
    return False if action_mode == "I do not" else True