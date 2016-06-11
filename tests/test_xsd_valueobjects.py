import six

from zeep import xsd
from zeep.xsd import valueobjects


def test_simple_args():
    fields = [
        ('item_1', xsd.Element('item_1', xsd.String())),
        ('item_2', xsd.Element('item_2', xsd.String()))
    ]
    args = tuple(['value-1', 'value-2'])
    kwargs = {}
    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        'item_1': 'value-1',
        'item_2': 'value-2',
    }


def test_simple_args_too_many():
    fields = [
        ('item_1', xsd.Element('item_1', xsd.String())),
        ('item_2', xsd.Element('item_2', xsd.String()))
    ]
    args = tuple(['value-1', 'value-2', 'value-3'])
    kwargs = {}

    try:
        valueobjects._process_signature(fields, args, kwargs)
    except TypeError as exc:
        assert six.text_type(exc) == (
            '__init__() takes at most 2 positional arguments (3 given)')
    else:
        assert False, "TypeError not raised"


def test_simple_args_too_few():
    fields = [
        ('item_1', xsd.Element('item_1', xsd.String())),
        ('item_2', xsd.Element('item_2', xsd.String()))
    ]
    args = tuple(['value-1'])
    kwargs = {}
    valueobjects._process_signature(fields, args, kwargs)


def test_simple_kwargs():
    fields = [
        ('item_1', xsd.Element('item_1', xsd.String())),
        ('item_2', xsd.Element('item_2', xsd.String()))
    ]
    args = tuple([])
    kwargs = {'item_1': 'value-1', 'item_2': 'value-2'}
    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        'item_1': 'value-1',
        'item_2': 'value-2',
    }


def test_simple_mixed():
    fields = [
        ('item_1', xsd.Element('item_1', xsd.String())),
        ('item_2', xsd.Element('item_2', xsd.String()))
    ]
    args = tuple(['value-1'])
    kwargs = {'item_2': 'value-2'}
    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        'item_1': 'value-1',
        'item_2': 'value-2',
    }


def test_choice():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Element('item_1', xsd.String()),
            xsd.Element('item_2', xsd.String())
        ]))
    ]
    args = tuple([])
    kwargs = {'item_2': 'value-2'}
    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        '_choice_1': valueobjects.ChoiceItem(1, {'item_2': 'value-2'})
    }


def test_choice_max_occurs_simple_interface():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Element('item_1', xsd.String()),
            xsd.Element('item_2', xsd.String())
        ], max_occurs=2))
    ]
    args = tuple([])
    kwargs = {
        'item_1': 'foo',
        'item_2': 'bar',
    }
    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        '_choice_1': [
            valueobjects.ChoiceItem(0, {'item_1': 'foo'}),
            valueobjects.ChoiceItem(1, {'item_2': 'bar'}),
        ]
    }


def test_choice_max_occurs():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Element('item_1', xsd.String()),
            xsd.Element('item_2', xsd.String())
        ], max_occurs=3))
    ]
    args = tuple([])
    kwargs = {
        '_choice_1': [
            {'item_1': 'foo'}, {'item_2': 'bar'}, {'item_1': 'bla'}
        ]
    }
    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        '_choice_1': [
            valueobjects.ChoiceItem(0, {'item_1': 'foo'}),
            valueobjects.ChoiceItem(1, {'item_2': 'bar'}),
            valueobjects.ChoiceItem(0, {'item_1': 'bla'}),
        ]
    }


def test_choice_max_occurs_on_choice():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Element('item_1', xsd.String(), max_occurs=2),
            xsd.Element('item_2', xsd.String())
        ], max_occurs=2))
    ]
    args = tuple([])
    kwargs = {
        '_choice_1': [
            {'item_1': ['foo', 'bar']},
            {'item_2': 'bla'},
        ]
    }
    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        '_choice_1': [
            valueobjects.ChoiceItem(0, {'item_1': ['foo', 'bar']}),
            valueobjects.ChoiceItem(1, {'item_2': 'bla'})
        ]
    }


def test_choice_mixed():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Element('item_1', xsd.String()),
            xsd.Element('item_2', xsd.String()),
        ])),
        ('item_2', xsd.Element('item_2', xsd.String()))
    ]
    args = tuple([])
    kwargs = {'item_1': 'value-1', 'item_2': 'value-2'}
    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        'item_2': 'value-2',
        '_choice_1': valueobjects.ChoiceItem(0, {'item_1': 'value-1'})
    }


