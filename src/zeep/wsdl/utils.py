from lxml import etree


def etree_to_string(node):
    return etree.tostring(
        node, pretty_print=True, xml_declaration=True, encoding='utf-8')


def combine_schemas(schema_nodes, location, parser_context):
    """Combine multiple xsd:schema elements in one schema

    A wsdl can contain multiple schema nodes. These can import each other
    by simply referencing them by the namespace. To handle this in a way
    that lxml schema can also handle it we create a new container schema
    which imports the other schemas.  Since imports are non-transitive we
    need to copy the schema imports the newyl created container schema.

    """
    # Merge schema's which have no targetNamespace
    empty_schemas = [
        node for node in schema_nodes if node.get('targetNamespace') is None
    ]
    if len(empty_schemas) > 1:
        for schema_node in empty_schemas[1:]:
            for node in schema_node.getchildren():
                empty_schemas[0].append(node)
            schema_nodes.remove(schema_node)

    if len(schema_nodes) == 1:
        return schema_nodes[0]

    schema_ns = {}
    for i, schema_node in enumerate(schema_nodes):
        ns = schema_node.get('targetNamespace')
        int_name = schema_ns[ns] = 'intschema:xsd%d' % i
        parser_context.schema_nodes.add(schema_ns[ns], schema_node)
        parser_context.schema_locations[int_name] = location

    # Create namespace mapping (namespace -> internal location)
    schema_ns = {}
    for i, schema_node in enumerate(schema_nodes):
        ns = schema_node.get('targetNamespace')
        int_name = schema_ns[ns] = 'intschema:xsd%d' % i
        parser_context.schema_nodes.add(schema_ns[ns], schema_node)
        parser_context.schema_locations[int_name] = location

    # Only handle the import statements from the 2001 xsd's for now
    import_tag = '{http://www.w3.org/2001/XMLSchema}import'

    # Create a new schema node with xsd:import statements for all
    # schema's listed here.
    # <xsd:schema targetNamespace="http://www.python-zeep.org/Imports">
    container = etree.Element(
        '{http://www.w3.org/2001/XMLSchema}schema',
        targetNamespace='http://www.python-zeep.org/Imports')

    for i, schema_node in enumerate(schema_nodes):

        # Create a new xsd:import element to import the schema
        # <xsd:import schemaLocation="intschema:xsdX" targetNamespace="">
        import_node = etree.Element(
            import_tag, schemaLocation='intschema:xsd%d' % i)

        if schema_node.get('targetNamespace'):
            import_node.set('namespace', schema_node.get('targetNamespace'))
        container.append(import_node)

        # Update the xsd:import statements in the schema to add a schema
        for import_node in schema_node.findall(import_tag):
            location = import_node.get('schemaLocation')
            namespace = import_node.get('namespace')
            if not location and namespace in schema_ns:
                import_node.set('schemaLocation', schema_ns[namespace])

    return container
