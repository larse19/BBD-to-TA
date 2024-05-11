import os
from copy import copy
from itertools import chain

from lark import ParseTree, Token, Tree

from classes import Entity, Label, Location
from helper_functions import (add_label, add_variable, commit_action,
                              create_channel_name, create_location,
                              create_transition, find_child, get_location,
                              get_state_guard_boolean, guard_to_operator)


def create_main_ta(ast: ParseTree) -> tuple[str, list[Location], list[str], list[str], list[str]]:

    globalDeclarations = ["clock x;"]

    variable_names = []
    channels = []

    entities = []
    main_entity = None
    entity_names = []
    all_locations = []

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
            current = (None, None)
            for property in property.children :
                if(property.type == "PROPERTY_NAME"):
                    if(current[0]):
                        properties.append(current)
                    current = (property.value, None)
                if(property.type == "INITIAL_PROPERTY_VALUE"):
                    current = (current[0], property.value)
                
        # single_property = find_child(entity, "PROPERTY_NAME")
        # if(single_property and single_property not in properties):
        #     properties.append(single_property.value)

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
    #next(ast.find_data("scenario"))


    def create_entity_type(entity: Entity):
        nonlocal globalDeclarations
        variable_string = 'struct {\n'
        for state in entity.states:
            variable_string += f'\t{"bool"} {state};\n'
        for property in entity.properties:
            variable_string += f'\t{"int"} {property[0]}{property[1] if property[1] else ""};\n'
        variable_string += f'{"}"} {entity.name};\n'
        globalDeclarations.append(variable_string)


    # new Rule 3: The first <state name> in the list of states, of the first entity, is mapped to the initial location of the TA
    initial_location = create_location(main_entity.states[0],  True, 0, 0, all_locations)

    # Create locations for all states in the main entity
    for state in entities[0].states:
        create_location(state,  False, 0, 0, all_locations)

    for property in main_entity.properties:
        add_variable(variable_names, f"int {property[0]}{property[1] if property[1] else ''}")

    # # Create properties as variables
    # for child in ast.iter_subtrees():
    #     for instance in chain(child.find_data("PROPERTY_INSTANCE"), child.find_data("ENTITY_INSTANCE")):
    #         print(instance)


    # Create all other entities as structs
    for i in range(1, len(entities)):
        create_entity_type(entities[i])

    for scenario in scenarios:
        current_location = None
        labels = []
        given_labels = []
        is_first_action = True


        for given in scenario.find_data("given_clause"):
            # print("GIVEN", given)
            # print(given)
            given_entity = ""
            property_name = ""
            guard = ""
            for child in given.children:
                if(isinstance(child, Token)):
                    if(child.type == "GUARD"):
                        guard = guard_to_operator(child.value)
                    elif(child.type == "PROPERTY_VALUE"):
                        if(given_entity):
                            add_label(given_labels, Label("guard", [f'{(given_entity + ".") if given_entity != main_entity.name else ""}{property_name} {guard} {child.value}']))
                        else:
                            add_label(given_labels, Label("guard", [f'{property_name} {guard} {child.value}']))
                if(isinstance(child, Tree)):
                    entity_name = find_child(child, "ENTITY_NAME")
                    if(entity_name):
                        given_entity = entity_name.value
                    _property_name = find_child(child, "PROPERTY_NAME")
                    if(_property_name):
                        property_name = _property_name.value
                    _entity_instance = find_child(child, "ENTITY_INSTANCE")
                    if(_entity_instance):
                        given_entity = _entity_instance.value
                        if(given_entity not in entities):
                            for e in entities:
                                if(e.name == entity_name.value):
                                    new_entity = copy(e)
                                    new_entity.name = _entity_instance.value
                                    create_entity_type(new_entity)
                                    entities.append(new_entity)
                                    break
            
            # print("given:", given_entity, "property:", property_name,"guard:", guard)

            entity = given.children[0]
            source = find_child(given, "STATE_NAME")
            if(not source):
                continue
            if(given_entity == main_entity.name):
                current_location = get_location(source.value, all_locations)
        for action in chain(scenario.find_data("action"), scenario.find_data("concurrent_action")):
            if(current_location != None):

                action_name = create_channel_name(action)
                
                action_transition = commit_action(current_location, action, channels)

                target = None
                if(action_transition):
                    if(is_first_action):
                        is_first_action = False
                        for label in given_labels:
                            action_transition.add_label(label)
                    target = action_transition.target

                # Set target as next location from action transition
                if(action_transition):
                    target = action_transition.target

                # Find target location
                if(not target):
                    for then_clause in scenario.find_data("then_clause"):
                        then_entity = ""
                        for child in then_clause.children:
                            if(isinstance(child, Tree)):
                                entity_name = find_child(child, "ENTITY_NAME")
                                if(entity_name):
                                    then_entity = entity_name.value
                            else:
                                if(then_entity == main_entity.name):
                                    if(child.type == "STATE_NAME"):
                                        target = get_location(child.value, all_locations)
                                        add_label(labels, Label("synchronisation", [action_name + "?"]))
                        if(target):
                            break
                    if(action_transition):
                        action_transition.target = target
                else:
                    current_location = target

                for then_clause in scenario.find_data("then_clause"):
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
                            _entity_instance = find_child(child, "ENTITY_INSTANCE")
                            if(_entity_instance):
                                then_entity = _entity_instance.value
                                if(then_entity not in entities):
                                    for e in entities:
                                        if(e.name == entity_name.value):
                                            new_entity = copy(e)
                                            new_entity.name = _entity_instance.value
                                            create_entity_type(new_entity)
                                            entities.append(new_entity)
                                            break
                                        
                        else:
                            if(then_entity == main_entity.name):
                                if(child.type == "STATE_NAME"):
                                    pass
                                elif(child.type == "PROPERTY_VALUE" or child.type == "PROPERTY_INSTANCE"):
                                    try:
                                        int(child.value)
                                        add_label(labels, Label("assignment", [f'{then_property} := {child.value}']))
                                        add_variable(variable_names, "int " + then_property)
                                    except ValueError:
                                        add_label(labels, Label("assignment", [f'{child.value} := true']))
                                        add_variable(variable_names,"bool " + child.value)
                            else:
                                if(child.type == "STATE_GUARD"):
                                    last_guard = get_state_guard_boolean(child)
                                if(child.type == "STATE_NAME"):
                                    add_label(labels, Label("assignment", [f'{then_entity}.{child.value} := {last_guard}']))
                                elif(child.type == "PROPERTY_VALUE" or child.type == "PROPERTY_INSTANCE" or child.type == "ENTITY_INSTANCE"):
                                    try:
                                        int(child.value)
                                        if(then_entity):
                                            add_label(labels, Label("assignment", [f'{then_entity}.{then_property} := {child.value}']))
                                        else:
                                            add_label(labels, Label("assignment", [f'{then_property} := {child.value}']))
                                            add_variable(variable_names, "int " + then_property)
                                    except ValueError:
                                        add_variable(variable_names, "bool " + child.value)
                                        add_label(labels, Label("assignment", [f'{child.value} := true']))
                

                for label in labels:
                    if(current_location == target):
                        print("SAME", current_location.name, action_name)
                    create_transition(current_location, target, action_name, label)
                current_location = target
                
    for variable in variable_names:
        globalDeclarations.append(f"{variable};")

    return (ta_name, all_locations, variable_names, channels, globalDeclarations)

    
