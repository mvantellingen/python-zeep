from lxml import etree

from zeep import xsd


def test_compound_value_xml():

    class UserValue(object):
        pass

    class OrderValue(object):
        pass

    class User(xsd.ComplexType):
        __metadata__ = {
            'fields': [
                xsd.Element('first_name', xsd.String()),
                xsd.Element('last_name', xsd.String()),
                xsd.Element('age', xsd.Integer()),
                xsd.Attribute('id', xsd.Integer()),
            ],
        }

    class Order(xsd.ComplexType):
        __metadata__ = {
            'fields': [
                xsd.Element('amount', xsd.Integer()),
                xsd.Element('user', User()),
            ]
        }

    value = UserValue()
    value.first_name = 'Foo'
    value.last_name = 'Bar'
    value.age = 10
    value.id = 12

    user_type = User()
    elm = xsd.Element(name='user', type_=User())

    node = etree.Element('root')
    elm.render(node, value)
    print etree.tostring(node, pretty_print=True)

    order = OrderValue()
    order.user = value
    order.amount = 1234

    order_type = Order()
    elm = xsd.Element(name='user', type_=Order())

    node = etree.Element('root')
    elm.render(node, order)
    print etree.tostring(node, pretty_print=True)
