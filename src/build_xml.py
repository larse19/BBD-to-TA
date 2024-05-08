from classes import Location, Nails, Position, Transition


def nail_between_nails(nail: Nails, all: list[Nails]):
    if(nail in all):
        return True
    for n in all:
        # if the line between the position of the nails of "nail" cross the line of any other set of nails, return True



        if(n.nail1.y == nail.nail1.y):
            # if any of the nails, are between two existing nails
            if((n.nail1.x < nail.nail2.x and n.nail1.x > nail.nail1.x) or (n.nail1.x > nail.nail2.x and n.nail1.x < nail.nail1.x) or 
                (n.nail2.x < nail.nail2.x and n.nail2.x > nail.nail1.x) or (n.nail2.x > nail.nail2.x and n.nail2.x < nail.nail1.x)):
                return True


            
def build_ta(name: str, init_location: Location):
    print(init_location)
    template_text = "<template>\n"
    template_text += "\t<name>" + name + "</name>\n"
    locations_text = ""
    transitions_text = ""
    init_text = ""
    explored_locations = []
    nail_positions = []
    label_positions = []


    def target_is_left_of_source(source: Location, target: Location):
        return target.position.x < source.position.x


    def get_transition_nails(source: Location, target: Location):
        nonlocal nail_positions
        location_offset = 200
        distance = abs(target.position.x - source.position.x)
        if(target_is_left_of_source(source, target)):
            nails = Nails(
                Position(source.position.x - 10, int(((distance / location_offset) )) * 50),
                Position(target.position.x + 10,  int(((distance / location_offset) )) * 50)
            )
            while (nail_between_nails(nails, nail_positions)):
                nails.nail1.y += 50
                nails.nail2.y += 50

            nail_positions.append(nails)
            return nails
        

        nails = Nails(
            Position(source.position.x + 10, - int(((distance / location_offset) ))* 50),
            Position(target.position.x - 10, - int(((distance / location_offset) ))* 50)
        )
        while (nail_between_nails(nails, nail_positions)):
            nails.nail1.y -= 50
            nails.nail2.y -= 50

        nail_positions.append(nails)
        return nails
        
    def calculate_label_position(transition: Transition, nails: Nails):
        nonlocal label_positions
        increment =  20 if target_is_left_of_source(transition.source, transition.target) else - 20
        base = 0 if target_is_left_of_source(transition.source, transition.target) else 20

        source_x = nails.nail1.x
        target_x = nails.nail2.x
        source_y = nails.nail1.y
        base_x = source_x + ((target_x-source_x) / 2)
        base_y = source_y - base
        position = Position(int(base_x), int(base_y))
        while position in label_positions:
            position.y += increment
        label_positions.append(position)
        return position

    def print_transition_to_file(transition: Transition):
        nonlocal transitions_text
        if((transition.source == transition.target) |  (not transition.target)):
            return
        source = transition.source
        # if(transition.invariant_location):
        #     print_location_to_file(transition.invariant_location)
        #     print_transition_to_file(Transition(source, transition.invariant_location, "", []))
        #     # transitions_text += f'\t<transition><source ref="{source.id}"/><target ref="{transition.invariant_location.id}"/></transition>\n'
        #     source = transition.invariant_location

        transitions_text += f'\t<transition><source ref="{source.id}"/><target ref="{transition.target.id}"/>\n'
        nails = get_transition_nails(source, transition.target)

        for label in transition.labels:
            position = calculate_label_position(transition, nails)
            # If more than one line of text, mark the extra lines as taken positions
            for i in range(1, len(label.text)):
                calculate_label_position(transition, nails)

            label_value = ',\n'.join(label.text)
            transitions_text += f'\t<label kind="{label.kind}" x="{position.x}" y="{position.y}">{label_value}</label>\n'
        if(nails.nail1.y != 0):
            transitions_text += f'\t<nail x="{nails.nail1.x}" y="{nails.nail1.y}"/>\n'
            transitions_text += f'\t<nail x="{nails.nail2.x}" y="{nails.nail2.y}"/>\n'
        transitions_text += "</transition>\n"
    
    def print_location_to_file(location: Location):
        if(not location):
            return
        nonlocal locations_text, init_text
        if(location in explored_locations):
            return
        explored_locations.append(location)

        location_text = f'''\t<location id="{location.id}" x="{location.position.x}" y="{location.position.y}"> 
        <name x="{location.position.x + 20}" y="{location.position.y }">{location.name}</name>\n'''
        
        if(location.invariant):
            location_text += f'\t\t<label kind="invariant" x="{location.position.x + 20}" y="{location.position.y +20}">{location.invariant}</label>\n'
        
        if(location.committed):
            location_text += "\t\t<committed/>\n" 
        
        if(location.init):
            init_text = f'\t<init ref="{location.id}"/>\n'

        location_text += "\t</location>\n"
        locations_text += location_text

        for transition in location.transitions:

            print_location_to_file(transition.target)
            print_transition_to_file(transition)

    print_location_to_file(init_location)

    template_text += locations_text

    template_text += init_text

    template_text += transitions_text

    template_text += "</template>\n" 

    return template_text


def build_ctl(formulas: list[(str, str)]):

    text = '''
    <queries>
    '''
    for formula in formulas:
         text += f'''
        <query>
            <formula>{formula[0]}</formula>
			<comment>{formula[1]}</comment>
        </query>
        '''
    
    text += '''
    </queries>
    '''

    return text
			
		

def build(names: list[str], template_text: str, query_text: str, channels: list[str], declarations: list[str]):
    startString = '''<?xml version="1.0" encoding="utf-8"?>
    <!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' 'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>
    <nta>\n'''
    declarationStart = '<declaration>\n'
    declarationEnd = '</declaration>\n'

    full_text_file = startString
    for channel in channels:
            declarations.append(f"chan {channel};")

    globalDeclarationFinal = declarationStart + "\n".join(declarations) + declarationEnd
    full_text_file += globalDeclarationFinal


    full_text_file += template_text   

    full_text_file += f"<system>\nsystem {','.join(names)};\n</system>\n"

    full_text_file += query_text

    full_text_file += "</nta>"

    return full_text_file