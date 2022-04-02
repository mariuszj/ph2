from typing import Optional, Union, Dict


def print_influxdb_format(
        measurement: str, fields: Dict[str, Union[str, int, float]],
        tags: Optional[Dict[str, Union[str, int, float]]] = None,
        timestamp: Optional[int] = None):
    result = f'{measurement}'

    if tags:
        for tag_name, tag_value in tags.items():
            if isinstance(tag_value, str):
                tag_value = tag_value.strip()
                tag_value = tag_value.replace(' ', r'\ ')
                tag_value = tag_value.replace(',', r'\,')
                tag_value = tag_value.replace('=', r'\=')

            result += f',{tag_name}={tag_value}'

    fields_list = []

    for field_name, field_value in fields.items():
        if isinstance(field_value, str):
            field_value = field_value.strip()
            if field_value not in \
                    ['true', 'True', 'TRUE', 't', 'T', 'false', 'False', 'FALSE', 'f', 'F', ]:
                if not is_str_repr_of_int(field_value):
                    field_value = field_value.replace('"', '\\"')
                    field_value = f'"{field_value}"'

        fields_list.append(f'{field_name}={field_value}')

    result += f' {",".join(fields_list)}'

    if timestamp:
        result += f' {timestamp}'

    print(result)


def is_str_repr_of_int(string):
    if string.startswith('-') or string.startswith('+'):
        if string[1:-1].isdigit() and string.endswith('i'):
            return True

    if string[0:-1].isdigit() and string.endswith('i'):
        return True

    return False
