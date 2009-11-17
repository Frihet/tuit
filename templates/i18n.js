{% load tuit_extras %}
{% for foo in strings.items %}
{{ foo.0 }} = {{ foo.1|to_json }};
{% endfor %}