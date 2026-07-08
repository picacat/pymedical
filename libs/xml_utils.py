import os

# def set_xml_file_to_big5(xml_file_name, dest_file_name=None):
#     from shutil import copyfile

#     file_path, file_name = os.path.split(xml_file_name)
#     temp_file_name = os.path.join(file_path, 'temp.xml')

#     with open(xml_file_name, encoding='Big5') as in_file, open(temp_file_name, 'w', encoding='Big5') as out_file:
#         txt = in_file.read()
#         txt = txt.replace('\'', '"')
#         txt = txt.replace('BIG5', 'Big5')
#         out_file.write(txt)

#     if dest_file_name is not None:
#         copyfile(temp_file_name, dest_file_name)
#     else:
#         copyfile(temp_file_name, xml_file_name)

#     os.remove(temp_file_name)


def set_xml_file_to_big5(xml_file_name, dest_file_name=None):
    import tempfile
    from shutil import move

    fd, temp_file_name = tempfile.mkstemp(suffix=".xml")
    with (
        open(xml_file_name, encoding="cp950") as in_file,
        os.fdopen(fd, "w", encoding="cp950", errors="replace") as out_file,
    ):
        for line in in_file:
            out_file.write(line.replace("'", '"').replace("BIG5", "Big5"))

    move(temp_file_name, dest_file_name or xml_file_name)


def convert_node_to_dict(node):
    node_dict = {}
    for node_data in node:
        node_dict[node_data.tag] = node_data.text

    return node_dict
