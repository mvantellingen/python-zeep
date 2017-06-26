from collections import deque

from tests.utils import load_xml, DummyTransport
from zeep import xsd
from zeep.exceptions import XMLParseError


def test_element_parse_substituted():
    from lxml import etree
    from zeep.xsd.context import XmlParserContext
    schema = xsd.Schema(load_xml("""
           <?xml version="1.0"?>
           <xsd:schema
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:tns="http://tests.python-zeep.org/"
               targetNamespace="http://tests.python-zeep.org/"
               elementFormDefault="qualified">

               <xsd:element name="name" type="xsd:string"/>
               <xsd:element name="navn" substitutionGroup="tns:name"/>

               <xsd:complexType name="custinfo">
                 <xsd:sequence>
                   <xsd:element ref="tns:name"/>
                 </xsd:sequence>
               </xsd:complexType>

               <xsd:element name="customer" type="tns:custinfo"/>
               <xsd:element name="kunde" substitutionGroup="tns:customer"/> 
           </xsd:schema>
       """), strict=True)
    assert len(schema._substitution_groups) > 0, "No substitution groups were found!"
    assert len(schema._substitution_groups) == 2, "Must be exactly two substitution groups found."
    cust_elem = schema.get_element('{http://tests.python-zeep.org/}customer')

    assert cust_elem.is_substitution_group is True, "The 'customer' element must identify as a" \
                                                    " substitutionGroup"
    subsitututed_node = load_xml("""
            <ns0:kunde xmlns:ns0="http://tests.python-zeep.org/"
                           xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <ns0:navn>Hello World</ns0:navn>
            </ns0:kunde>
        """)
    original_node = load_xml("""
            <ns0:customer xmlns:ns0="http://tests.python-zeep.org/"
                           xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <ns0:name>Hello World</ns0:name>
            </ns0:customer>
        """)

    kunde_node_elements = deque([subsitututed_node])
    element_tag = etree.QName(kunde_node_elements[0].tag)
    context1 = XmlParserContext()
    p1 = cust_elem.parse_xmlelement_substituted(kunde_node_elements, schema, element_tag,
                                                substitution_group=None, context=context1)

    assert p1 is not None, "parse_element_substituted should return a match."
    assert isinstance(p1, tuple) and len(p1) == 2,\
        "parse_element_substituted match should be a tuple of length 2"
    assert str(p1[1]) == "kunde",\
        "parse_element_substituted should match with element named \"kunde\""

    cust_node_elements = deque([original_node])
    element_tag = etree.QName(cust_node_elements[0].tag)
    context2 = XmlParserContext()
    p2 = cust_elem.parse_xmlelement_substituted(cust_node_elements, schema, element_tag,
                                                substitution_group=None, context=context2)
    assert p2 == (None, None) or p2 is None,\
        "parse_element_substituted should return None when element does not " \
        "_need_ to be substituted."

def test_element_parse_substituted_with_no_sub_groups():
    from lxml import etree
    from zeep.xsd.context import XmlParserContext
    schema = xsd.Schema(load_xml("""
           <?xml version="1.0"?>
           <xsd:schema
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:tns="http://tests.python-zeep.org/"
               targetNamespace="http://tests.python-zeep.org/"
               elementFormDefault="qualified">

               <xsd:element name="name" type="xsd:string"/>

               <xsd:complexType name="custinfo">
                 <xsd:sequence>
                   <xsd:element ref="tns:name"/>
                 </xsd:sequence>
               </xsd:complexType>

               <xsd:element name="customer" type="tns:custinfo"/>
           </xsd:schema>
       """), strict=True)
    assert len(schema._substitution_groups) == 0, "Must be 0 substitution groups defined."
    cust_elem = schema.get_element('{http://tests.python-zeep.org/}customer')
    assert cust_elem.is_substitution_group is False, "The 'customer' element must not " \
                                                     "identify as a substitutionGroup."
    subsitututed_node = load_xml("""
            <ns0:kunde xmlns:ns0="http://tests.python-zeep.org/"
                           xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <ns0:navn>Hello World</ns0:navn>
            </ns0:kunde>
        """)
    original_node = load_xml("""
            <ns0:customer xmlns:ns0="http://tests.python-zeep.org/"
                           xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <ns0:name>Hello World</ns0:name>
            </ns0:customer>
        """)

    kunde_node_elements = deque([subsitututed_node])
    element_tag = etree.QName(kunde_node_elements[0].tag)
    context1 = XmlParserContext()
    p1 = cust_elem.parse_xmlelement_substituted(kunde_node_elements, schema, element_tag,
                                                substitution_group=None, context=context1)
    assert p1 == (None, None) or p1 is None,\
        "Substitution should not work when no substitution groups are defined."

    cust_node_elements = deque([original_node])
    element_tag = etree.QName(cust_node_elements[0].tag)
    context2 = XmlParserContext()
    p2 = cust_elem.parse_xmlelement_substituted(cust_node_elements, schema, element_tag,
                                                substitution_group=None, context=context2)
    assert p2 == (None, None) or p2 is None,\
        "parse_element_substituted should return None when element does not " \
        "_need_ to be substituted."

