import pytest
from lxml import etree

from tests.utils import DummyTransport, load_xml
from zeep import exceptions, xsd
from zeep.xsd import Schema


def test_default_types():
    schema = xsd.Schema()
    xsd_string = schema.get_type('{http://www.w3.org/2001/XMLSchema}string')
    assert xsd_string == xsd.String()


def test_default_types_not_found():
    schema = xsd.Schema()
    with pytest.raises(exceptions.LookupError):
        schema.get_type('{http://www.w3.org/2001/XMLSchema}bar')


def test_default_elements():
    schema = xsd.Schema()
    xsd_schema = schema.get_element('{http://www.w3.org/2001/XMLSchema}schema')
    isinstance(xsd_schema, Schema)


def test_default_elements_not_found():
    schema = xsd.Schema()
    with pytest.raises(exceptions.LookupError):
        schema.get_element('{http://www.w3.org/2001/XMLSchema}bar')


def test_invalid_namespace_handling():
    schema = xsd.Schema()
    qname = '{http://tests.python-zeep.org/404}foo'

    with pytest.raises(exceptions.NamespaceError) as exc:
        schema.get_element(qname)
    assert qname in str(exc.value.message)

    with pytest.raises(exceptions.NamespaceError) as exc:
        schema.get_type(qname)
    assert qname in str(exc.value.message)

    with pytest.raises(exceptions.NamespaceError) as exc:
        schema.get_group(qname)
    assert qname in str(exc.value.message)

    with pytest.raises(exceptions.NamespaceError) as exc:
        schema.get_attribute(qname)
    assert qname in str(exc.value.message)

    with pytest.raises(exceptions.NamespaceError) as exc:
        schema.get_attribute_group(qname)
    assert qname in str(exc.value.message)


def test_invalid_localname_handling():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/"
            elementFormDefault="qualified">
        </xs:schema>
    """))

    qname = '{http://tests.python-zeep.org/}foo'
    namespace = 'http://tests.python-zeep.org/'
    localname = 'foo'

    with pytest.raises(exceptions.LookupError) as exc:
        schema.get_element(qname)
    assert namespace in str(exc.value.message)
    assert localname in str(exc.value.message)

    with pytest.raises(exceptions.LookupError) as exc:
        schema.get_type(qname)
    assert namespace in str(exc.value.message)
    assert localname in str(exc.value.message)

    with pytest.raises(exceptions.LookupError) as exc:
        schema.get_group(qname)
    assert namespace in str(exc.value.message)
    assert localname in str(exc.value.message)

    with pytest.raises(exceptions.LookupError) as exc:
        schema.get_attribute(qname)
    assert namespace in str(exc.value.message)
    assert localname in str(exc.value.message)

    with pytest.raises(exceptions.LookupError) as exc:
        schema.get_attribute_group(qname)
    assert namespace in str(exc.value.message)
    assert localname in str(exc.value.message)


def test_schema_repr_none():
    schema = xsd.Schema()
    assert repr(schema) == "<Schema()>"


def test_schema_repr_val():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/"
            elementFormDefault="qualified">
        </xs:schema>
    """))
    assert repr(schema) == "<Schema(location=None, tns='http://tests.python-zeep.org/')>"


