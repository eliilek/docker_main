$(document).ready(function(){
	$(".draggable-img").draggable({helper:'clone'})
	$(".droppable-div").droppable({
		over:overFunction,
		out:outFunction,
		drop:dropFunction
	})
})

function overFunction(event, ui){
	$(this).addClass("drag-hover");
}

function outFunction(event, ui){
	$(this).removeClass("drag-hover");
}

function dropFunction(event, ui){
	//Remove any children in div
	$(this).empty()
	$(this).removeClass("drag-hover");
	//Create img tag, copy src from draggable, add draggable's ID attr to hidden input
	ui.draggable.clone().attr("id", "").appendTo(this);
	if ($(this).hasClass("left")){
		$(this).parent().children(".left").val(ui.draggable.attr("id"));
	} else {
		$(this).parent().children(".right").val(ui.draggable.attr("id"));
	}
	//NOTE magic number lives here
	if ($("img").length == 16){
		$("input[type=submit]").prop("disabled", false);
	}
}