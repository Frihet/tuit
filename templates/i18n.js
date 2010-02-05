{% load tuit_extras %}
$(document).ready(function(){
	if(!('dpText' in $)) $.dpText = {};
{% for foo in strings.items %}
	{{ foo.0 }} = {{ foo.1|to_json }};
{% endfor %}
    });