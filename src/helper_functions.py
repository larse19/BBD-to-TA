from lark import Token, Tree

from classes import Label, Location, Transition


def get_state_guard_boolean(token: Token):
    if(token.type == "STATE_GUARD"):
        return "true" if token.value == "is" else "true" if token.value == "are" else "false"
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

def create_location(name: str, init: bool, pos_x: int, pos_y: int, all_locations: list[Location]):
    location = Location(name, generateId(len(all_locations)), [], init, pos_x, pos_y)
    if(location in all_locations):
        return
    all_locations.append(location)
    return location

def get_location(name: str, all_locations: list[Location]):
    for location in all_locations:
        if location.name == name:
            return location
    return None


def commit_action(current: Location, action: Tree, channels: list[str]):
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
            return transition.target
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

def generateId(index):
    index += 1
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