def test_element_parse_substituted_wrong_namespace():
    from lxml import etree
    from zeep.xsd.context import XmlParserContext
    # Example taken from https://www.w3schools.com/xml/schema_complex_subst.asp
    schema_a = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            elementFormDefault="qualified">

            <xsd:element name="name" type="xsd:string"/>
            <xsd:complexType name="custinfo">
              <xsd:sequence>
                <xsd:element ref="tns:name"/>
              </xsd:sequence>
            </xsd:complexType>

            <xsd:element name="customer" type="tns:custinfo"/>
        </xsd:schema>
    """)
    schema_b = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            xmlns:tnsa="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">
            <xsd:import
                schemaLocation="http://tests.python-zeep.org/a.xsd"
                namespace="http://tests.python-zeep.org/a"/>

            <xsd:element name="navn" substitutionGroup="tnsa:name"/>
            <xsd:element name="kunde" substitutionGroup="tnsa:customer"/> 
        </xsd:schema>
    """)
    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/a.xsd', schema_a)
    transport.bind('http://tests.python-zeep.org/b.xsd', schema_b)
    schema = xsd.Schema(schema_b, transport=transport, strict=True)
    assert len(schema._substitution_groups) > 0, "No substitution groups were found!"
    assert len(schema._substitution_groups) == 2, "Must be exactly two substitution groups."
    cust_elem = schema.get_element('{http://tests.python-zeep.org/a}customer')

    assert cust_elem.is_substitution_group is True, "The 'customer' element must be a" \
                                                    " substitutionGroup"
    subsitututed_node = load_xml("""
            <ns0:kunde xmlns:ns0="http://tests.python-zeep.org/c"
                           xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <ns0:navn>Hello World</ns0:navn>
            </ns0:kunde>
        """)
    original_node = load_xml("""
            <ns0:customer xmlns:ns0="http://tests.python-zeep.org/a"
                           xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
                <ns0:name>Hello World</ns0:name>
            </ns0:customer>
        """)

    kunde_node_elements = deque([subsitututed_node])
    element_tag = etree.QName(kunde_node_elements[0].tag)
    context1 = XmlParserContext()
    p1 = cust_elem.parse_xmlelement_substituted(kunde_node_elements, schema, element_tag,
                                                substitution_group=None, context=context1)
    assert p1 == (None, None) or p1 is None, \
        "Substitution should not work when element does not match substitution_group namespace."

