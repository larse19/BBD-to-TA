
import argparse
import os

from bddProcessor import parse
from build_xml import build, build_ctl, build_ta
from create_ctl import create_ctl
from create_main_entity import create_main_ta
from create_user import create_user


def convert(infile: str, outfile: str):

    dirname = os.path.dirname(__file__)

    text = open(os.path.join(dirname, infile), "r")
    ast = parse(text.read())
    text.close()

    (ta_name, main_locations, variable_names, channels, globalDeclarations) = create_main_ta(ast)
    ta_text = build_ta(ta_name, main_locations[0])

    (user_name, user_locations) = create_user(ast)
    user_text = build_ta(user_name, user_locations[0])

    query_text = build_ctl(create_ctl(ast, user_locations))

    full_text_file = build([ta_name, "user"], ta_text + user_text, query_text, channels, globalDeclarations)

    outfile = open(os.path.join(dirname, outfile), "w")

    outfile.write(full_text_file)

    outfile.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert a BDD file to a UPPAAL file')
    parser.add_argument('-i', metavar='infile', nargs=1,
                        help='a .txt file with BDD code')
    parser.add_argument('-o', metavar='outfile', nargs=1,
                        help='a .xml file to write the UPPAAL save file to')

    args = parser.parse_args()
    infile = args.i[0]
    outfile = args.o[0]
    if(not infile or not outfile):
        raise ValueError("Input and output files must be provided")
    if not infile.endswith(".txt"):
        raise ValueError("Input file must be a .txt file")
    if not outfile.endswith(".xml"):
        raise ValueError("Output file must be a .xml file")
    if not os.path.isfile(infile):
        raise FileNotFoundError("Input file not found")
    
    convert(infile, outfile)
    