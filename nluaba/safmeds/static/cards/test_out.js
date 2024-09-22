var timing_start;
var timeout;
var temp_interval;
var index = 0;
var responses = [];
var rand_name;
var typo_responses = [];
var stimulus_start;
var ended = false;

function makeName() {
  var text = "";
  var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

  for (var i = 0; i < 5; i++){
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}

function sleep(delay) {
  var start = new Date().getTime();
  while (new Date().getTime() < start + delay);
}

function end(auto=false){
  if (ended == false){
    ended = true;
  var timing_end = Date.now();
  payload = {"responses": JSON.stringify(responses), "deck":deck, "practice_type":"test_out"}
  payload['duration'] = timing_end - timing_start;
  if (auto){
    report(payload, function(){
      console.log("Done");
    })
  } else {
    report(payload, function(){
      window.location = "/"
      //$("#card").empty();
      //$("#card").html("You're almost done! Press the button below to correct any typos the program may have detected.");
      //$("#finish").show();
      //$("#finish").focus();
    });
  }
}}

$(document).ready(function(){
  rand_name = makeName();
  $("#typos").hide();
  $(".real_input").attr('id', 'response_' + rand_name);
  console.log('response_' + rand_name);
  $("#finish").hide();
  $("#finish").click(function(){
    $(".typo-input").each(function(index){
      if ($(this).val() != ""){
        responses[$(this).data("index")]['response'] = $(this).val();
      }
    });
    end();
    return;
  });
  $("#definition").html(cards[index]['definition']);
  $(".real_input").focus();
  $(".real_input").on("keypress", function(event){
    $(".real_input").off("keypress");
    timing_start = Date.now();
    stimulus_start = Date.now();
    $(".real_input").on("keypress", function(event){
      if (event.keyCode == 13){
        $("#next").click();
      }
    });
  });
  $("#next").click(function(event){
    responses.push({'card_id':cards[index]['id'], 'response':$(".real_input").val(), 'latency':Date.now()-stimulus_start});
    if ($(".real_input").val().toUpperCase().replace("`", "'").trim() != cards[index]['term'].toUpperCase().replace("`", "'").trim()){
      typo_responses.push({'index':index, 'response':$(".real_input").val()});
    }
    index += 1;
    if (index >= cards.length){
      if (typo_responses.length == 0){
        end();
        return;
      }
      for (var i = 0; i < typo_responses.length; i++) {
        var new_row = $("<tr></tr>");
        var new_response = $("<td></td>");
        new_response.html(typo_responses[i]['response']);
        new_row.append(new_response);
        var new_input_container = $("<td></td>");
        var new_input = $("<input type='text' class='typo-input' />");
        new_input.data("index", typo_responses[i]['index']);
        new_input.val(typo_responses[i]['response']);
        new_input_container.append(new_input);
        new_row.append(new_input_container);
        $("#typos").append(new_row);
      }
      $("#card").hide();
      $("#typos").show();
      $("#finish").show();
      return;
    }
    $("#definition").html(cards[index]['definition']);
    $("#next").prop("disabled", false);
    $(".real_input").prop("disabled", false);
    $(".real_input").val("");
    $(".real_input").focus();
    stimulus_start = Date.now();
  });
  $(window).on("beforeunload", function(e){
    console.log("Unload");
    responses.push({'card_id':cards[index]['id'], 'response':$(".real_input").val(), 'latency':Date.now()-stimulus_start});
    end(true);
    sleep(1500);
  });
  $(".real_input").css("height", "35px");
});
