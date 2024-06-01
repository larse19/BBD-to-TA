# BBD-to-TA

This is a software tool for created Timed Automata models in UPPAAL, based on Behavior-Driven Development scenarios, written using a DSL.

The tool is the result of a Masters Thesis in Software Engineering, and might not be complete.

# Setup

The tool is built using python 3.6, which is required for the tool to run.

To install dependencies, run this command:

```
pip install -r src/requirements.txt
```

# How to use

In a terminal, enter ./src and write following command:

```cmd
py bddmap.py -i [input file] -o [output file]
```

The input file has to be .txt file containing BDD scenarios, following the grammar described in ./src/grammar.lark

The output file has to be a .xml file