def test_complex_type_element_substitution_same_namespace():
    # Example taken from https://www.w3schools.com/xml/schema_complex_subst.asp
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/"
            elementFormDefault="qualified">
            
            <xsd:element name="name" type="xsd:string"/>
            <xsd:element name="navn" substitutionGroup="tns:name"/>
            
            <xsd:complexType name="custinfo">
              <xsd:sequence>
                <xsd:element ref="tns:name"/>
              </xsd:sequence>
            </xsd:complexType>
            
            <xsd:element name="customer" type="tns:custinfo"/>
            <xsd:element name="kunde" substitutionGroup="tns:customer"/> 
        </xsd:schema>
    """), strict=True)
    assert len(schema._substitution_groups) > 0, "No substitution groups were found!"
    assert len(schema._substitution_groups) == 2, "Must be exactly two substitution groups found."
    cust_info = schema.get_type('{http://tests.python-zeep.org/}custinfo')
    name_elem = schema.get_element('{http://tests.python-zeep.org/}name')
    cust_elem = schema.get_element('{http://tests.python-zeep.org/}customer')
    assert name_elem.is_substitution_group is True, "The 'name' element must identify as a" \
                                                    " substitutionGroup"
    assert cust_elem.is_substitution_group is True, "The 'customer' element must identify as a" \
                                                    " substitutionGroup"
    original_node = load_xml("""
        <ns0:customer xmlns:ns0="http://tests.python-zeep.org/"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:name>Hello World</ns0:name>
        </ns0:customer>
    """)
    subsitututed_node = load_xml("""
        <ns0:kunde xmlns:ns0="http://tests.python-zeep.org/"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:navn>Hello World</ns0:navn>
        </ns0:kunde>
    """)
    data1 = cust_elem.parse(original_node, schema)
    data2 = cust_elem.parse(subsitututed_node, schema)
    assert data1._xsd_type == data2._xsd_type and data2._xsd_type == cust_info

    assert data2['navn'] == "Hello World" # name was substituted for 'navn'
    assert data2['name'] == "Hello World" # but name also still exists for backward compatibility


def test_complex_type_element_substitution_not_in_group():
    # Example taken from https://www.w3schools.com/xml/schema_complex_subst.asp
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/"
            elementFormDefault="qualified">

            <xsd:element name="name" type="xsd:string"/>
            <xsd:element name="navn" substitutionGroup="tns:name"/>

            <xsd:complexType name="custinfo">
              <xsd:sequence>
                <xsd:element ref="tns:name"/>
              </xsd:sequence>
            </xsd:complexType>

            <xsd:element name="customer" type="tns:custinfo"/>
            <xsd:element name="kunde" substitutionGroup="tns:customer"/> 
        </xsd:schema>
    """), strict=True)
    assert len(schema._substitution_groups) > 0, "No substitution groups were found!"
    assert len(schema._substitution_groups) == 2, "Must be exactly two substitution groups found."
    cust_info = schema.get_type('{http://tests.python-zeep.org/}custinfo')
    name_elem = schema.get_element('{http://tests.python-zeep.org/}name')
    cust_elem = schema.get_element('{http://tests.python-zeep.org/}customer')
    assert name_elem.is_substitution_group is True, "The 'name' element must identify as a" \
                                                    " substitutionGroup"
    assert cust_elem.is_substitution_group is True, "The 'customer' element must identify as a" \
                                                    " substitutionGroup"
    original_node = load_xml("""
        <ns0:customer xmlns:ns0="http://tests.python-zeep.org/"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:name>Hello World</ns0:name>
        </ns0:customer>
    """)
    subsitututed_node = load_xml("""
        <ns0:kunde xmlns:ns0="http://tests.python-zeep.org/"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:noun>Hello World</ns0:noun>
        </ns0:kunde>
    """)
    data1 = cust_elem.parse(original_node, schema)
    try:
        data2 = cust_elem.parse(subsitututed_node, schema)
        raise AssertionError("Should not have been able to parse that XML.")
    except XMLParseError as e:
        assert e.args[0] is not None, "Should have caught a populated XMLParseError"



