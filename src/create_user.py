import os
from itertools import chain

from lark import ParseTree, Token, Tree

from bddProcessor import parse
from build_xml import build_ta
from classes import Entity, Label, Location
from helper_functions import (add_label, commit_action, constraint_to_string,
                              create_channel_name, create_location,
                              create_transition, find_child,
                              get_action_constraint, get_location,
                              guard_to_operator)


def create_user(ast: ParseTree) -> tuple[str, list[Location]]:

    location_x_offset = 200
    channels = []

    entities = []
    main_entity = None
    entity_names = []
    location_index = -1
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

    #Rule 2 The <entity name> of the first entity (main entity) is implemented as the name of the TA.
    ta_name = "user"

    scenarios = ast.find_data("scenario")

    # new Rule 3: The first <state name> in the list of states, of the first entity, is mapped to the initial location of the TA
    initial_location = create_location(main_entity.states[0],  True, 0, 0, all_locations)

    # Create locations for all states in the main entity
    for state in entities[0].states:
        create_location(state,  False, location_index * location_x_offset, 0, all_locations)
    
    for scenario in scenarios:
        # print("\n", scenario.children[0].value)
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
                # if(isinstance(child, Token)):
                #     if(child.type == "GUARD"):
                #         guard = guard_to_operator(child.value)
                #     elif(child.type == "PROPERTY_VALUE"):
                #         if(given_entity):
                #             add_label(given_labels, Label("guard", [f'{(given_entity + ".") if given_entity != main_entity.name else ""}{property_name} {guard} {child.value}']))
                #         else:
                #             add_label(given_labels, Label("guard", [f'{property_name} {guard} {child.value}']))
                if(isinstance(child, Tree)):
                    entity_name = find_child(child, "ENTITY_NAME")
                    if(entity_name):
                        given_entity = entity_name.value
                    _property_name = find_child(child, "PROPERTY_NAME")
                    if(_property_name):
                        property_name = _property_name.value
            
            # print("given:", given_entity, "property:", property_name,"guard:", guard)

            entity = given.children[0]
            source = find_child(given, "STATE_NAME")
            if(not source):
                continue
            if(given_entity == main_entity.name):
                current_location = get_location(source.value, all_locations)
   
        if(current_location):
            for action in chain(scenario.find_data("action"), scenario.find_data("concurrent_action")):
                action_name = create_channel_name(action)
                action_transition = commit_action(current_location, action, channels)
                next_location = None
                if(action_transition):
                    if(is_first_action):
                        is_first_action = False
                        for label in given_labels:
                            action_transition.add_label(label)
                    next_location = action_transition.target

                if(not next_location):
                    target = next_location

                    for then_clause in scenario.find_data("then_clause"):

                        for child in then_clause.children:
                            if(isinstance(child, Token)):
                                if(child.type == "STATE_NAME"):
                                    target = get_location(child.value, all_locations)
                                    add_label(labels,Label("synchronisation", [action_name + "!"]))


                    constraint = get_action_constraint(action)
                    # if(current_location != target):
                    if(constraint):
                        invariant_location = create_location("inv_" + action_name, False, 0 ,0 ,all_locations, constraint_to_string(constraint))
                        for label in labels:
                            transition = create_transition(current_location, invariant_location, action_name, label)
                            if(target == initial_location):
                                transition = create_transition(invariant_location, target, action_name, Label("assignment", ["x := 0"]))
                            else:
                                transition = create_transition(invariant_location, target, action_name, None)
                            transition.invariant_location = invariant_location
                    else:
                        for label in labels:
                            transition = create_transition(current_location, target, action_name, label)

                    current_location = target
                else:
                    current_location = next_location

    return (ta_name, all_locations)