def test_schema_doc_repr_val():
    schema = xsd.Schema(load_xml("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/"
            targetNamespace="http://tests.python-zeep.org/"
            elementFormDefault="qualified">
        </xs:schema>
    """))
    docs = schema._get_schema_documents('http://tests.python-zeep.org/')
    assert len(docs) == 1
    doc = docs[0]
    assert repr(doc) == "<SchemaDocument(location=None, tns='http://tests.python-zeep.org/', is_empty=True)>"


def test_multiple_extension():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">

            <xs:import
                schemaLocation="http://tests.python-zeep.org/b.xsd"
                namespace="http://tests.python-zeep.org/b"/>

            <xs:complexType name="type_a">
              <xs:complexContent>
                <xs:extension base="b:type_b"/>
              </xs:complexContent>
            </xs:complexType>
            <xs:element name="typetje" type="tns:type_a"/>

        </xs:schema>
    """.strip())

    node_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            targetNamespace="http://tests.python-zeep.org/b"
            xmlns:c="http://tests.python-zeep.org/c"
            elementFormDefault="qualified">

            <xs:import
                schemaLocation="http://tests.python-zeep.org/c.xsd"
                namespace="http://tests.python-zeep.org/c"/>

            <xs:complexType name="type_b">
              <xs:complexContent>
                <xs:extension base="c:type_c"/>
              </xs:complexContent>
            </xs:complexType>
        </xs:schema>
    """.strip())

    node_c = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/c"
            targetNamespace="http://tests.python-zeep.org/c"
            elementFormDefault="qualified">

            <xs:complexType name="type_c">
              <xs:complexContent>
                <xs:extension base="tns:type_d"/>
              </xs:complexContent>
            </xs:complexType>

            <xs:complexType name="type_d">
                <xs:attribute name="wat" type="xs:string" />
            </xs:complexType>
        </xs:schema>
    """.strip())
    etree.XMLSchema(node_c)

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/b.xsd', node_b)
    transport.bind('http://tests.python-zeep.org/c.xsd', node_c)

    schema = xsd.Schema(node_a, transport=transport)
    type_a = schema.get_type('ns0:type_a')
    type_a(wat='x')


def test_global_element_and_type():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">

            <xs:import
                schemaLocation="http://tests.python-zeep.org/b.xsd"
                namespace="http://tests.python-zeep.org/b"/>

            <xs:complexType name="refs">
              <xs:sequence>
                <xs:element ref="b:ref_elm"/>
              </xs:sequence>
              <xs:attribute ref="b:ref_attr"/>
            </xs:complexType>

        </xs:schema>
    """.strip())

    node_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            targetNamespace="http://tests.python-zeep.org/b"
            xmlns:c="http://tests.python-zeep.org/c"
            elementFormDefault="qualified">

            <xs:import
                schemaLocation="http://tests.python-zeep.org/c.xsd"
                namespace="http://tests.python-zeep.org/c"/>

            <xs:element name="ref_elm" type="xs:string"/>
            <xs:attribute name="ref_attr" type="xs:string"/>
        </xs:schema>
    """.strip())

    node_c = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/c"
            targetNamespace="http://tests.python-zeep.org/c"
            elementFormDefault="qualified">

            <xs:complexType name="type_a">
              <xs:sequence>
                <xs:element name="item_a" type="xs:string"/>
              </xs:sequence>
            </xs:complexType>
            <xs:element name="item" type="xs:string"/>
        </xs:schema>
    """.strip())
    etree.XMLSchema(node_c)

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/b.xsd', node_b)
    transport.bind('http://tests.python-zeep.org/c.xsd', node_c)

    schema = xsd.Schema(node_a, transport=transport)
    type_a = schema.get_type('{http://tests.python-zeep.org/c}type_a')

    type_a = schema.get_type('{http://tests.python-zeep.org/c}type_a')
    type_a(item_a='x')

    elm = schema.get_element('{http://tests.python-zeep.org/c}item')
    elm('x')

    elm = schema.get_type('{http://tests.python-zeep.org/a}refs')
    elm(ref_elm='foo', ref_attr='bar')


def test_cyclic_imports():
    schema_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">

            <xs:import
                schemaLocation="http://tests.python-zeep.org/b.xsd"
                namespace="http://tests.python-zeep.org/b"/>
        </xs:schema>
    """.strip())

    schema_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            targetNamespace="http://tests.python-zeep.org/b"
            xmlns:c="http://tests.python-zeep.org/c"
            elementFormDefault="qualified">

            <xs:import
                schemaLocation="http://tests.python-zeep.org/c.xsd"
                namespace="http://tests.python-zeep.org/c"/>
        </xs:schema>
    """.strip())

    schema_c = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/c"
            targetNamespace="http://tests.python-zeep.org/c"
            elementFormDefault="qualified">

            <xs:import
                schemaLocation="http://tests.python-zeep.org/a.xsd"
                namespace="http://tests.python-zeep.org/a"/>
        </xs:schema>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/a.xsd', schema_a)
    transport.bind('http://tests.python-zeep.org/b.xsd', schema_b)
    transport.bind('http://tests.python-zeep.org/c.xsd', schema_c)
    xsd.Schema(schema_a, transport=transport, location='http://tests.python-zeep.org/a.xsd')


def test_get_type_through_import():
    schema_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">

            <xs:import
                schemaLocation="http://tests.python-zeep.org/b.xsd"
                namespace="http://tests.python-zeep.org/b"/>
            <xs:element name="foo" type="b:bar"/>

        </xs:schema>
    """.strip())

    schema_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            targetNamespace="http://tests.python-zeep.org/b"
            xmlns:c="http://tests.python-zeep.org/c"
            elementFormDefault="qualified">

            <xs:complexType name="bar"/>

        </xs:schema>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/a.xsd', schema_a)
    transport.bind('http://tests.python-zeep.org/b.xsd', schema_b)
    xsd.Schema(schema_a, transport=transport)


