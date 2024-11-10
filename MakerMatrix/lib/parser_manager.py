import importlib.util
import os

from MakerMatrix.parts.parts import Part


def load_module_from_file(directory, filename):
    module_name = filename[:-3]
    module_path = os.path.join(directory, filename)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_valid_parser_file(filename):
    return (os.path.isfile(os.path.join('./parsers/', filename)) and
            filename.endswith('.py') and not filename.startswith('__'))


def get_parser_instances(module):
    return [getattr(module, attr_name)() for attr_name in dir(module)
            if isinstance(getattr(module, attr_name), type) and 'Parser' in str(getattr(module, attr_name).__bases__)]


def load_parsers():
    parsers = []
    parser_dir = './parsers/'
    try:

        for filename in os.listdir(parser_dir):
            if is_valid_parser_file(filename):
                module = load_module_from_file(parser_dir, filename)
                parsers.extend(get_parser_instances(module))
        return parsers
    except TypeError as e:
        print(f"Invalid parser file '{filename} : {e}")


class ParserManager:
    def __init__(self):
        self.parsers = load_parsers()

    def parse_data(self, data):
        for parser in self.parsers:
            if parser.matches(data):
                parser.part = Part()
                parser.required_inputs = []
                parser.part.generate_part_id()
                parser.parse(data)
                return parser
        return None

    def get_parser_instances(self, module):
        return [getattr(module, attr_name)() for attr_name in dir(module)
                if
                isinstance(getattr(module, attr_name), type) and 'Parser' in str(getattr(module, attr_name).__bases__)]

# Usage example:
# parser_manager = ParserManager()
# parsed_data = parser_manager.parse_data(raw_data)
