
from tests.utils import load_xml
from zeep import xsd


def test_complex_type_element_substitution():
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
    """))
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
