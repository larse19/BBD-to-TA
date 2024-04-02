from classes import Location, Nails, Position, Transition


def build(name: str, init_location: Location, channels: list[str], declarations: str):
    startString = '''<?xml version="1.0" encoding="utf-8"?>
    <!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' 'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>
    <nta>\n'''
    declarationStart = '<declaration>\n'
    declarationEnd = '</declaration>\n'

    full_text_file = startString
    for channel in channels:
            declarations += f"chan {channel};\n"

    globalDeclarationFinal = declarationStart + declarations + declarationEnd
    full_text_file += globalDeclarationFinal

    explored_locations = []
    nail_positions = []
    label_positions = []


    template_text = "<template>\n"
    template_text += "\t<name>" + name + "</name>\n"
    locations_text = ""
    transitions_text = ""
    init_text = ""


    def target_is_left_of_source(source: Location, target: Location):
        return target.position.x < source.position.x


    def get_transition_nails(transition: Transition):
        nonlocal nail_positions
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
        nonlocal label_positions
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
        nonlocal transitions_text
        transitions_text += f'\t<transition><source ref="{transition.source.id}"/><target ref="{transition.target.id}"/>\n'
        nails = get_transition_nails(transition)

        for label in transition.labels:
            position = calculate_label_position(transition, nails)
            transitions_text += f'\t<label kind="{label.kind}" x="{position.x}" y="{position.y}">{label.text}</label>\n'

        transitions_text += f'\t<nail x="{nails.nail1.x}" y="{nails.nail1.y}"/>\n'
        transitions_text += f'\t<nail x="{nails.nail2.x}" y="{nails.nail2.y}"/>\n'
        transitions_text += "</transition>\n"
    
    def print_location_to_file(location: Location):
        nonlocal locations_text, init_text
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

    print_location_to_file(init_location)

    template_text += locations_text

    template_text += init_text

    template_text += transitions_text

    template_text += "</template>\n" 
    full_text_file += template_text   

    full_text_file += f"<system>\nsystem {name}, user;\n</system>\n"

    full_text_file += "</nta>"

    return full_text_file