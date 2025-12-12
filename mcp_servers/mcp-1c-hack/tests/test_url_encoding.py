from odata_tool.url_builder import ODataUrlBuilder


def test_cyrillic_in_filter():
    builder = ODataUrlBuilder()
    url = builder.build(
        "http://server/base",
        "Catalog_Номенклатура",
        {"$filter": "Наименование eq 'Тест'", "$top": 10},
    )
    assert "Catalog_%D0%9D%D0%BE%D0%BC%D0%B5%D0%BD%D0%BA%D0%BB%D0%B0%D1%82%D1%83%D1%80%D0%B0" in url
    assert "$top=10" in url
    assert "%D0%A2%D0%B5%D1%81%D1%82" in url  # encoded Cyrillic