def test_duplicate_target_namespace():
    schema_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            elementFormDefault="qualified">

            <xs:import
                schemaLocation="http://tests.python-zeep.org/b.xsd"
                namespace="http://tests.python-zeep.org/duplicate"/>
            <xs:import
                schemaLocation="http://tests.python-zeep.org/c.xsd"
                namespace="http://tests.python-zeep.org/duplicate"/>
        </xs:schema>
    """.strip())

    schema_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/duplicate"
            targetNamespace="http://tests.python-zeep.org/duplicate"
            elementFormDefault="qualified">
            <xsd:element name="elm-in-b" type="tns:item-c"/>
            <xsd:complexType name="item-c">
              <xsd:sequence>
                <xsd:element name="item-a" type="xsd:string"/>
                <xsd:element name="item-b" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>
        </xsd:schema>
    """.strip())

    schema_c = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/duplicate"
            targetNamespace="http://tests.python-zeep.org/duplicate"
            elementFormDefault="qualified">
            <xsd:element name="elm-in-c" type="tns:item-c"/>
            <xsd:complexType name="item-c">
              <xsd:sequence>
                <xsd:element name="item-a" type="xsd:string"/>
                <xsd:element name="item-b" type="xsd:string"/>
              </xsd:sequence>
            </xsd:complexType>

        </xsd:schema>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/a.xsd', schema_a)
    transport.bind('http://tests.python-zeep.org/b.xsd', schema_b)
    transport.bind('http://tests.python-zeep.org/c.xsd', schema_c)
    schema = xsd.Schema(schema_a, transport=transport)

    elm_b = schema.get_element('{http://tests.python-zeep.org/duplicate}elm-in-b')
    elm_c = schema.get_element('{http://tests.python-zeep.org/duplicate}elm-in-c')
    assert not isinstance(elm_b.type, xsd.UnresolvedType)
    assert not isinstance(elm_c.type, xsd.UnresolvedType)


def test_multiple_no_namespace():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            elementFormDefault="qualified">

          <xsd:import schemaLocation="http://tests.python-zeep.org/b.xsd"/>
          <xsd:import schemaLocation="http://tests.python-zeep.org/c.xsd"/>
        </xsd:schema>
    """.strip())

    node_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            elementFormDefault="qualified">
        </xsd:schema>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/b.xsd', node_b)
    transport.bind('http://tests.python-zeep.org/c.xsd', node_b)
    xsd.Schema(node_a, transport=transport)


def test_multiple_only_target_ns():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            elementFormDefault="qualified">

          <xsd:import schemaLocation="http://tests.python-zeep.org/b.xsd"/>
          <xsd:import schemaLocation="http://tests.python-zeep.org/c.xsd"/>
        </xsd:schema>
    """.strip())

    node_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            elementFormDefault="qualified"
            targetNamespace="http://tests.python-zeep.org/duplicate-ns">
        </xsd:schema>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/b.xsd', node_b)
    transport.bind('http://tests.python-zeep.org/c.xsd', node_b)
    xsd.Schema(node_a, transport=transport)


