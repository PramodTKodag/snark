from django.conf import settings
from drf_spectacular.generators import SchemaGenerator


def test_every_operation_uses_a_documented_tag():
    schema = SchemaGenerator().get_schema(request=None, public=True)
    documented = {tag["name"] for tag in settings.SPECTACULAR_SETTINGS["TAGS"]}
    used = {
        tag
        for path_item in schema["paths"].values()
        for operation in path_item.values()
        for tag in operation.get("tags", [])
    }
    assert used <= documented, f"undocumented tags: {used - documented}"
    assert documented <= used, f"unused documented tags: {documented - used}"
