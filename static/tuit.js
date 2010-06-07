

var tuit = {

    translations: {
	/*
	  Filled out by i18n script
	 */
    },
    
    dependency_id: 0,

    /*
      Perform all searches specified by data.

      This involves sending one ajax request per search, waiting for
      the result and displaying it.
     */
    search: function(data)
    {
	$.each(data, function(key, value) {
		var tbody = $('#results_' + value.id)[0];

		tbody.addText = function(text) {
		    var r=this.insertRow(this.rows.length);
		    var c = document.createElement('td');
		    c.innerHTML = text;
		    r.appendChild(c);
		};
		
		tbody.addSearchResult = function(name, description, url) {
		    var r=this.insertRow(this.rows.length);
		    var c = document.createElement('td');
		    var a = document.createElement('a');
		    a.innerHTML = name;
		    a.href=url;
		    c.appendChild(a);		    
		    r.appendChild(c);
		};

		$.getJSON(value.url, {'time':tuit.time()},
			  function (result, status) {
			      //alert(results.length);
			      //$('#results_' + value.id)[0].innerHTML = results;
			      var count = result.ResultSet.Result.length;
			      var number_shown = 0;
			      var show_max = 0;

			      
			      function showMore(event){
				  show_max += 20;

				  for (; number_shown<(count<show_max?count:show_max); number_shown++) {
				      var el = result.ResultSet.Result[number_shown];
				      tbody.addSearchResult(el.name, el.description, el.url);
				  }
				  if (number_shown >= count) {
				      $('#toggle_button_'+value.id).hide();
				  }

				  stripe();
			      }

			      showMore();
			      $('#search_message_'+value.id)[0].innerHTML = tuitSearchTotalMessage.replace("%s", result.ResultSet.totalResultsAvailable);

			      $('#toggle_button_'+value.id)[0].onclick=showMore;

			      /*			      $.each(result.ResultSet.Result, 
				     function (id, el) {
					 tbody.addSearchResult(el.name, el.description, el.url);
					 });*/
			      //
			      stripe();
			  });
	    });
    },

    setItemValue: function( field, value) {
	if(tinyMCE.editors[field]){
	    tinyMCE.editors[field].setContent(value); 
	}
	else {
	    var fld = $('#'+field);
	    if(fld && fld.length == 1) {
		fld[0].value = value;
	    } else {
		fld = $('#'+field+'_'+value);
		if(fld && fld.length > 0) {
		    fld[0].checked=true;
		}
		else {
		    /*
		      Give up, we can't find the field
		    */
		}
	    }
	}

    },

    quickChange: function(obj)
    {
	var idx = $('#quick')[0].value;
	if(idx === "") {
	    return;
	}
	
	$.each(quick_fill, function(key2, value2) {
		if( value2.id == idx ) {
		    $.each(value2.item, function(key, value) {
			    tuit.setItemValue(value.field, value.value);
			});
		};
	    });
    },

    localUrlRegexp: new RegExp("^[^:/]*://[^/]*"),
    dirRedirectRegexp: new RegExp("/(\\?|$)"),
    cleanupUrl: function(url)
    {
     return url.replace(this.localUrlRegexp, "").replace(this.dirRedirectRegexp, "$1");
    },
    getMainMenu: function ()
    {
       	var menu_target = $('.main_menu_target');

	if(menu_target.length) {
	    menu_target.replaceWith($.ajax({url: "/tuit/menu/", async: false}).responseText)
        }

       	var main_menu = $('.main_menu');
       	var breadcrumb_head = $('.breadcrumb a + a')[0];
        if (breadcrumb_head === undefined) 
	    breadcrumb_head = $('.breadcrumb a')[0];	

        if (breadcrumb_head === undefined) 
	    return;
	
	main_menu.children().each(function(i, li) {
 	    if (tuit.cleanupUrl($(li).find("a")[0].href) == tuit.cleanupUrl(breadcrumb_head.href))
	        $(li).addClass('active');
	});
    },

    init: function()
    {
        this.getMainMenu();
	$.each($('input'), function(key, value) {
		var type = value.getAttribute("type");
		if ( type  == "submit" || type == "button" || type == "reset")	
		    $(value).addClass("button");
		else if (type == "radio" || type == "checkbox" || type == "text" || type=="file") 
		    $(value).addClass(type);

	    } );
	tuit.setupForm();
	tuit.getComments();
    },

    setupForm: function()
    {

	if($('body').autocomplete) {
	    var usr_url = "/tuit/query/user_complete/";
	    var usr_url2 = "/tuit/query/user_complete/?contacts=1";
	    var dep_url = "/tuit/query/issue_complete/";
	    var kb_url = "/cgi-bin/foswiki/search/KB/?cover=autocomplete&type=literal&web=KB+IKB&scope=all";	
	    var ci_url = "/FreeCMDB/?controller=ciList&output=autocomplete";
	    
	    var uoptions_single = {
		matchContains: true,
		mustMatch: false,
		param: "query",
		format: "json"
	    };
	    var uoptions_multiple = {
		matchContains: true,
		multiple: true,
		multipleSeparator:"\n",
		mustMatch: false,
		multipleSeparator:"\n",
		param: "query",
		format: "json"
	    };
	    
	    var uoptions_multiple_free = {
		matchContains: true,
		multiple: true,
		multipleSeparator:"\n",
		mustMatch: false,
		multipleSeparator:"\n",
		param: "query",
		format: "json"
	    };
	    
	    var uoptions_single_free = {
		matchContains: true,
		mustMatch: false,
		param: "query",
		format: "json"
	    };
	    
	    var u = $('.user');
	    
	    u.filter('input').not('.contact').not('.free').autocomplete(usr_url, uoptions_single);
	    u.filter('input').filter('.contact').not('.free').autocomplete(usr_url2, uoptions_single);
	    
	    u.filter('input').not('.contact').filter('.free').autocomplete(usr_url, uoptions_single_free);
	    u.filter('input').filter('.contact').filter('.free').autocomplete(usr_url2, uoptions_single_free);
	    u.filter('textarea').not('.contact').not('.free').autocomplete(usr_url, uoptions_multiple);
	    u.filter('textarea').not('.contact').filter('.free').autocomplete(usr_url, uoptions_multiple_free);
	    u.filter('textarea').filter('.contact').not('.free').autocomplete(usr_url2, uoptions_multiple);
	    u.filter('textarea').filter('.contact').filter('.free').autocomplete(usr_url2, uoptions_multiple_free);
		
	    $('.depend').autocomplete(dep_url,
            {
		matchContains: true,
		multiple: true,
		multipleSeparator:"\n",
		mustMatch: true,
		param: "query",
		format: "json"
		});
	
	    $('.ci').autocomplete(ci_url,
            {
		matchContains: true,
		multiple: true,
		multipleSeparator:"\n",
		mustMatch: true
		});

	    $('.kb').autocomplete(kb_url,
            {
 	        matchContains: true,
		multiple: true,
		multipleSeparator:"\n",
		mustMatch: false,
		param: "search"
		});
	
	}

	$('.advanced_head').click(function() {
		$('.advanced').toggle();
		return false;
	    });
	$('.advanced').hide();
	
        $('#quick').bind("change", null, tuit.quickChange);

	$('#requester').bind('change',function(event){
		var uname = $('#requester')[0].value.split(' ');
		if (uname.length < 1)
		    return;
		    
		$.getJSON('/tuit/query/autofill/',
			  {
			      'field':   'requester',
			      'username': uname[0],
			      'time':     tuit.time()},
			  function(value) {
			      $.each(value,function(name, value) {
				      tuit.setItemValue( name, value);
				  });
			  });
	    });

	$('#assigned_to').bind('change',function(event){
		var uname = $('#assigned_to')[0].value.split(' ');
		if (uname.length < 1)
		    return;
		    
		$.getJSON('/tuit/query/autofill/',
			  {
			      'field':   'assigned_to',
			      'value': uname[0],
			      'time':     tuit.time()},
			  function(value) {
			      $.each(value,function(name, value) {
				      tuit.setItemValue( name, value);
				  });
			  });
	    });
	
	if( window.field_fill != undefined) {
	    $.each(field_fill, function(key, value) {
		    $('#' + value).bind('change', function(event) {
			    //			alert();
			    var nam = event.target.name;
			    var val = event.target.value;
			    
			    $.getJSON('/tuit/query/autofill/',
				      {
					  'field':   nam,
					      'value': val,
					      'time':     tuit.time()},
				      function(value) {
					  $.each(value,function(name, value) {
						  tuit.setItemValue( value.field, value.value);
					      });
				      });
			});
		    		    
		});
	}
    },
	
    getComments: function() {
	var comment_target = $('.comment_target');
	if(comment_target.length) {
	    comment_target=comment_target[0];

	    function createItem(wrap){
		var res = document.createElement('li');
		res.className = 'tuit_comment';
		comment_target.appendChild(res);
		if (wrap != null) {
		    var res2 = document.createElement(wrap);
		    res.appendChild(res2);
		    return res2;
		}
		return res;
	    }


	    $.getJSON('/tuit/comment/get/',{'url':window.location.pathname},
		      function (data, status) {
			  if (data === false) {
			      return;
			  }
			  $('.tuit_comment').remove();
			  var title = createItem('h2');
			  $(title).text(_('Comments') + ':');
			  if(data.length > 0) {
			      $.each(data, function(key, value) {
				      var header = createItem('em');
				      var body = createItem();
				      $(header).text(value['username'] + "("+value['creation_time']+"):");
				      $(body).text(value['text']);
				  });
			  }
			  else {
			      var header = createItem();
			      $(header).text('('+ _('No comments posted yet')+')');
			  }
			  var form = createItem();
			  $(form).html('<input name="tuit_comment" id="tuit_comment_input" size="16"/> <button id="tuit_comment_button" type="button" onclick="javascript:tuit.addComment();">' +_('Send')+'</button>');
			  $('#tuit_comment_input').bind('keypress', function (event) {
				  if((event.keyCode || event.which) == 13) {
				      tuit.addComment();
				      return false;
				  }
				  return true;
			      });
			  
		      });
	}
    },

    addComment: function() {
	var comment = $('#tuit_comment_input')[0];
	if (comment.value == '' ) {
	    return;
	}
	$.getJSON('/tuit/comment/set/',{'url':window.location.pathname,
					'comment':comment.value},
		      function (data, status) {
			  if (data) {
			      /*
				Reload comments. Yay!
			      */
			      tuit.getComments();
			  }
		      });
    },

    insertKbArticle: function(){
	var articleName = tuit.strip($('#kb_insert')[0].value);
	var url = '/cgi-bin/foswiki/view/'+escape(articleName)
	if (articleName == "" || articleName.split('/').length < 2) {
	    return;
	}
	$.get(url, {'cover':'text','time':tuit.time()},
	      function (result, status) {
		  if(tuit.strip(result)  != "") { 
		      tinyMCE.editors['comment'].setContent(result); 
		      $('#kb_preview').hide(200);
		  }
	      });
    },

    previewKbArticle: function(){
	var articleName = tuit.strip($('#kb_insert')[0].value);
	var url = '/cgi-bin/foswiki/view/'+escape(articleName);
	if (articleName == "" || articleName.split('/').length< 2) {
	    return;
	}	
	$.get(url, {'cover':'text','time':tuit.time()},
	      function (result, status) {
		  if(tuit.strip(result)  != "") { 
		      $('#kb_preview_content')[0].innerHTML=result;
		      $('#kb_preview').show(200);
		  }
		  
	      });
    },

    previewKbArticleHide: function(){
	$('#kb_preview').hide(200);
    },

    createKbArticle: function(contentId){
	var content = $('#'+contentId)[0].innerHTML;
	$('#kb_content')[0].value = content;
	$('#kb_popup').show(50);
	//$('#kb_form')[0].submit();
    },

    /*
      Show a debug message in the main browser window
     */
    debug: function(str){
	$('#debug')[0].innerHTML += str + "<br/>";
    },

    /*
      Check the email boxes specified by lst, uncheck all other email boxes.
     */
    checkEmailCheckboxes: function(lst)
    {
	$('.email_checkbox').attr('checked',false);
	
	for(var i=0; i<lst.length; i++) 
	{
	    var el = $('#'+lst[i]+"_email")[0];
	    el.checked=true;
	}
    },
    
    /*
      Utility function. Strip whitespace from both ends of string
     */
    strip: function(str)
    {
	return str.replace(/^\s+|\s+$/g,"");
    },

    /*
      Go over the content section of the document and make a TOC, insert it at the specified point
    */
    makeTOC: function(location) {
	var am = $(location)[0];
	function addItem(text, anchor, tag){
	    var li = document.createElement('li');
	    var a = document.createElement('a');
	    a.innerHTML = text;
	    a.href='#' + anchor;
	    li.className = "toc_" + tag.toLowerCase();
	    li.appendChild(a);
	    am.appendChild(li);
	}
	$('.help h1, .help h2').each(function(idx , el){
		if (el.innerHTML && el.innerHTML != "") { 
		    if(el.childNodes.length == 1 && el.childNodes[0].name != null) {
			addItem(el.childNodes[0].innerHTML,el.childNodes[0].name,el.tagName);
		    }
		    else {
			addItem(el.innerHTML,"",el.tagName);
		    }
		}
	    });
    },

    time: function()
    {
	return "" + (new Date()).getTime();
	
    },

    fileCount: 0,

    addFileWidget: function() {
	var tbody = $('#file')[0];
	var tr = document.createElement('tr');
	var td1 = document.createElement('td');
	var td2 = document.createElement('td');
	var input = document.createElement('input');

	tr.appendChild(td1);
	
	input.type='file';
	input.name='file_' + tuit.fileCount++;
	input.className = "file";

	td2.appendChild(input);
	tr.appendChild(td2);
	tbody.appendChild(tr);
	stripe();

	function createItem(wrap){
	    res.className = 'tuit_comment';
	    comment_target.appendChild(res);
	    if (wrap != null) {
		var res2 = document.createElement(wrap);
		res.appendChild(res2);
		return res2;
	    }
	    return res;
	}
	
	
    },
    
    setTicketType: function(type_id, type_name){
	$(".type_selector_label").removeClass("selected");
	$("#type_"+type_id+"_selector_label").addClass("selected");
	$.get('/tuit/ticket/new/', {'type_id':type_id,'partial':'1'},	
	      function (result, status) {
	       $('#ticket_form').html(result);
		  
		  var d = $('#ticket_form')[0].getElementsByTagName("script");
		  var t = d.length
		  for (var x=0;x<t;x++){
		      var newScript = document.createElement('script');
		      newScript.type = "text/javascript";
		      newScript.text = d[x].text;
		      document.getElementById('ticket_form').appendChild (newScript);
		  }
		  tuit.setupForm();
		  tinyMCE.init({
			  mode : "specific_textareas",
			      editor_selector : "rich_edit",
			      theme : "advanced",
			      theme_advanced_buttons1 : "bold,italic,underline,strikethrough,separator,justifyleft,justifycenter,justifyright,justifyfull,separator,bullist,numlist,separator,undo,redo,link,unlink",
			      theme_advanced_buttons2 : "",
			      theme_advanced_buttons3 : "",
			      theme_advanced_toolbar_location : "top",
			      theme_advanced_toolbar_align : "left"
			      });
	      }
	      );
	//	$('.widget_header h2')[0].innerHTML = type_name
    },
    
    addDependency: function(){
	var dependency_type_field = $('#p_depend_type')[0];
	var dependency_field = $('#p_depend')[0];
	if(dependency_field.value == "")
	    return;
	
	var id=0;
	while($("#dependency_" + id).length != 0)
	    id++;

	var list = $('#dependencies_list')[0];
	var li = document.createElement('li');
	li.id="dependency_" + id;
	li.appendChild(document.createTextNode(dependency_type_field.options[dependency_type_field.selectedIndex].text));
	li.appendChild(document.createTextNode(": "));
	li.appendChild(document.createTextNode(dependency_field.value+ " "));
	var dep_type = document.createElement('input');
	dep_type.type='hidden';
	dep_type.name='dependency_' + id + '_type';
	dep_type.value=dependency_type_field.value;
	li.appendChild(dep_type);

	var dep_id = document.createElement('input');
	dep_id.type='hidden';
	dep_id.name='dependency_' + id + '_id';
	dep_id.value=dependency_field.value.split(' ')[0];
	li.appendChild(dep_id);
	
	var b=document.createElement('button');
	b.className='dependency_remove';
	b.type='button';
	
	b.onclick=function(){$('#dependency_' + id).remove();};	
	b.appendChild(document.createTextNode("-"));
	li.appendChild(b);

	list.appendChild(li);
    }
};

$(document).ready(function(){
	tuit.init();
});

$(window).load(function(){
	/*
	  This needs to wait until 18n.js has loaded, so we don't run
	  it until window.load is triggered.
	 */
	if($('body').datePicker) {
	    $('.date_picker').datePicker({"startDate":"01.01.2000"});
	}
    });


function _ (input) {
    return (input in tuit.translations)?tuit.translations[input]:input;
}