def test_schema_error_handling():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">

        </xs:schema>
    """.strip())
    transport = DummyTransport()
    schema = xsd.Schema(node_a, transport=transport)

    with pytest.raises(ValueError):
        schema.get_element('nonexisting:something')
    with pytest.raises(ValueError):
        schema.get_type('nonexisting:something')
    with pytest.raises(exceptions.NamespaceError):
        schema.get_element('{nonexisting}something')
    with pytest.raises(exceptions.NamespaceError):
        schema.get_type('{nonexisting}something')
    with pytest.raises(exceptions.LookupError):
        schema.get_element('ns0:something')
    with pytest.raises(exceptions.LookupError):
        schema.get_type('ns0:something')


def test_schema_import_xmlsoap():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">
          <xsd:import namespace="http://schemas.xmlsoap.org/soap/encoding/"/>
        </xsd:schema>
    """.strip())
    transport = DummyTransport()
    xsd.Schema(node_a, transport=transport)


def test_schema_import_unresolved():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">
          <xsd:import namespace="http://schemas.xmlsoap.org/soap/encoding/"/>
        </xsd:schema>
    """.strip())
    transport = DummyTransport()
    xsd.Schema(node_a, transport=transport)


def test_no_target_namespace():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            elementFormDefault="qualified">

          <xsd:import schemaLocation="http://tests.python-zeep.org/b.xsd"/>

          <xsd:element name="container">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element ref="bla"/>
              </xsd:sequence>
            </xsd:complexType>
          </xsd:element>

        </xsd:schema>
    """.strip())

    node_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xsd:schema
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            elementFormDefault="qualified">
            <xsd:element name="bla" type="xsd:string"/>
        </xsd:schema>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/b.xsd', node_b)
    xsd.Schema(node_a, transport=transport)


def test_include_recursion():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">

            <xs:import
                schemaLocation="http://tests.python-zeep.org/b.xsd"
                namespace="http://tests.python-zeep.org/b"/>

        </xs:schema>
    """.strip())

    node_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            targetNamespace="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">

            <xs:include schemaLocation="http://tests.python-zeep.org/c.xsd"/>
            <xs:element name="bar" type="xs:string"/>
        </xs:schema>
    """.strip())

    node_c = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            targetNamespace="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">

            <xs:include schemaLocation="http://tests.python-zeep.org/b.xsd"/>

            <xs:element name="foo" type="xs:string"/>
        </xs:schema>
    """.strip())

    transport = DummyTransport()
    transport.bind('http://tests.python-zeep.org/b.xsd', node_b)
    transport.bind('http://tests.python-zeep.org/c.xsd', node_c)

    schema = xsd.Schema(node_a, transport=transport)
    schema.get_element('{http://tests.python-zeep.org/b}foo')
    schema.get_element('{http://tests.python-zeep.org/b}bar')


def test_merge():
    node_a = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/a"
            targetNamespace="http://tests.python-zeep.org/a"
            xmlns:b="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">
          <xs:element name="foo" type="xs:string"/>
        </xs:schema>
    """.strip())

    node_b = etree.fromstring("""
        <?xml version="1.0"?>
        <xs:schema
            xmlns:xs="http://www.w3.org/2001/XMLSchema"
            xmlns:tns="http://tests.python-zeep.org/b"
            targetNamespace="http://tests.python-zeep.org/b"
            elementFormDefault="qualified">
          <xs:element name="foo" type="xs:int"/>
        </xs:schema>
    """.strip())

    schema_a = xsd.Schema(node_a)
    schema_b = xsd.Schema(node_b)
    schema_a.merge(schema_b)

    schema_a.get_element('{http://tests.python-zeep.org/a}foo')
    schema_a.get_element('{http://tests.python-zeep.org/b}foo')