def test_choice_sequences_simple():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Sequence([
                xsd.Element('item_1', xsd.String()),
                xsd.Element('item_2', xsd.String())
            ]),
            xsd.Sequence([
                xsd.Element('item_3', xsd.String()),
                xsd.Element('item_4', xsd.String())
            ]),
        ])),
    ]
    args = tuple([])
    kwargs = {'item_1': 'value-1', 'item_2': 'value-2'}
    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        '_choice_1': valueobjects.ChoiceItem(0, {
            'item_1': 'value-1', 'item_2': 'value-2'
        })
    }


def test_choice_sequences_no_match():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Sequence([
                xsd.Element('item_1', xsd.String()),
                xsd.Element('item_2', xsd.String())
            ]),
            xsd.Sequence([
                xsd.Element('item_3', xsd.String()),
                xsd.Element('item_4', xsd.String())
            ]),
        ])),
    ]
    args = tuple([])
    kwargs = {'item_1': 'value-1', 'item_3': 'value-3'}

    try:
        valueobjects._process_signature(fields, args, kwargs)
    except TypeError as exc:
        assert six.text_type(exc) == (
            "No complete xsd:Choice '_choice_1'.\n" +
            "The signature is: _choice_1: {item_1: xsd:string, item_2: xsd:string} " +
            "| {item_3: xsd:string, item_4: xsd:string}")
    else:
        assert False, "TypeError not raised"


def test_choice_sequences_no_match_nested():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Sequence([
                xsd.Element('item_1', xsd.String()),
                xsd.Element('item_2', xsd.String())
            ]),
        ])),
    ]
    args = tuple([])
    kwargs = {'_choice_1': {'item_1': 'value-1'}}
    try:
        valueobjects._process_signature(fields, args, kwargs)
    except TypeError as exc:
        assert six.text_type(exc) == (
            "No complete xsd:Sequence found for the xsd:Choice '_choice_1'.\n" +
            "The signature is: _choice_1: {item_1: xsd:string, item_2: xsd:string}")
    else:
        assert False, "TypeError not raised"


def test_choice_sequences_optional_elms():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Sequence([
                xsd.Element('item_1', xsd.String()),
                xsd.Element('item_2', xsd.String(), min_occurs=0)
            ]),
            xsd.Sequence([
                xsd.Element('item_1', xsd.String()),
                xsd.Element('item_2', xsd.String()),
                xsd.Element('item_3', xsd.String())
            ]),
        ])),
    ]
    args = tuple([])
    kwargs = {'item_1': 'value-1'}
    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        '_choice_1': valueobjects.ChoiceItem(
            0, {'item_1': 'value-1', 'item_2': None})
    }


def test_choice_sequences_max_occur():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Sequence([
                xsd.Element('item_1', xsd.String()),
                xsd.Element('item_2', xsd.String())
            ]),
            xsd.Sequence([
                xsd.Element('item_2', xsd.String()),
                xsd.Element('item_3', xsd.String()),
            ]),
        ], max_occurs=2)),
    ]
    args = tuple([])
    kwargs = {
        '_choice_1': [
            {'item_1': 'value-1', 'item_2': 'value-2'},
            {'item_2': 'value-2', 'item_3': 'value-3'},
        ]
    }

    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        '_choice_1': [
            valueobjects.ChoiceItem(0, {'item_1': 'value-1', 'item_2': 'value-2'}),
            valueobjects.ChoiceItem(1, {'item_2': 'value-2', 'item_3': 'value-3'}),
        ]
    }


def test_choice_sequences_init_dict():
    fields = [
        ('_choice_1', xsd.Choice([
            xsd.Sequence([
                xsd.Element('item_1', xsd.String()),
                xsd.Element('item_2', xsd.String())
            ]),
            xsd.Sequence([
                xsd.Element('item_2', xsd.String()),
                xsd.Element('item_3', xsd.String()),
            ]),
        ], max_occurs=2)),
    ]
    args = tuple([])
    kwargs = {
        '_choice_1': {'item_1': 'value-1', 'item_2': 'value-2'},
    }

    result = valueobjects._process_signature(fields, args, kwargs)
    assert result == {
        '_choice_1': [
            valueobjects.ChoiceItem(0, {'item_1': 'value-1', 'item_2': 'value-2'})
        ]
    }