def test_complex_type_element_substitution_out_of_order():
    # Example taken from https://www.w3schools.com/xml/schema_complex_subst.asp
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/"
            elementFormDefault="qualified">
            
            <xsd:element name="kunde" substitutionGroup="tns:customer"/> 
            
            <xsd:element name="name" type="xsd:string"/>
            <xsd:element name="navn" substitutionGroup="tns:name"/>

            <xsd:complexType name="custinfo">
              <xsd:sequence>
                <xsd:element ref="tns:name"/>
              </xsd:sequence>
            </xsd:complexType>

            <xsd:element name="customer" type="tns:custinfo"/>
        </xsd:schema>
    """), strict=True)
    assert len(schema._substitution_groups) > 0, "No substitution groups were found!"
    assert len(schema._substitution_groups) == 2, "Must be exactly two substitution groups found."
    cust_info = schema.get_type('{http://tests.python-zeep.org/}custinfo')
    name_elem = schema.get_element('{http://tests.python-zeep.org/}name')
    cust_elem = schema.get_element('{http://tests.python-zeep.org/}customer')
    assert name_elem.is_substitution_group is True, "The 'name' element must identify as a" \
                                                    " substitutionGroup"
    assert cust_elem.is_substitution_group is True, "The 'customer' element must identify as a" \
                                                    " substitutionGroup"


def test_complex_type_element_substitution_differ_namespace():
    # Example taken from https://www.w3schools.com/xml/schema_complex_subst.asp
    schema_a = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            elementFormDefault="qualified">

            <xsd:element name="name" type="xsd:string"/>
            <xsd:complexType name="custinfo">
              <xsd:sequence>
                <xsd:element ref="tns:name"/>
              </xsd:sequence>
            </xsd:complexType>

            <xsd:element name="customer" type="tns:custinfo"/>
        </xsd:schema>
    """)
    schema_b = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            xmlns:tnsa="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">
            <xsd:import
                schemaLocation="http://tests.python-zeep.org/a.xsd"
                namespace="http://tests.python-zeep.org/a"/>
                
            <xsd:element name="navn" substitutionGroup="tnsa:name"/>
            <xsd:element name="kunde" substitutionGroup="tnsa:customer"/> 
        </xsd:schema>
    """)
    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/a.xsd', schema_a)
    transport.bind('http://tests.python-zeep.org/b.xsd', schema_b)
    schema = xsd.Schema(schema_b, transport=transport, strict=True)
    assert len(schema._substitution_groups) > 0, "No substitution groups were found!"
    assert len(schema._substitution_groups) == 2, "Must be exactly two substitution groups found."
    cust_info = schema.get_type('{http://tests.python-zeep.org/a}custinfo')
    name_elem = schema.get_element('{http://tests.python-zeep.org/a}name')
    cust_elem = schema.get_element('{http://tests.python-zeep.org/a}customer')
    assert name_elem.is_substitution_group is True, "The 'name' element must identify as a" \
                                                    " substitutionGroup"
    assert cust_elem.is_substitution_group is True, "The 'customer' element must identify as a" \
                                                    " substitutionGroup"
    original_node = load_xml("""
        <ns0:customer xmlns:ns0="http://tests.python-zeep.org/a"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:name>Hello World</ns0:name>
        </ns0:customer>
    """)
    subsitututed_node = load_xml("""
        <ns0:kunde xmlns:ns0="http://tests.python-zeep.org/b"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:navn>Hello World</ns0:navn>
        </ns0:kunde>
    """)
    data1 = cust_elem.parse(original_node, schema)
    data2 = cust_elem.parse(subsitututed_node, schema)
    assert data1._xsd_type == data2._xsd_type and data2._xsd_type == cust_info

    assert data2['navn'] == "Hello World"  # name was substituted for 'navn'
    assert data2['name'] == "Hello World"  # but name also still exists for backward compatibility


def test_complex_type_element_substitution_differ_namespace_not_in_group():
    # Example taken from https://www.w3schools.com/xml/schema_complex_subst.asp
    schema_a = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            elementFormDefault="qualified">

            <xsd:element name="name" type="xsd:string"/>
            <xsd:complexType name="custinfo">
              <xsd:sequence>
                <xsd:element ref="tns:name"/>
              </xsd:sequence>
            </xsd:complexType>

            <xsd:element name="customer" type="tns:custinfo"/>
        </xsd:schema>
    """)
    schema_b = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            xmlns:tnsa="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">
            <xsd:import
                schemaLocation="http://tests.python-zeep.org/a.xsd"
                namespace="http://tests.python-zeep.org/a"/>

            <xsd:element name="navn" substitutionGroup="tnsa:name"/>
            <xsd:element name="kunde" substitutionGroup="tnsa:customer"/> 
        </xsd:schema>
    """)
    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/a.xsd', schema_a)
    transport.bind('http://tests.python-zeep.org/b.xsd', schema_b)
    schema = xsd.Schema(schema_b, transport=transport, strict=True)
    assert len(schema._substitution_groups) > 0, "No substitution groups were found!"
    assert len(schema._substitution_groups) == 2, "Must be exactly two substitution groups found."
    cust_info = schema.get_type('{http://tests.python-zeep.org/a}custinfo')
    name_elem = schema.get_element('{http://tests.python-zeep.org/a}name')
    cust_elem = schema.get_element('{http://tests.python-zeep.org/a}customer')
    assert name_elem.is_substitution_group is True, "The 'name' element must identify as a" \
                                                    " substitutionGroup"
    assert cust_elem.is_substitution_group is True, "The 'customer' element must identify as a" \
                                                    " substitutionGroup"
    original_node = load_xml("""
        <ns0:customer xmlns:ns0="http://tests.python-zeep.org/a"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:name>Hello World</ns0:name>
        </ns0:customer>
    """)
    subsitututed_node = load_xml("""
        <ns0:kunde xmlns:ns0="http://tests.python-zeep.org/b"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:noun>Hello World</ns0:noun>
        </ns0:kunde>
    """)
    data1 = cust_elem.parse(original_node, schema)
    try:
        data2 = cust_elem.parse(subsitututed_node, schema)
        raise AssertionError("Should not have been able to parse that XML.")
    except XMLParseError as e:
        assert e.args[0] is not None, "Should have caught a populated XMLParseError"

def test_complex_type_element_substitution_incorrect():
    # Example taken from https://www.w3schools.com/xml/schema_complex_subst.asp
    schema_a = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            elementFormDefault="qualified">

            <xsd:element name="name" type="xsd:string"/>
            <xsd:complexType name="custinfo">
              <xsd:sequence>
                <xsd:element ref="tns:name"/>
              </xsd:sequence>
            </xsd:complexType>

            <xsd:element name="customer" type="tns:custinfo"/>
        </xsd:schema>
    """)
    schema_b = load_xml("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            xmlns:tnsa="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">
            <xsd:import
                schemaLocation="http://tests.python-zeep.org/a.xsd"
                namespace="http://tests.python-zeep.org/a"/>
            <xsd:element name="noun"/>
            <xsd:element name="kunde" substitutionGroup="tnsa:customer"/> 
        </xsd:schema>
    """)
    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/a.xsd', schema_a)
    transport.bind('http://tests.python-zeep.org/b.xsd', schema_b)
    schema = xsd.Schema(schema_b, transport=transport, strict=True)
    assert len(schema._substitution_groups) > 0, "No substitution groups were found!"
    assert len(schema._substitution_groups) == 1, "Must be exactly one substitution group found."
    name_elem = schema.get_element('{http://tests.python-zeep.org/a}name')
    cust_elem = schema.get_element('{http://tests.python-zeep.org/a}customer')
    assert name_elem.is_substitution_group is False, "The 'name' element must not identify as a" \
                                                     " substitutionGroup"
    assert cust_elem.is_substitution_group is True, "The 'customer' element must identify as a" \
                                                    " substitutionGroup"
    original_node = load_xml("""
        <ns0:customer xmlns:ns0="http://tests.python-zeep.org/a"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:name>Hello World</ns0:name>
        </ns0:customer>
    """)
    subsitututed_node = load_xml("""
        <ns0:kunde xmlns:ns0="http://tests.python-zeep.org/b"
                       xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ns0:noun>Hello World</ns0:noun>
        </ns0:kunde>
    """)
    data1 = cust_elem.parse(original_node, schema)
    try:
        data2 = cust_elem.parse(subsitututed_node, schema)
        raise AssertionError("Should not have been able to parse that XML.")
    except XMLParseError as e:
        assert e.args[0] is not None, "Should have caught a populated XMLParseError"
