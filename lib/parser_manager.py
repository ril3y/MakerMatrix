import importlib.util
import os

class ParserManager:
    def __init__(self):
        self.parsers = self.load_parsers()

    def load_parsers(self):
        parsers = []
        parser_dir = './parsers/'
        for filename in os.listdir(parser_dir):
            if self.is_valid_parser_file(filename):
                module = self.load_module_from_file(parser_dir, filename)
                parsers.extend(self.get_parser_instances(module))
        return parsers

    def is_valid_parser_file(self, filename):
        return (os.path.isfile(os.path.join('./parsers/', filename)) and
                filename.endswith('.py') and not filename.startswith('__'))

    def load_module_from_file(self, dir, filename):
        module_name = filename[:-3]
        module_path = os.path.join(dir, filename)
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def get_parser_instances(self, module):
        return [getattr(module, attr_name)() for attr_name in dir(module)
                if isinstance(getattr(module, attr_name), type) and 'Parser' in str(getattr(module, attr_name).__bases__)]

    def parse_data(self, data):
        for parser in self.parsers:
            if parser.matches(data):
                parser.part.generate_uuid()
                parser.parse(data)
                return parser
        return None

# Usage example:
# parser_manager = ParserManager()
# parsed_data = parser_manager.parse_data(raw_data)
