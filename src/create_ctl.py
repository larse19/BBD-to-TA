import os
from itertools import chain
from typing import List, get_type_hints

from lark import Token, Tree

from bddProcessor import parse
from classes import Location
from helper_functions import (action_mode_is_positive, commit_action,
                              create_channel_name, find_child, get_location,
                              guard_to_operator, guards_to_operator,
                              state_guard_to_ctl_operator)


def given_clause_to_ctl(clause: Tree):
    state_name = None
    property_name = None
    property_value = None
    entity_name = None
    guard = None
    state_guard = None
    for child in clause.children:
        if isinstance(child, Tree) and child.data == "entity_property":
            for subchild in child.children:
                if isinstance(subchild, Token) and subchild.type == "ENTITY_NAME":
                    entity_name = subchild.value
                if isinstance(subchild, Token) and subchild.type == "PROPERTY_NAME":
                    property_name = subchild.value
        if isinstance(child, Token) and child.type == "STATE_NAME":
            state_name = child.value
        if isinstance(child, Token) and child.type == "STATE_GUARD":
            state_guard = child.value
        if isinstance(child, Token) and child.type == "PROPERTY_VALUE" :
            property_value = child.value
        if isinstance(child, Token) and child.type == "GUARD":
            guard = child.value

    # if clause points to a state -> TA_name.state_name
    if(state_name):
        return f'{state_guard_to_ctl_operator(state_guard)} {entity_name}.{state_name} '

    #if clause points to a property -> [entity.](entity_instance | property_instance) (= | <= | >=) value
    if(property_value):
        try:
            int(property_value)
            return f' {entity_name}.{property_name} {guards_to_operator(state_guard,guard)} {property_value} '
        except ValueError:
            return  f'{property_value} {guards_to_operator(state_guard,guard)} true'



def action_target_to_ctl(target: str)-> str:
    return f'user.{target}'


def evaluate_action(action: Tree, current_location_name: str, user_locations: list[Location]) -> Location:
    location = get_location(current_location_name, user_locations)
    t = commit_action(location, action, [])
    if t:
        return t.target.name
    return None

    
    # print(actions)
    # statement = ""
    # action_mode = None
    # action_name = None
    # action_value = None
    # guard = None
    # entity_name = None
    # entity_instance = None
    # property_name = None
    # property_instance = None
    # state_name = None
    # time_variable = None
    # time_value = None

    # for child in action.children:
    #     if isinstance(child, Tree) and child.data == "within_time":
    #         for subchild in child.children:
    #             if isinstance(subchild, Token) and subchild.type == "TIME_VARIABLE":
    #                 time_variable = subchild.value
    #             elif isinstance(subchild, Token) and subchild.type == "TIME_VARIABLE_VALUE":
    #                 time_value = subchild.value
    #     elif isinstance(child, Tree) and child.data == "entity_property":
    #         for subchild in child.children:
    #             if isinstance(subchild, Token) and subchild.type == "ENTITY_NAME":
    #                 entity_name = subchild.value
    #             elif isinstance(subchild, Token) and subchild.type == "PROPERTY_NAME":
    #                   property_name = subchild.value
    #     elif isinstance(child, Token) and child.type == "ACTION_MODE":
    #         action_mode = child.value
    #     elif isinstance(child, Token) and child.type == "ACTION_NAME":
    #         action_name = child.value
    #     elif isinstance(child, Token) and child.type == "GUARD":
    #         guard = child.value
    #     elif isinstance(child, Token) and child.type == "ACTION_VALUE":
    #         action_value = child.value

    # if(time_value):
    #     statement = (f'x {"&lt;=" if action_mode_is_positive(action_mode) else "&gt;"} {time_value}')
    


    # return statement

# returns list of (ctl, scenario_name)
def create_ctl(user_locations: list[Location]) -> list[(str, str)]:
    dirname = os.path.dirname(__file__)

    text = open(os.path.join(dirname, "BDD_full.txt"), "r")
    ast = parse(text.read())
    text.close()

    ctls = []

    for scenario in ast.find_data("scenario"):
        left_side = []
        right_side = []

        current_location = None
        
        # Evaluate all given clauses
        given_clauses = scenario.find_data("given_clause")
        for given_clause in given_clauses:
            source = find_child(given_clause, "STATE_NAME")
            if(source):
                current_location = source.value
            c = given_clause_to_ctl(given_clause)
            if(c):
                left_side.append(c)

        # Evaluate all actions
        actions = chain(scenario.find_data("action"), scenario.find_data("concurrent_action"))
        for action in actions:
            current_location = evaluate_action(action, current_location, user_locations)
        
        if(current_location):
            left_side.append(action_target_to_ctl(current_location))

        ctl_text = "("
        ctl_text += " and ".join(left_side)
        ctl_text += ") --> ("

        # Evaluate all then clauses
        then_clauses = scenario.find_data("then_clause")
        for then_clause in then_clauses:
            c = given_clause_to_ctl(then_clause)
            if(c):
                right_side.append(c)

        ctl_text += " and ".join(right_side)
        ctl_text += ")"

        ctls.append((ctl_text, scenario.children[0].value))

    return ctls

if __name__ == "__main__":
    create_ctl()