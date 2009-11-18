

var tuit = {
    
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

		$.getJSON(value.url,
			  function (result, status) {
			      //alert(results.length);
			      //$('#results_' + value.id)[0].innerHTML = results;
			      var count = result.ResultSet.Result.length;
			      var number_shown = 0;
			      var show_max = 0;

			      
			      function showMore(event){
				  show_max += 10;

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

    init: function()
    {
	usr_url = "/tuit/query/user_complete/";
	usr_url2 = "/tuit/query/user_complete/?contacts=1";
	dep_url = "/tuit/query/issue_complete/";
	kb_url = "/cgi-bin/foswiki/search/KB/?skin=autocomplete&type=literal"	
	ci_url = "/FreeCMDB/?controller=ciList&output=autocomplete"

	var uoptions_single = {
	    matchContains: true,
	    mustMatch: true,
	    param: "query",
	    multipleSeparator:"\n",
	    format: "json"
	};
	var uoptions_multiple = {
	  matchContains: true,
	  multiple: true,
	  multipleSeparator:"\n",
	  mustMatch: true,
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

	var u = $('.user');

	u.filter('input').not('.contact').autocomplete(usr_url, uoptions_single);
	u.filter('input').filter('.contact').autocomplete(usr_url2, uoptions_single);
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
	
	
	var tjolahopp = null;
		
	$('.advanced_head').click(function() {
		$('.advanced').toggle();
		return false;
	    });
	$('.advanced').hide();
	
	var quickChange = function(obj)
	{
	    var idx = $('#quick')[0].value;
	    if(idx == "")
		return;
	    
	    $.each(quick_fill,function(key2, value2)
	{
	    if( value2.id == idx ) {
		$.each(value2.item,function(key, value)
		       {
			   if(tinyMCE.editors[value.field]){
			       tinyMCE.editors[value.field].setContent(value.value); 
			   }
			   else {
			       var fld = $('#'+value.field);
			       if(fld && fld.length == 1) {
				   fld[0].value = value.value;
			       } else {
				   fld = $('#'+value.field+value.value);
				   if(fld) {
				       fld[0].checked=true;
				   }
			       }
			   }
		       });
	    };
	    return;
	});
	};
	
        $('#quick').bind("change", null, quickChange);
	
        $(".contact input").attr("disabled","disabled");
        $(".contact input").addClass("disabled");
	$('.date_picker').datePicker({"startDate":"01.01.2000"});

	$('#requester').bind('change',function(event){
		var uname = $('#requester')[0].value.split(' ');
		if (uname.length < 1)
		    return
		    
		$.getJSON('/tuit/query/user_location/',{'username':uname[0]},
			  function(value) {
			      $.each(value,function(name, value) {
				      $('#' + name)[0].value = value;
				  });
			  });

	    });
	    
	
    },

    insertKbArticle: function(){
	var articleName = tuit.strip($('#kb_insert')[0].value);
	var url = 'http://fhi-dev.freecode.no/cgi-bin/foswiki/view/KB/'+escape(articleName)+'?skin=text';
	$.get(url,
	      function (result, status) {
		  tinyMCE.editors['comment'].setContent(result); 
		  $('#kb_preview').hide(200);
	      });
    },

    previewKbArticle: function(){
	var articleName = tuit.strip($('#kb_insert')[0].value);
	
	var url = 'http://fhi-dev.freecode.no/cgi-bin/foswiki/view/KB/'+escape(articleName)+'?skin=text';
	
	$.get(url,
	      function (result, status) {
		  $('#kb_preview_content')[0].innerHTML=result;
		  $('#kb_preview').show(200);
		  
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

    debug: function(str){
	$('#debug')[0].innerHTML += str + "<br/>";
    },

    checkEmailCheckboxes: function(lst)
    {
	$('.email_checkbox').attr('checked',false);
	
	for(var i=0; i<lst.length; i++) 
	{
	    var el = $('#'+lst[i]+"_email")[0];
	    el.checked=true;
	}
    },
    
    strip: function(str)
    {
	return str.replace(/^\s+|\s+$/g,"");
    }
}

$(document).ready(function(){
	tuit.init();
});

