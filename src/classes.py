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
        self.invariant_location: "Location" = None

    def add_label(self, label: "Label"):
        if(label in self.labels):
            return
        self.labels.append(label)

    def __str__(self):
        return f"\nSource: {self.source}\nTarget: {self.target}\nAction: {self.action}\nLabels: {self.labels}\n"
    
    def __repr__(self):
        return f"({self.source.name} -> {self.target.name} : {self.action})"
    
    def __eq__(self, __value: object) -> bool:
        if(self.target is None):
            return self.source == __value.source and self.action == __value.action
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
        self.invariant = None

    def __str__(self):
        return f"({self.name}, {self.transitions})"
    
    def __repr__(self):
        return f"{self.name}{'(init)' if self.init else ''}"
    
    def __eq__(self, __value: object) -> bool:
        if(__value is None):
            return False
        return self.name == __value.name and self.invariant == __value.invariant
    
    def set_committed(self, committed: bool):
        self.committed = committed