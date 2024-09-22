var warning_confirmed = false;

$(document).ready(function(){
    $( "#failed-submit-dialog" ).dialog({
    	dialogClass: "no-close",
  		modal: true,
  		autoOpen: false,
    	buttons: [
    		{
    		text: "OK",
    		click: function(){
    			warning_confirmed = true;
    			$(this).dialog("close");
    		}
    		}
    	]
    })

    $("#required-finished-dialog").dialog({
    	dialogClass: "no-close",
    	modal: true,
    	autoOpen: true,
    	buttons: [
    	{
    		text: "OK",
    		click: function(){
    			$(this).dialog("close");
    		}
    	}
    	]
    })

    $('input[type="radio"]').change(function(){
    	if ($(this).is(':checked')){
    	  //AJAX back the data
    	  to_report = {}
    	  to_report[$(this).attr('name')] = $(this).val()
    	  report(to_report)
    	}
  	});

    $('textarea').blur(function(){
    	if ($(this).val() != ""){
    		to_report = {}
    		to_report[$(this).attr('name')] = $(this).val()
    		report(to_report)
    	}
    });

	$("form").submit(function(){
		var temp=true;
		$(".radio-tr").each(function(){
			if($(this).find("input:checked").length == 0){
				temp = false;
				return false;
			}
		});
		if(!temp){
			$("#failed-submit-dialog").dialog('open');
			return false;
		}

		if ($("input[name='next_question']").length != 0){
			return true;
		}

	    if ($('#question_select option:selected').next().next().length > 0){
			$('#question_select option:selected').prop('selected', false).next().next().prop('selected', true);
    	} else {
    		$('#question_select option').prop('selected', false).first().prop('selected', true);
    	}
    	var next_question = $("<input type='hidden' name='next_question' />");
      	next_question.attr('value', $("#question_select").val());
      	$("form").append(next_question);
      	$("form").submit();
      	return false;
	});
	$("#question_select").change(function(){
		var temp=true;
		$(".radio-tr").each(function(){
			if($(this).find("input:checked").length == 0){
				temp = false;
				return false;
			}
		});
		if(!temp && !warning_confirmed){
			$("#failed-submit-dialog").dialog('open');
			$("#question_select").prop("selectedIndex",select_initial_index);
			return false;
		}
		select_question(parseInt($("#question_select").val()));
  	});

});
