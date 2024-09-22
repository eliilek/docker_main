var idleTime = 0;

$(document).ready(function(){
	var idleInterval = setInterval(timerIncrement, 60000); // 1 minute

	// Zero the idle timer on mouse movement.
    $(this).mousemove(function (e) {
        idleTime = -1;
    });
    $(this).keypress(function (e) {
        idleTime = -1;
    });
    $("#timeout-dialog").hide();
    $("#failed-submit-dialog").hide();
    $( "#timeout-dialog" ).dialog({
  		dialogClass: "no-close",
  		modal: true,
  		autoOpen: false,
  		buttons: [
    			{
      			text: "OK",
      			click: function() {
        			$( this ).dialog( "close" );
      			}
    		}
  		]
	});

    $( "#failed-submit-dialog" ).dialog({
    	dialogClass: "no-close",
  		modal: true,
  		autoOpen: false,
    	buttons: [
    		{
    		text: "OK",
    		click: function(){
    			$(this).dialog("close");
    		}
    		}
    	]
    })

	$("form").submit(function(){
		var temp=true;
		$(".radio-div").each(function(){
			if($(this).find("input:checked").length == 0){
				temp = false;
				return false;
			}
		});
		$("input[type='text']").each(function(){
			if(!$(this).val()){
				temp = false;
				return false;
			}
		});
		$("textarea").each(function(){
			if(!$(this).val()){
				temp = false
				return false;
			}
		});
		if(!temp){
			$("#failed-submit-dialog").dialog('open');
			return false;
		}
	});
});

function timerIncrement(){
	idleTime = idleTime + 1;
	console.log(idleTime.toString());
	if (idleTime == 8){
		//Issue warning
		$("#timeout-dialog").dialog('open');
	} else if (idleTime == 10) {
		timeout();
	} else if (idleTime == 0) {
		$("#timeout-dialog").dialog('close');
	}
}