import os
from itertools import chain

from lark import ParseTree, Token, Tree

from build_xml import build, build_ctl, build_ta
from classes import Entity, Label, Location
from create_ctl import create_ctl
from create_user import create_user
from helper_functions import (commit_action, create_channel_name,
                              create_location, create_transition, find_child,
                              get_location, get_state_guard_boolean,
                              guard_to_operator)


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
    next(ast.find_data("scenario"))


    def create_entity_type(entity: Entity):
        nonlocal globalDeclarations
        variable_string = 'struct {\n'
        for state in entity.states:
            variable_string += f'\t{"bool"} {state};\n'
        for property in entity.properties:
            variable_string += f'\t{"int"} {property};\n'
        variable_string += f'{"}"} {entity.name};\n'
        globalDeclarations.append(variable_string)


    # new Rule 3: The first <state name> in the list of states, of the first entity, is mapped to the initial location of the TA
    initial_location = create_location(main_entity.states[0],  True, 0, 0, all_locations)

    # Create locations for all states in the main entity
    for state in entities[0].states:
        create_location(state,  False, 0, 0, all_locations)

    # # Create properties as variables
    # for child in ast.iter_subtrees():
    #     for instance in chain(child.find_data("PROPERTY_INSTANCE"), child.find_data("ENTITY_INSTANCE")):
    #         print(instance)


    # Create all other entities as structs
    for i in range(1, len(entities)):
        create_entity_type(entities[i])

    for scenario in scenarios:
        print("\n", scenario.children[0].value)
        current_location = None
        labels = []
        for given in scenario.find_data("given_clause"):
            # print(given)
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
            current_location = get_location(source.value, all_locations)
        if(current_location):
            for action in chain(scenario.find_data("action"), scenario.find_data("concurrent_action")):
                action_name = create_channel_name(action)
                action_transition = commit_action(current_location, action, channels)
                next_location = None
                if(action_transition):
                    next_location = action_transition.target

                if(not next_location):
                    target = next_location
                    # labels = [] 
                    # constraint = get_action_constraint(action)
                    # if(constraint):
                    #     labels.append(Label("guard", constraint_to_string(constraint)))
                    for then_clause in scenario.find_data("then_clause"):
                        then_entity = ""
                        then_property = ""
                        then_entity_instance = ""
                        last_guard = "true"
                        for child in then_clause.children:
                            if(isinstance(child, Tree)):
                                print(then_clause)
                                entity_name = find_child(child, "ENTITY_NAME")
                                if(entity_name):
                                    then_entity = entity_name.value
                                property_name = find_child(child, "PROPERTY_NAME")
                                if(property_name):
                                    then_property = property_name.value
                                entity_instance = find_child(child, "ENTITY_INSTANCE")
                                if(entity_instance):
                                    then_entity_instance = entity_instance.value
                                print(then_entity, then_property, then_entity_instance)
                                    
                            else:
                                if(then_entity == main_entity.name):
                                    if(child.type == "STATE_NAME"):
                                        target = get_location(child.value, all_locations)
                                        # TODO: add ! sync to user template
                                        labels.append(Label("synchronisation", action_name + "?"))
                                        if(not target):
                                            # print("!!!",child.value)
                                            pass
                                    elif(child.type == "PROPERTY_VALUE" or child.type == "PROPERTY_INSTANCE"):
                                        try:
                                            int(child.value)
                                            labels.append(Label("assignment", f'{then_property} := {child.value}'))
                                            variable_names.append(then_property)
                                        except ValueError:
                                            variable_names.append(child.value)
                                            labels.append(Label("assignment", f'{child.value} := true'))
                                else:
                                    if(child.type == "STATE_GUARD"):
                                        last_guard = get_state_guard_boolean(child)
                                    # print(child.type, child.value)
                                    # TODO: update entity struct
                                    if(child.type == "STATE_NAME"):
                                        labels.append(Label("assignment", f'{then_entity}.{child.value} := {last_guard}'))
                                    elif(child.type == "PROPERTY_VALUE" or child.type == "PROPERTY_INSTANCE"):
                                        try:
                                            int(child.value)
                                            labels.append(Label("assignment", f'{then_entity}.{then_property} := {child.value}'))
                                        except ValueError:
                                            variable_names.append(child.value)
                                            labels.append(Label("assignment", f'{child.value} := true'))
                    if(action_transition):
                        action_transition.target = target

                    for label in labels:
                        create_transition(current_location, target, action_name, label)
                    current_location = target
                else:
                    current_location = next_location
                
    for variable in variable_names:
        globalDeclarations.append(f'bool {variable};')

    return (ta_name, all_locations, variable_names, channels, globalDeclarations)

    
