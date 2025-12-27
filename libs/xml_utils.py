import os


def set_xml_file_to_big5(xml_file_name, dest_file_name=None):
    from shutil import copyfile

    file_path, file_name = os.path.split(xml_file_name)
    temp_file_name = os.path.join(file_path, 'temp.xml')

    with open(xml_file_name, encoding='Big5') as in_file, open(temp_file_name, 'w', encoding='Big5') as out_file:
        txt = in_file.read()
        txt = txt.replace('\'', '"')
        txt = txt.replace('BIG5', 'Big5')
        out_file.write(txt)

    if dest_file_name is not None:
        copyfile(temp_file_name, dest_file_name)
    else:
        copyfile(temp_file_name, xml_file_name)

    os.remove(temp_file_name)

    # convert LF => CR/LF
    # if sys.platform == 'win32':
    #     with open(xml_file_name) as in_file, open(xml_out_file_name, 'w') as out_file:
    #         txt = in_file.read()
    #         txt = txt.replace('\n', '\n') # in windows system, \n will auto lead with \r
    #         out_file.write(txt)
    # else:
    #     with open(xml_out_file_name, 'w') as out_file:
    #         cmd = ['sed', 's/$/\r/', xml_file_name]
    #         sp = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=out_file)
    #         sp.communicate()


def convert_node_to_dict(node):
    node_dict = {}
    for node_data in node:
        node_dict[node_data.tag] = node_data.text

    return node_dict
