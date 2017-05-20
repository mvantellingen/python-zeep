import six

import operator


def generate(client):
    xsd_schema = client.wsdl.types
    wsdl = client.wsdl

    for service in wsdl.services.values():
        print(service.name)
        print('=' * len(service.name))
        print()
        print('.. py:class:: ServiceProxy')
        print()
        for port in service.ports.values():

            operations = sorted(
                port.binding._operations.values(),
                key=operator.attrgetter('name'))

            for operation in operations:
                _generate_operation_docstring(operation)


def _generate_operation_docstring(operation):
    print('    .. py:method:: %s()' % operation.name)
    print('')

    _get_type_parameters(operation.input.body.type)
    _get_output_parameters(operation.output.body.type)
    print('')
    print('')
    print('')


def _get_type_parameters(xsd_type):
    for name, elm in xsd_type.elements:
        print('       :param %s:' % name)
        print('       :type %s:' % (elm.type.name))


def _get_output_parameters(xsd_type):
    for name, elm in xsd_type.elements:
        print('       :return %s:' % name)
        print('       :rtype %s:' % (elm.type.name))
