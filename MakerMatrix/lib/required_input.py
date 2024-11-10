class RequiredInput:
    def __init__(self, field_name, data_type, prompt, value=None):
        self.field_name = field_name
        self.data_type = data_type
        self.prompt = prompt
        self.value = value

    def to_dict(self):
        return {
            "field_name": self.field_name,
            "data_type": self.data_type,
            "prompt": self.prompt,
            "value": self.value
        }

    def __repr__(self):
        return f"RequiredInput(field_name={self.field_name!r}, data_type={self.data_type!r}, prompt={self.prompt!r})"
