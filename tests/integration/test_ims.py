import os
import uuid

import requests_mock

import zeep


def read_file(file_name, folder="wsdl_ims"):
    file = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder, file_name)
    with open(file) as f:
        return f.read()


def test_find_customer():
    with requests_mock.mock() as m:
        m.get("http://example.com/inventory?wsdl", text=read_file("inventory.wsdl"))
        m.post(
            "http://example.com/Inventory/inventoryhttps",
            text=read_file("find_customer_by_name_response.xml", "mock_ims"),
        )
        # set strict to True -> then data will be available in _raw_elements
        client = zeep.Client(
            "http://example.com/inventory?wsdl",
            settings=zeep.settings.Settings(strict=False),
        )
        filter_fields = [
            {
                "FilterField": {
                    "Name": "Name",
                    "SelectedOperator": "OperationEquals",
                    "Value": "SURFNET",
                }
            }
        ]
        ims_filter = {"Filters": filter_fields}
        pager = {
            "StartElement": 0,
            "Descending": False,
            "NumberOfElements": 10,
            "OrderByProperty": None,
        }

        result = client.service.GetAllCustomersFiltered(
            pager=pager, filter=ims_filter, sessionToken=str(uuid.uuid4())
        )

        assert result.GetAllCustomersFilteredResult.Customer[0].Id == 2644557
        assert result.GetAllCustomersFilteredResult.Customer[0].Name == "SURFNET"
