from lxml import etree

from zeep import xsd


def test_signature_complex_type_choice():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Choice([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.String()),
            ])
        ))
    assert custom_type.signature() == '({item_1: xsd:string} | {item_2: xsd:string})'


def test_signature_complex_type_choice_sequence():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Choice([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Sequence([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_2_1'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_2_2'),
                        xsd.String()),
                ])
            ])
        ))
    assert custom_type.signature() == (
        '({item_1: xsd:string} | {item_2_1: xsd:string, item_2_2: xsd:string})')


def test_signature_nested_sequences():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.String()),
                xsd.Sequence([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_3'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_4'),
                        xsd.String()),
                ]),
                xsd.Choice([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_5'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_6'),
                        xsd.String()),
                    xsd.Sequence([
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_5'),
                            xsd.String()),
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_6'),
                            xsd.String()),
                    ])
                ])
            ])
        ))

    assert custom_type.signature() == (
        'item_1: xsd:string, item_2: xsd:string, item_3: xsd:string, item_4: xsd:string, _value_1: ({item_5: xsd:string} | {item_6: xsd:string} | {item_5: xsd:string, item_6: xsd:string})'  # noqa
    )


def test_signature_nested_sequences_multiple():
    custom_type = xsd.Element(
        etree.QName('http://tests.python-zeep.org/', 'authentication'),
        xsd.ComplexType(
            xsd.Sequence([
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_1'),
                    xsd.String()),
                xsd.Element(
                    etree.QName('http://tests.python-zeep.org/', 'item_2'),
                    xsd.String()),
                xsd.Sequence([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_3'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_4'),
                        xsd.String()),
                ]),
                xsd.Choice([
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_5'),
                        xsd.String()),
                    xsd.Element(
                        etree.QName('http://tests.python-zeep.org/', 'item_6'),
                        xsd.String()),
                    xsd.Sequence([
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_5'),
                            xsd.String()),
                        xsd.Element(
                            etree.QName('http://tests.python-zeep.org/', 'item_6'),
                            xsd.String()),
                    ])
                ], min_occurs=2, max_occurs=3)
            ])
        ))

    assert custom_type.signature() == (
        'item_1: xsd:string, item_2: xsd:string, item_3: xsd:string, item_4: xsd:string, _value_1: ({item_5: xsd:string} | {item_6: xsd:string} | {item_5: xsd:string, item_6: xsd:string})[]'  # noqa
    )
