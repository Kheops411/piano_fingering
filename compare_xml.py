from lxml import etree
import sys

def canonicalize_xml(filepath):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(filepath, parser)
    for el in tree.xpath('//*[@id]'):
        del el.attrib['id']
    for el in tree.xpath('//*[@xml:id]'):
        del el.attrib['{http://www.w3.org/XML/1998/namespace}id']
    return etree.tostring(tree.getroot(), method='c14n', exclusive=True, with_comments=False)

original_xml = canonicalize_xml('original/output.xml')
new_xml = canonicalize_xml('new/output.xml')

if original_xml == new_xml:
    print("XML files are identical after canonicalization.")
    sys.exit(0)
else:
    print("XML files differ after canonicalization.")
    sys.exit(1)
