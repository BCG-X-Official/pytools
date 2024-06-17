import logging

from pytools.text import camel_case_to_snake_case

log = logging.getLogger(__name__)


def test_string_conversion() -> None:
    camel_snake_conversions = [
        ("", ""),
        ("RandomForestDF", "random_forest_df"),
        ("!@#$%", "!@#$%"),
        ("HTTPRequest", "http_request"),
        ("MyHTTPRequest", "my_http_request"),
        ("My_HTTP_Request", "my_http_request"),
        ("My__HTTP__Request", "my__http__request"),
        ("My_HT_TP_Request", "my_ht_tp_request"),
        ("My___HT___TP___Request", "my___ht___tp___request"),
        ("MyHTTPRequest123", "my_http_request123"),
        ("MyHT123TPRequest123", "my_ht_123_tp_request123"),
        ("MyHT$!3&TPRequest$^&7&", "my_ht_$!_3_&_tp_request_$^&_7_&"),
    ]

    for camel, snake in camel_snake_conversions:
        assert camel_case_to_snake_case(camel) == snake
