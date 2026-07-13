from lxml import etree as ET


def convert_node_to_dict(node):
    node_dict = {}
    for node_data in node:
        node_dict[node_data.tag] = node_data.text

    return node_dict


def write_big5_xml(root, xml_file_name):
    """以健保要求的格式輸出 XML: <?xml version="1.0" encoding="Big5"?>"""
    xml_bytes = ET.tostring(
        root,
        pretty_print=True,
        encoding="Big5",
        xml_declaration=False,  # ✅ 關閉 lxml 自動產生的宣告, 由下面自行輸出
    )
    with open(xml_file_name, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="Big5"?>\n')
        f.write(xml_bytes)

    ET.parse(xml_file_name)
